"""What the agent knows when it sits down to plan the day.

Every number here comes from a query the tool already runs for one of its pages —
planning must not become a second source of truth that drifts from what the dashboard
says. It is deliberately compact: this whole thing goes into a prompt, and a model given
five hundred rows plans worse than one given the twenty that matter.
"""
from __future__ import annotations

import datetime as dt

MAX_ROWS = 12          # per list; enough to choose between, small enough to read


def _rows(conn, sql: str, params: tuple = ()) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def _pending_replies(conn) -> list[dict]:
    return _rows(conn,
                 "SELECT m.id, m.lead_no, m.channel, m.intent, m.received_at,"
                 "       l.company_en, l.country"
                 " FROM inbox_messages m JOIN leads l ON l.no=m.lead_no"
                 " WHERE m.kind='reply' AND m.handled_at IS NULL"
                 " ORDER BY m.received_at DESC LIMIT ?", (MAX_ROWS,))


def _overdue_tasks(conn) -> list[dict]:
    return _rows(conn,
                 "SELECT a.id, a.lead_no, a.title, a.type, a.due_at, l.company_en"
                 " FROM activities a JOIN leads l ON l.no=a.lead_no"
                 " WHERE a.status='open' AND a.due_at < date('now', 'localtime')"
                 " ORDER BY a.due_at LIMIT ?", (MAX_ROWS,))


def _stalled_opportunities(conn) -> list[dict]:
    from app import opportunities
    rows = opportunities.list_all(conn, attention=True)
    return [{k: o.get(k) for k in
             ("id", "lead_no", "title", "stage", "amount", "currency",
              "next_action", "next_action_date", "overdue", "stale")}
            for o in rows[:MAX_ROWS]]


def _opportunity_coaching(conn) -> list[dict]:
    from app.agent import opportunity_coach
    result = []
    for row in opportunity_coach.portfolio(conn, limit=MAX_ROWS):
        result.append({
            "opportunity_id": row["opportunity_id"],
            "lead_no": row["lead_no"],
            "company_en": row["company_en"],
            "title": row["title"],
            "stage": row["stage"],
            "amount": row["amount"],
            "currency": row["currency"],
            "health": row["health"],
            "severity": row["severity"],
            "qualification_pct": row["qualification"]["completeness"],
            "missing_project_facts": [m["label"] for m in row["qualification"]["missing"][:5]],
            "missing_authority": [m["label"] for m in row["contact_coverage"]["missing"]],
            "risks": row["risks"][:5],
            "next_best_action": row["next_best_action"],
            "fresh_signal": (row["fresh_signal"] or {}).get("headline"),
            "open_task": bool(row["open_task"]),
        })
    return result


def _untouched(conn) -> dict:
    """The untouched pile: how big it really is, and the best dozen in it.

    Both numbers matter. Showing only the high scorers once made the planner announce
    that the pool was empty while three contactable companies sat just under the score
    threshold — so the size of the pool is reported separately from the shortlist.

    Narrowed in SQL before scoring: `ranked()` scores every open lead, and the planner
    only ever needs the top of this pile. The shortlist also includes deterministic
    autonomous-send readiness so the model never has to infer whether missing evidence
    is acceptable.
    """
    from app import sales_intelligence
    from app.agent import send_decision

    sales_intelligence.ensure_schema(conn)
    total_untouched = conn.execute(
        "SELECT COUNT(*) c FROM leads l"
        " WHERE COALESCE(l.do_not_contact,0)=0"
        "   AND COALESCE(l.stage,'new') NOT IN ('won','lost')"
        "   AND NOT EXISTS (SELECT 1 FROM outreach o WHERE o.lead_no=l.no"
        "                   AND o.status IN ('messaged','replied'))"
    ).fetchone()["c"]
    scored = sales_intelligence.ranked(
        conn, limit=2000, min_score=55, untouched_only=True)
    emailable = conn.execute(
        "SELECT COUNT(*) c FROM leads l"
        " WHERE COALESCE(l.do_not_contact,0)=0 AND l.email IS NOT NULL AND l.email != ''"
        "   AND COALESCE(l.email_status,'') != 'invalid'"
        "   AND NOT EXISTS (SELECT 1 FROM outreach o WHERE o.lead_no=l.no"
        "                   AND o.status IN ('messaged','replied'))").fetchone()["c"]
    top = []
    for row in scored[:MAX_ROWS]:
        decision = send_decision.evaluate_account(conn, row["lead_no"], sales=row)
        top.append({
            "lead_no": row["lead_no"],
            "company_en": row["company_en"],
            "country": row["country"],
            "score": row["score"],
            "grade": row["grade"],
            "next_action": row["next_action"],
            "missing_decision_maker": row["missing_decision_maker"],
            "autonomous_send": {
                "ready_for_template_check": decision["ready_for_template_check"],
                "blockers": decision["blockers"][:5],
                "positives": decision["positives"][:5],
                "best_signal": decision.get("best_signal"),
            },
        })
    return {
        "total_untouched": total_untouched,
        "emailable_untouched": emailable,
        "top": top,
    }


def _channel_capacity(conn) -> dict:
    """`outreach.remaining_today` already resolves rotation vs the fallback Gmail, so
    that one number is the answer; `email_sendable` says whether either exists at all,
    which is the difference between "no budget left today" and "no way to send"."""
    from app import channel_outreach, mailboxes, outreach
    from app.channels.email_adapter import get_password
    return {
        "email_remaining_today": outreach.remaining_today(conn),
        "email_sendable": mailboxes.has_active(conn) or bool(get_password()),
        "whatsapp_remaining_today": max(
            0, channel_outreach.DAILY_CAP["whatsapp"]
            - channel_outreach.sent_today(conn, "whatsapp")),
        "instagram_remaining_today": max(
            0, channel_outreach.DAILY_CAP["instagram"]
            - channel_outreach.sent_today(conn, "instagram")),
        "max_per_batch": channel_outreach.MAX_BATCH,
    }


def _reply_rate(conn, days: int = 30) -> dict:
    row = conn.execute(
        "SELECT COUNT(DISTINCT s.lead_no) AS reached,"
        " COUNT(DISTINCT CASE WHEN o.status='replied' THEN s.lead_no END) AS replied"
        " FROM send_log s LEFT JOIN outreach o"
        "   ON o.lead_no=s.lead_no AND o.channel=s.channel"
        " WHERE s.sent_at >= date('now', ?)", (f"-{days} days",)).fetchone()
    reached, replied = row["reached"] or 0, row["replied"] or 0
    return {"days": days, "reached": reached, "replied": replied,
            "reply_rate_pct": round(replied * 100 / reached, 1) if reached else 0.0}


def _weak(conn) -> list[dict]:
    from app.agent import learn
    return learn.weak_campaigns(conn)[:MAX_ROWS]


def build(conn) -> dict:
    from app import activities, autosend, sequences
    from app.agent import account_brain, mission, proposals
    proposals.ensure_schema(conn)
    return {
        "today": dt.date.today().isoformat(),
        "mission": mission.get(conn),
        "mission_progress": mission.progress(conn),
        "pending_replies": _pending_replies(conn),
        "tasks": {**activities.stats(conn), "overdue_list": _overdue_tasks(conn)},
        "stalled_opportunities": _stalled_opportunities(conn),
        # Stage-aware LED sales coaching: whether a live deal is actually qualified and
        # whether authority/next-step gaps make it unsafe to treat the stage as progress.
        "opportunity_coaching": _opportunity_coaching(conn),
        # Contacted accounts that have no other mechanism owning their next step.
        # This is the deterministic portfolio an experienced salesperson keeps in mind.
        "due_followups": account_brain.due_accounts(conn, limit=MAX_ROWS),
        "untouched": _untouched(conn),
        "sequence_due_today": len(sequences.due_queue(conn)),
        "capacity": _channel_capacity(conn),
        "email_safety_pause": autosend.safety_pause(conn),
        "reply_rate": _reply_rate(conn),
        # What has demonstrably stopped working, with the volume to back it up.
        "weak_campaigns": _weak(conn),
        "templates": _rows(conn, "SELECT id, name, channel FROM templates ORDER BY id"),
        "sequences": _rows(conn, "SELECT id, name, channel FROM sequences ORDER BY id"),
        # So the plan does not re-propose what is already waiting or running.
        "already_pending": _rows(
            conn, "SELECT kind, lead_no, title, status FROM agent_proposals"
                  " WHERE status IN ('pending','approved','edited_approved')"
                  " ORDER BY id DESC LIMIT 50"),
    }
