"""Evidence-backed account truth that stays separate from the human CRM stage.

`leads.stage` is a useful sales judgement, but it is not evidence that a message was
answered or a commercial milestone happened. This module derives communication and
commercial truth from durable rows and reports contradictions without rewriting the
human stage.

The only mutating helper, :func:`self_heal`, is intentionally narrow: it may repair
machine-owned sequence/task state that is impossible given stronger inbox evidence.
It never changes CRM stage, quotes, orders, price, payment or delivery commitments.
"""
from __future__ import annotations

import datetime as dt
import sqlite3


TERMINAL_STAGES = {"won", "lost"}
_STAGE_BEHIND_REPLY = {None, "", "new", "contacted"}


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _count(conn: sqlite3.Connection, sql: str, params=()) -> int:
    row = conn.execute(sql, params).fetchone()
    return int((row[0] if row else 0) or 0)


def _anomaly(code: str, severity: str, detail: str, *, repairable: bool = False) -> dict:
    return {
        "code": code,
        "severity": severity,
        "detail": detail,
        "repairable": repairable,
    }


def assess(conn: sqlite3.Connection, lead_no: int) -> dict | None:
    """Return one read-only, evidence-backed account truth snapshot."""
    lead = conn.execute(
        "SELECT no,company_en,country,stage,do_not_contact FROM leads WHERE no=?", (lead_no,)
    ).fetchone()
    if lead is None:
        return None

    stage = (lead["stage"] or "new").strip().lower()
    human_replies = 0
    auto_replies = 0
    if _table_exists(conn, "inbox_messages"):
        human_replies = _count(
            conn, "SELECT COUNT(*) FROM inbox_messages WHERE lead_no=? AND kind='reply'", (lead_no,)
        )
        auto_replies = _count(
            conn, "SELECT COUNT(*) FROM inbox_messages WHERE lead_no=? AND kind='auto'", (lead_no,)
        )

    outreach_rows = []
    if _table_exists(conn, "outreach"):
        outreach_rows = conn.execute(
            "SELECT channel,status,COALESCE(touch_count,0) touch_count,"
            " COALESCE(reply_received,0) reply_received,message_sent_date"
            " FROM outreach WHERE lead_no=?",
            (lead_no,),
        ).fetchall()
    touch_count = sum(int(r["touch_count"] or 0) for r in outreach_rows
                      if r["status"] in ("messaged", "replied"))
    outreach_replied = sum(1 for r in outreach_rows if r["status"] == "replied")
    reply_received = sum(1 for r in outreach_rows if int(r["reply_received"] or 0) == 1)

    send_count = 0
    if _table_exists(conn, "send_log"):
        send_count = _count(conn, "SELECT COUNT(*) FROM send_log WHERE lead_no=?", (lead_no,))
    contacted = bool(send_count or touch_count)
    verified_human_reply = bool(human_replies or reply_received)

    active_sequences = 0
    if _table_exists(conn, "sequence_enrollments"):
        active_sequences = _count(
            conn,
            "SELECT COUNT(*) FROM sequence_enrollments WHERE lead_no=? AND status='active'",
            (lead_no,),
        )

    quote_sent = quote_accepted = 0
    if _table_exists(conn, "quotes"):
        quote_sent = _count(
            conn,
            "SELECT COUNT(*) FROM quotes WHERE lead_no=? AND status IN ('sent','accepted')",
            (lead_no,),
        )
        quote_accepted = _count(
            conn, "SELECT COUNT(*) FROM quotes WHERE lead_no=? AND status='accepted'", (lead_no,)
        )

    order_count = 0
    if _table_exists(conn, "orders"):
        order_count = _count(conn, "SELECT COUNT(*) FROM orders WHERE lead_no=?", (lead_no,))

    if stage in TERMINAL_STAGES:
        factual_state = stage
    elif order_count:
        factual_state = "ordered"
    elif quote_accepted:
        factual_state = "quote_accepted"
    elif quote_sent:
        factual_state = "quoted"
    elif verified_human_reply:
        factual_state = "human_replied"
    elif contacted:
        factual_state = "contacted"
    else:
        factual_state = "never_contacted"

    anomalies: list[dict] = []
    if stage == "replied" and not verified_human_reply:
        anomalies.append(_anomaly(
            "stage_replied_without_human_reply", "medium",
            "CRM 阶段是 replied，但没有可验证的真人回复证据；保留人工阶段，不让 Agent 把它当通信事实。",
        ))
    if outreach_replied and not verified_human_reply:
        anomalies.append(_anomaly(
            "outreach_replied_without_human_reply", "high",
            "outreach 仍标记 replied，但 inbox/reply_received 没有真人回复证据；需要历史数据复核。",
        ))
    if verified_human_reply and stage in _STAGE_BEHIND_REPLY:
        anomalies.append(_anomaly(
            "human_reply_but_stage_behind", "info",
            "存在真人回复证据，但 CRM 阶段仍较早；这是人工 CRM 标签落后，不自动改阶段。",
        ))
    if quote_accepted and not order_count:
        anomalies.append(_anomaly(
            "accepted_quote_without_order", "high",
            "存在已接受报价但尚未建立订单，应由销售流程确认并转单。",
        ))
    if order_count and stage != "won":
        anomalies.append(_anomaly(
            "order_but_stage_behind", "info",
            "已经存在订单，但 CRM 阶段还不是 won；不自动判定成交，避免覆盖人工判断。",
        ))
    if verified_human_reply and active_sequences:
        anomalies.append(_anomaly(
            "active_sequence_after_human_reply", "high",
            f"真人回复后仍有 {active_sequences} 个活跃跟进序列，属于可安全修复的机器状态。",
            repairable=True,
        ))

    stale_reply_tasks = 0
    if _table_exists(conn, "activities") and _table_exists(conn, "inbox_messages"):
        rows = conn.execute(
            "SELECT a.id,a.source_ref,m.kind FROM activities a"
            " LEFT JOIN inbox_messages m ON m.id=CAST(substr(a.source_ref,7) AS INTEGER)"
            " WHERE a.lead_no=? AND a.status='open' AND a.source='reply'"
            " AND a.source_ref LIKE 'inbox:%'",
            (lead_no,),
        ).fetchall()
        stale_reply_tasks = sum(1 for row in rows if row["kind"] != "reply")
        if stale_reply_tasks:
            anomalies.append(_anomaly(
                "stale_reply_task", "medium",
                f"有 {stale_reply_tasks} 个 reply task 已不再指向真人 reply，可安全取消。",
                repairable=True,
            ))

    severity_order = {"high": 0, "medium": 1, "info": 2}
    anomalies.sort(key=lambda a: severity_order.get(a["severity"], 9))
    return {
        "lead_no": lead_no,
        "company_en": lead["company_en"],
        "country": lead["country"],
        "crm_stage": stage,
        "factual_state": factual_state,
        "verified_human_reply": verified_human_reply,
        "contacted": contacted,
        "do_not_contact": bool(lead["do_not_contact"]),
        "evidence": {
            "human_replies": human_replies,
            "auto_replies": auto_replies,
            "reply_received_channels": reply_received,
            "outreach_replied_channels": outreach_replied,
            "touch_count": touch_count,
            "send_count": send_count,
            "active_sequences": active_sequences,
            "quotes_sent_or_accepted": quote_sent,
            "quotes_accepted": quote_accepted,
            "orders": order_count,
            "stale_reply_tasks": stale_reply_tasks,
        },
        "anomalies": anomalies,
        "has_anomaly": bool(anomalies),
        "repairable_anomalies": sum(1 for a in anomalies if a["repairable"]),
    }


def portfolio(conn: sqlite3.Connection, *, limit: int = 50) -> dict:
    """Aggregate read-only truth health for the control center."""
    rows: list[dict] = []
    counts: dict[str, int] = {}
    repairable = 0
    for lead in conn.execute("SELECT no FROM leads ORDER BY no").fetchall():
        truth = assess(conn, lead["no"])
        if not truth or not truth["has_anomaly"]:
            continue
        rows.append(truth)
        repairable += int(truth["repairable_anomalies"])
        for anomaly in truth["anomalies"]:
            counts[anomaly["code"]] = counts.get(anomaly["code"], 0) + 1

    severity_order = {"high": 0, "medium": 1, "info": 2}
    rows.sort(key=lambda item: (
        min((severity_order.get(a["severity"], 9) for a in item["anomalies"]), default=9),
        -len(item["anomalies"]), item["lead_no"],
    ))
    return {
        "anomalous_accounts": len(rows),
        "repairable_anomalies": repairable,
        "by_code": counts,
        "accounts": rows[:max(1, min(int(limit), 200))],
    }


def _stop_active_sequences(conn: sqlite3.Connection, lead_no: int) -> int:
    if not _table_exists(conn, "sequence_enrollments"):
        return 0
    from app import sequences
    return sequences.stop_for_lead(conn, lead_no)


def _cancel_stale_reply_tasks(conn: sqlite3.Connection, lead_no: int) -> int:
    if not (_table_exists(conn, "activities") and _table_exists(conn, "inbox_messages")):
        return 0
    rows = conn.execute(
        "SELECT a.id,a.source_ref,m.kind FROM activities a"
        " LEFT JOIN inbox_messages m ON m.id=CAST(substr(a.source_ref,7) AS INTEGER)"
        " WHERE a.lead_no=? AND a.status='open' AND a.source='reply'"
        " AND a.source_ref LIKE 'inbox:%'",
        (lead_no,),
    ).fetchall()
    ids = [row["id"] for row in rows if row["kind"] != "reply"]
    if not ids:
        return 0
    now = _now()
    for activity_id in ids:
        conn.execute(
            "UPDATE activities SET status='cancelled',completed_at=NULL,updated_at=? WHERE id=?",
            (now, activity_id),
        )
    conn.commit()
    from app import activities
    activities.sync_lead(conn, lead_no)
    return len(ids)


def self_heal(conn: sqlite3.Connection, *, limit: int = 100) -> dict:
    """Repair only contradictions in machine-owned derived state.

    The function deliberately uses stored human-reply evidence as its prerequisite and
    never changes `leads.stage`, outreach status, quotes or orders.
    """
    healed_sequences = 0
    cancelled_tasks = 0
    touched: list[int] = []
    for lead in conn.execute("SELECT no FROM leads ORDER BY no LIMIT ?", (max(1, int(limit)),)).fetchall():
        truth = assess(conn, lead["no"])
        if not truth:
            continue
        before = healed_sequences + cancelled_tasks
        if truth["verified_human_reply"] and truth["evidence"]["active_sequences"]:
            healed_sequences += _stop_active_sequences(conn, lead["no"])
        if truth["evidence"]["stale_reply_tasks"]:
            cancelled_tasks += _cancel_stale_reply_tasks(conn, lead["no"])
        if healed_sequences + cancelled_tasks > before:
            touched.append(lead["no"])
    return {
        "leads_touched": len(touched),
        "lead_nos": touched,
        "sequences_stopped": healed_sequences,
        "reply_tasks_cancelled": cancelled_tasks,
    }
