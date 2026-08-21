"""Deterministic account attention for customers that would otherwise fall through gaps.

The LLM should choose between good options, not remember every account in the database.
This module finds contacted customers whose next step has no owner: no reply waiting,
no open task, no active sequence and no Agent proposal already covering the account.

It deliberately creates internal task proposals only. Customer-facing follow-up remains
behind the existing sequence/reply/send paths and their safety/autonomy controls.
"""
from __future__ import annotations

import datetime as dt

from app.agent import proposals

MAX_WORLD_ROWS = 12
MAX_SAFETY_NET = 3


def _parse_date(value: str | None) -> dt.date | None:
    if not value:
        return None
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def cadence_days(touch_count: int) -> int:
    """A conservative B2B cadence once a lead leaves an explicit sequence."""
    if touch_count <= 1:
        return 5
    if touch_count == 2:
        return 7
    return 14


def _candidate_rows(conn) -> list[dict]:
    """Return leads that have been contacted but have no mechanism owning next action."""
    proposals.ensure_schema(conn)
    rows = conn.execute(
        "SELECT l.no, l.company_en, l.country, l.stage,"
        "       COALESCE(SUM(CASE WHEN o.status IN ('messaged','replied')"
        "                         THEN COALESCE(o.touch_count,0) ELSE 0 END),0) touch_count,"
        "       MAX(CASE WHEN o.status IN ('messaged','replied') THEN o.message_sent_date END) last_touch"
        " FROM leads l JOIN outreach o ON o.lead_no=l.no"
        " WHERE COALESCE(l.do_not_contact,0)=0"
        "   AND COALESCE(l.stage,'new') NOT IN ('won','lost')"
        "   AND o.status='messaged'"
        "   AND NOT EXISTS (SELECT 1 FROM inbox_messages m"
        "                   WHERE m.lead_no=l.no AND m.kind='reply' AND m.handled_at IS NULL)"
        "   AND NOT EXISTS (SELECT 1 FROM outreach r"
        "                   WHERE r.lead_no=l.no AND (r.status='replied' OR r.reply_received=1))"
        "   AND NOT EXISTS (SELECT 1 FROM activities a"
        "                   WHERE a.lead_no=l.no AND a.status='open')"
        "   AND NOT EXISTS (SELECT 1 FROM sequence_enrollments e"
        "                   WHERE e.lead_no=l.no AND e.status='active')"
        "   AND NOT EXISTS (SELECT 1 FROM agent_proposals p"
        "                   WHERE p.lead_no=l.no"
        "                     AND p.status IN ('pending','approved','edited_approved')"
        "                     AND p.kind IN ('create_task','reply_draft','send_outreach',"
        "                                    'enroll_sequence','stop_sequence','build_opportunity'))"
        " GROUP BY l.no, l.company_en, l.country, l.stage"
        " HAVING last_touch IS NOT NULL"
    ).fetchall()
    return [dict(r) for r in rows]


def due_accounts(conn, *, today: dt.date | None = None,
                 limit: int = MAX_WORLD_ROWS) -> list[dict]:
    """Rank due contacted accounts using the existing explainable sales intelligence."""
    from app import sales_intelligence

    today = today or dt.date.today()
    sales_intelligence.ensure_schema(conn)
    due: list[dict] = []
    for row in _candidate_rows(conn):
        last_touch = _parse_date(row.get("last_touch"))
        if not last_touch:
            continue
        touch_count = max(1, int(row.get("touch_count") or 1))
        cadence = cadence_days(touch_count)
        due_date = last_touch + dt.timedelta(days=cadence)
        if due_date > today:
            continue
        score = sales_intelligence.score_lead(conn, row["no"], today=today, _ensure=False)
        if not score:
            continue
        due.append({
            "lead_no": row["no"],
            "company_en": row["company_en"],
            "country": row.get("country"),
            "score": score["score"],
            "grade": score["grade"],
            "touch_count": touch_count,
            "last_touch": last_touch.isoformat(),
            "due_date": due_date.isoformat(),
            "days_overdue": max(0, (today - due_date).days),
            "next_action": score["next_action"],
        })
    due.sort(key=lambda r: (-r["score"], -r["days_overdue"], r["due_date"], r["lead_no"]))
    return due[:max(1, min(int(limit), 100))]


def safety_net(conn, *, today: dt.date | None = None,
               limit: int = MAX_SAFETY_NET) -> dict:
    """Ensure both dormant accounts and unhealthy live deals have an owned next step.

    At the default `propose` autonomy this only creates visible recommendations. If Allen
    explicitly sets create_task to `auto`, the normal proposal executor creates the task.
    Customer-facing messages are never sent here.
    """
    from app.agent import opportunity_coach

    today = today or dt.date.today()
    made: list[int] = []
    considered = due_accounts(conn, today=today, limit=limit)
    for account in considered:
        title = f"跟进 {account['company_en']}：{account['next_action']}"
        p = proposals.create(
            conn, "create_task", lead_no=account["lead_no"],
            title=title[:200],
            reasoning=(f"已触达 {account['touch_count']} 次，最后一次在 {account['last_touch']}；"
                       f"按当前节奏应在 {account['due_date']} 前有下一步，现已逾期"
                       f" {account['days_overdue']} 天。销售优先级 {account['score']} 分"
                       f"（{account['grade']}）。"),
            evidence=[
                {"claim": "最近触达", "source": account["last_touch"]},
                {"claim": "下一最佳动作", "source": account["next_action"]},
            ],
            payload={
                "title": title[:200],
                "type": "task",
                "due_at": today.isoformat(),
                "priority": "high" if account["score"] >= 75 else "normal",
                "note": (f"Account Brain：最后触达 {account['last_touch']}，"
                         f"累计 {account['touch_count']} 次；建议：{account['next_action']}"),
            },
            risk="low",
            dedupe_key=(f"account-brain-{account['last_touch']}-"
                        f"{account['touch_count']}-{account['next_action']}"),
        )
        if p:
            made.append(p["id"])

    # Live opportunities are a separate portfolio: a quoted deal with no next-action
    # date is more dangerous than a cold account being late by a day. Reuse the same
    # internal proposal/autonomy mechanism instead of building another executor.
    opportunity_result = opportunity_coach.safety_net(conn, today=today, limit=limit)
    ids = [*made, *opportunity_result["ids"]]
    return {
        "due": len(considered),
        "proposed": len(ids),
        "ids": ids,
        "accounts": considered,
        "opportunity_coach": opportunity_result,
    }
