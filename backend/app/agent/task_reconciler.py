"""Deterministically close or supersede Agent-created sales tasks.

Only tasks that are explicitly `source='agent'` and trace back to a real Agent proposal
are eligible. Historical manual/legacy/reply/opportunity tasks are never inferred from
their titles and are therefore never touched here.
"""
from __future__ import annotations

import datetime as dt

from app import activities, opportunities
from app.agent import proposals


def _proposal_id(source_ref: str | None) -> int | None:
    if not source_ref or not source_ref.startswith("proposal:"):
        return None
    try:
        return int(source_ref.split(":", 1)[1])
    except (TypeError, ValueError):
        return None


def _append_note(existing: str | None, reason: str) -> str:
    stamp = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M UTC")
    suffix = f"[Agent 自动回收 {stamp}] {reason}"
    return f"{existing}\n{suffix}".strip()[:1000]


def _resolve(conn, activity: dict, *, status: str, reason: str) -> None:
    activities.update(conn, activity["id"], {
        "status": status,
        "note": _append_note(activity.get("note"), reason),
    })


def _account_rule_done(conn, activity: dict, rule: dict) -> tuple[bool, str]:
    key = rule.get("next_action_key")
    lead_no = activity["lead_no"]

    if key == "refresh_icp":
        from app import recheck
        row = conn.execute("SELECT target_fit FROM leads WHERE no=?", (lead_no,)).fetchone()
        if row and recheck.fit_score(row["target_fit"]) > 0:
            return True, "官网 ICP 已重新分级，这条补资料任务已满足"

    elif key == "find_decision_maker":
        found = conn.execute(
            "SELECT 1 FROM contacts WHERE lead_no=? AND role='decision_maker' LIMIT 1",
            (lead_no,),
        ).fetchone()
        if found:
            return True, "已存在明确 decision_maker 联系人"

    elif key == "replace_invalid_channel":
        lead = conn.execute(
            "SELECT email_status, phone, instagram FROM leads WHERE no=?", (lead_no,)
        ).fetchone()
        contact = conn.execute(
            "SELECT 1 FROM contacts WHERE lead_no=? AND ((email IS NOT NULL AND COALESCE(email_status,'')!='invalid')"
            " OR phone IS NOT NULL) LIMIT 1",
            (lead_no,),
        ).fetchone()
        if lead and (lead["email_status"] != "invalid" or lead["phone"] or lead["instagram"] or contact):
            return True, "已补到可行动联系渠道"

    elif key == "verify_company":
        from app import sales_intelligence
        lead = conn.execute("SELECT company_en FROM leads WHERE no=?", (lead_no,)).fetchone()
        if lead and not sales_intelligence._junk_company_name(lead["company_en"]):
            return True, "公司名称已经核实，不再是页面标题/404 类占位名称"

    elif key == "quote_to_order":
        quote_no = (rule.get("context") or {}).get("quote_no")
        if quote_no:
            order = conn.execute(
                "SELECT 1 FROM orders o JOIN quotes q ON q.id=o.quote_id WHERE q.quote_no=? LIMIT 1",
                (quote_no,),
            ).fetchone()
            if order:
                return True, f"报价 {quote_no} 已转订单"

    elif key == "quote_followup":
        quote_no = (rule.get("context") or {}).get("quote_no")
        if quote_no:
            quote = conn.execute("SELECT status FROM quotes WHERE quote_no=?", (quote_no,)).fetchone()
            if quote and quote["status"] != "sent":
                return True, f"报价 {quote_no} 状态已变为 {quote['status']}"
        reply = conn.execute(
            "SELECT 1 FROM inbox_messages WHERE lead_no=? AND kind='reply'"
            " AND created_at > ? LIMIT 1",
            (lead_no, activity["created_at"]),
        ).fetchone()
        if reply:
            return True, "任务创建后客户已回复，原报价跟进任务已被新事实取代"

    elif key in ("first_touch", "schedule_followup", "generic_followup"):
        baseline = rule.get("baseline_last_touch")
        if baseline:
            newer = conn.execute(
                "SELECT 1 FROM outreach WHERE lead_no=? AND status IN ('messaged','replied')"
                " AND message_sent_date > ? LIMIT 1",
                (lead_no, baseline),
            ).fetchone()
            if newer:
                return True, "已发生比任务基线更新的客户触达"
        active_sequence = conn.execute(
            "SELECT 1 FROM sequence_enrollments WHERE lead_no=? AND status='active' LIMIT 1",
            (lead_no,),
        ).fetchone()
        if active_sequence:
            return True, "客户已由自动跟进序列接管"

    return False, ""


def _reconcile_one(conn, activity: dict, proposal: dict, rule: dict) -> tuple[str, str] | None:
    rule_type = rule.get("type")
    if rule_type == "account_brain":
        done, reason = _account_rule_done(conn, activity, rule)
        return ("done", reason) if done else None

    if rule_type == "opportunity_coach":
        opportunity_id = proposal.get("opportunity_id") or activity.get("opportunity_id")
        if not opportunity_id:
            return None
        opp = opportunities.get(conn, int(opportunity_id))
        if opp is None or opp["stage"] in ("won", "lost"):
            return "done", "关联商机已经关闭"
        from app.agent import opportunity_coach
        current = opportunity_coach.coach_opportunity(conn, opp)
        if current["severity"] == "low":
            return "done", "当前商机体检已恢复为低风险"
        current_digest = opportunity_coach._issue_digest(current)
        baseline = rule.get("issue_digest")
        if baseline and current_digest != baseline:
            return "cancelled", "商机风险结构已经变化，旧体检任务作废；如仍需处理将生成新的下一步"
    return None


def reconcile(conn, *, limit: int = 500) -> dict:
    """Reconcile traceable Agent tasks before the next planning pass."""
    activities.ensure_schema(conn)
    proposals.ensure_schema(conn)
    rows = conn.execute(
        "SELECT * FROM activities WHERE source='agent' AND status='open'"
        " AND source_ref LIKE 'proposal:%' ORDER BY id LIMIT ?",
        (max(1, min(int(limit), 2000)),),
    ).fetchall()
    resolved = cancelled = checked = 0
    for row in rows:
        activity = dict(row)
        proposal_id = _proposal_id(activity.get("source_ref"))
        if proposal_id is None:
            continue
        proposal = proposals.get(conn, proposal_id)
        if not proposal:
            continue
        payload = proposal.get("payload") or {}
        rule = payload.get("completion_rule")
        if not isinstance(rule, dict):
            continue
        checked += 1
        outcome = _reconcile_one(conn, activity, proposal, rule)
        if not outcome:
            continue
        status, reason = outcome
        _resolve(conn, activity, status=status, reason=reason)
        if status == "done":
            resolved += 1
        else:
            cancelled += 1
    return {"checked": checked, "resolved": resolved, "superseded": cancelled}
