"""Deterministically close or supersede Agent-created sales tasks.

Only tasks explicitly owned by an Agent proposal are eligible. Historical rows may be
reclassified from the old `manual` bug only when an executed proposal names the exact
created activity id in its execution result; titles are never used to guess ownership.
"""
from __future__ import annotations

import datetime as dt
import re

from app import activities, opportunities
from app.agent import proposals


def _proposal_id(source_ref: str | None) -> int | None:
    if not source_ref or not source_ref.startswith("proposal:"):
        return None
    try:
        return int(source_ref.split(":", 1)[1])
    except (TypeError, ValueError):
        return None


def _instant(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    raw = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.UTC)
    return parsed.astimezone(dt.UTC)


def _reply_after(conn, lead_no: int, created_at: str | None) -> bool:
    baseline = _instant(created_at)
    if baseline is None:
        return False
    rows = conn.execute(
        "SELECT received_at FROM inbox_messages WHERE lead_no=? AND kind='reply'"
        " AND received_at IS NOT NULL ORDER BY received_at DESC LIMIT 20",
        (lead_no,),
    ).fetchall()
    return any((when := _instant(row["received_at"])) is not None and when > baseline for row in rows)


def _append_note(existing: str | None, reason: str) -> str:
    stamp = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M UTC")
    suffix = f"[Agent 自动回收 {stamp}] {reason}"
    return f"{existing}\n{suffix}".strip()[:1000]


def _resolve(conn, activity: dict, *, status: str, reason: str) -> None:
    activities.update(conn, activity["id"], {
        "status": status,
        "note": _append_note(activity.get("note"), reason),
    })


def _ensure_contacts(conn) -> None:
    from app import contacts
    contacts.ensure_schema(conn)


def _ensure_documents(conn) -> None:
    from app import sales_documents
    sales_documents.ensure_schema(conn)


def backfill_agent_task_provenance(conn) -> int:
    """Repair the pre-PR4 source bug using the exact task id recorded by the executor.

    The executor result is of the form `已建销售任务 #123：...`. Matching that id plus
    lead ownership is strong provenance; no title/date heuristic is used.
    """
    proposals.ensure_schema(conn)
    activities.ensure_schema(conn)
    rows = conn.execute(
        "SELECT id, lead_no, execution_result FROM agent_proposals"
        " WHERE kind='create_task' AND status='executed'"
        " AND execution_result LIKE '已建销售任务 #%'")
    fixed = 0
    for row in rows:
        match = re.search(r"已建销售任务 #(\d+)", row["execution_result"] or "")
        if not match:
            continue
        activity_id = int(match.group(1))
        cur = conn.execute(
            "UPDATE activities SET source='agent', source_ref=?, updated_at=?"
            " WHERE id=? AND lead_no=? AND source='manual' AND COALESCE(source_ref,'')=''",
            (f"proposal:{row['id']}", dt.datetime.now(dt.UTC).isoformat(),
             activity_id, row["lead_no"]),
        )
        fixed += cur.rowcount
    if fixed:
        conn.commit()
    return fixed


def _account_rule_outcome(conn, activity: dict, rule: dict) -> tuple[str, str] | None:
    key = rule.get("next_action_key")
    lead_no = activity["lead_no"]

    if key == "refresh_icp":
        from app import recheck
        row = conn.execute("SELECT target_fit FROM leads WHERE no=?", (lead_no,)).fetchone()
        if row and recheck.fit_score(row["target_fit"]) > 0:
            return "done", "官网 ICP 已重新分级，这条补资料任务已满足"

    elif key == "find_decision_maker":
        _ensure_contacts(conn)
        found = conn.execute(
            "SELECT 1 FROM contacts WHERE lead_no=? AND role='decision_maker' LIMIT 1",
            (lead_no,),
        ).fetchone()
        if found:
            # The original recommendation says find the person *then* continue the
            # outreach. Finding the person satisfies the precondition, not the whole
            # multi-step task, so supersede it and let the next cycle choose the new step.
            return "cancelled", "决策联系人已找到；原多步骤任务进入下一阶段，将按新状态重新规划"

    elif key == "replace_invalid_channel":
        _ensure_contacts(conn)
        lead = conn.execute(
            "SELECT email_status, phone, instagram FROM leads WHERE no=?", (lead_no,)
        ).fetchone()
        contact = conn.execute(
            "SELECT 1 FROM contacts WHERE lead_no=? AND ((email IS NOT NULL AND COALESCE(email_status,'')!='invalid')"
            " OR phone IS NOT NULL) LIMIT 1",
            (lead_no,),
        ).fetchone()
        if lead and (lead["email_status"] != "invalid" or lead["phone"] or lead["instagram"] or contact):
            return "done", "已补到可行动联系渠道"

    elif key == "verify_company":
        from app import sales_intelligence
        lead = conn.execute("SELECT company_en FROM leads WHERE no=?", (lead_no,)).fetchone()
        if lead and not sales_intelligence._junk_company_name(lead["company_en"]):
            return "done", "公司名称已经核实，不再是页面标题/404 类占位名称"

    elif key == "quote_to_order":
        _ensure_documents(conn)
        quote_no = (rule.get("context") or {}).get("quote_no")
        if quote_no:
            order = conn.execute(
                "SELECT 1 FROM orders o JOIN quotes q ON q.id=o.quote_id WHERE q.quote_no=? LIMIT 1",
                (quote_no,),
            ).fetchone()
            if order:
                return "done", f"报价 {quote_no} 已转订单"

    elif key == "quote_followup":
        _ensure_documents(conn)
        quote_no = (rule.get("context") or {}).get("quote_no")
        if quote_no:
            quote = conn.execute("SELECT status FROM quotes WHERE quote_no=?", (quote_no,)).fetchone()
            if quote and quote["status"] != "sent":
                return "done", f"报价 {quote_no} 状态已变为 {quote['status']}"
        if _reply_after(conn, lead_no, activity.get("created_at")):
            return "done", "任务创建后客户已回复，原报价跟进任务已经取得结果"

    elif key in ("first_touch", "schedule_followup", "generic_followup"):
        baseline = rule.get("baseline_last_touch")
        if baseline:
            newer = conn.execute(
                "SELECT 1 FROM outreach WHERE lead_no=? AND status IN ('messaged','replied')"
                " AND message_sent_date > ? LIMIT 1",
                (lead_no, baseline),
            ).fetchone()
            if newer:
                return "done", "已发生比任务基线更新的客户触达"
        active_sequence = conn.execute(
            "SELECT 1 FROM sequence_enrollments WHERE lead_no=? AND status='active' LIMIT 1",
            (lead_no,),
        ).fetchone()
        if active_sequence:
            return "done", "客户已由自动跟进序列接管"

    return None


def _reconcile_one(conn, activity: dict, proposal: dict, rule: dict) -> tuple[str, str] | None:
    rule_type = rule.get("type")
    if rule_type == "account_brain":
        return _account_rule_outcome(conn, activity, rule)

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
    """Repair provenance, then reconcile traceable Agent tasks before planning."""
    activities.ensure_schema(conn)
    proposals.ensure_schema(conn)
    backfilled = backfill_agent_task_provenance(conn)
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
    return {
        "provenance_backfilled": backfilled,
        "checked": checked,
        "resolved": resolved,
        "superseded": cancelled,
    }
