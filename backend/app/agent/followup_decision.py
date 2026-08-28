"""When a follow-up may go out (docs/75).

Allen took every quality gate off this path: "质量门拆了，以后不许设置质量门 …
反正就是要多发". What is left is not a weaker gate but a different kind of rule — this
module no longer judges whether a company is worth writing to, only whether writing to
them right now would be too soon or addressed to somebody who should not get a cold
letter at all.

Two things decide that:

  * who must not be written to — already replied, already bought, written off, an open
    opportunity, an unsendable address. None of those are quality judgements.
  * COOLDOWN_DAYS on the same channel, unless they replied.

The angle machinery is gone with the gates. Its real fault was not that changing the
copy is wrong — it is that the system changed it *by itself* on a bad number, then
parked 75 letters when it ran out of angles. Rewriting the pitch is Allen's call.
"""
from __future__ import annotations

import datetime as dt
import sqlite3

from app import sales_intelligence

# docs/75 R1. One number instead of the old escalating table (3 days, then 5, then 8),
# because one number is harder to argue around. A company that did not answer hears
# nothing on that channel for two weeks; a company that answered is not throttled at all.
COOLDOWN_DAYS = 14
FRESH_SIGNAL = 60

SCHEMA = """
CREATE TABLE IF NOT EXISTS followup_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id INTEGER NOT NULL,
    lead_no INTEGER NOT NULL,
    sequence_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    reason TEXT NOT NULL,
    score INTEGER,
    touch_count INTEGER NOT NULL DEFAULT 0,
    signal_confidence INTEGER NOT NULL DEFAULT 0,
    decided_at TEXT NOT NULL,
    applied INTEGER NOT NULL DEFAULT 0,
    next_due_date TEXT
);
CREATE INDEX IF NOT EXISTS idx_followup_decisions_enrollment
    ON followup_decisions(enrollment_id, decided_at DESC);
CREATE INDEX IF NOT EXISTS idx_followup_decisions_action
    ON followup_decisions(action, decided_at DESC);
"""


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def _today() -> dt.date:
    return dt.date.today()


def _ensure_audit_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Initialize evidence dependencies once before a decision batch.

    Sales Intelligence owns contacts/opportunities/activities/quotes/signals. The
    automatic sender calls this once per batch; standalone callers still get a complete
    safe initialization through evaluate()'s default `_ensure=True`.
    """
    sales_intelligence.ensure_schema(conn)
    _ensure_audit_schema(conn)


def _parse_date(value) -> dt.date | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return dt.datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return dt.date.fromisoformat(raw[:10])
        except ValueError:
            return None


def _spacing_days(_touches: int = 0) -> int:
    """Kept as a function so callers read the rule, not a bare literal."""
    return COOLDOWN_DAYS


def _latest_send(conn: sqlite3.Connection, lead_no: int) -> tuple[int, dt.date | None]:
    row = conn.execute(
        "SELECT COUNT(*) c, MAX(sent_at) latest FROM send_log"
        " WHERE lead_no=? AND channel='email'", (lead_no,),
    ).fetchone()
    log_count = int(row["c"] or 0)
    outreach = conn.execute(
        "SELECT COALESCE(touch_count,0) touches, message_sent_date"
        " FROM outreach WHERE lead_no=? AND channel='email' LIMIT 1", (lead_no,),
    ).fetchone()
    outreach_count = int(outreach["touches"] or 0) if outreach else 0
    latest = _parse_date(row["latest"])
    if outreach and _parse_date(outreach["message_sent_date"]):
        other = _parse_date(outreach["message_sent_date"])
        latest = max([d for d in (latest, other) if d is not None], default=None)
    return max(log_count, outreach_count), latest


def _best_signal(sales: dict | None) -> tuple[int, str | None]:
    signal = (sales or {}).get("best_signal") or {}
    if not signal:
        return 0, None
    return int(signal.get("confidence") or 0), signal.get("headline")


def _memory_context(conn: sqlite3.Connection, lead_no: int) -> list[str]:
    """Small audit context only; free prose never becomes an automatic stop command."""
    try:
        from app.agent import memory
        rows = memory.items(conn, lead_no)
    except Exception:  # schema may not exist in an old maintenance DB
        return []
    return [str(r.get("content") or "")[:180] for r in rows[-3:] if r.get("content")]


def evaluate(conn: sqlite3.Connection, enrollment_id: int,
             *, today: dt.date | None = None, _ensure: bool = True,
             weak_sequence_ids: set[int] | None = None) -> dict:
    """Return one of continue/delay/stop without mutating the enrollment."""
    if _ensure:
        ensure_schema(conn)
    today = today or _today()
    row = conn.execute(
        "SELECT e.id enrollment_id,e.lead_no,e.sequence_id,e.current_step,e.status,"
        " e.next_due_date,s.name sequence_name,s.channel,l.company_en,l.stage,"
        " COALESCE(l.do_not_contact,0) do_not_contact,l.email,l.email_status,"
        " COALESCE(st.subject,'') step_subject,st.body step_body"
        " FROM sequence_enrollments e JOIN sequences s ON s.id=e.sequence_id"
        " JOIN leads l ON l.no=e.lead_no"
        " JOIN sequence_steps st ON st.sequence_id=e.sequence_id AND st.step_order=e.current_step"
        " WHERE e.id=?", (enrollment_id,),
    ).fetchone()
    if row is None:
        return {"enrollment_id": enrollment_id, "action": "stop", "reason": "跟进记录不存在",
                "score": 0, "touch_count": 0, "signal_confidence": 0, "next_due_date": None,
                "memory": []}
    data = dict(row)
    no = data["lead_no"]
    if data["status"] != "active":
        return {**data, "action": "stop", "reason": f"跟进状态已是 {data['status']}",
                "score": 0, "touch_count": 0, "signal_confidence": 0,
                "next_due_date": None, "memory": _memory_context(conn, no)}
    if data["channel"] != "email":
        return {**data, "action": "continue", "reason": "非邮件渠道不受自动邮件质量策略控制",
                "score": 0, "touch_count": 0, "signal_confidence": 0,
                "next_due_date": None, "memory": []}

    # Strong ownership/consent facts always outrank timing or account scores.
    if data["do_not_contact"]:
        return {**data, "action": "stop", "reason": "客户已标记不再联系",
                "score": 0, "touch_count": 0, "signal_confidence": 0,
                "next_due_date": None, "memory": _memory_context(conn, no)}
    if str(data["stage"] or "new") in {"won", "lost"}:
        return {**data, "action": "stop", "reason": f"CRM 阶段为 {data['stage']}，停止冷跟进",
                "score": 0, "touch_count": 0, "signal_confidence": 0,
                "next_due_date": None, "memory": _memory_context(conn, no)}
    if conn.execute(
        "SELECT 1 FROM inbox_messages WHERE lead_no=? AND kind='reply' LIMIT 1", (no,),
    ).fetchone() or conn.execute(
        "SELECT 1 FROM outreach WHERE lead_no=? AND channel='email'"
        " AND (status='replied' OR reply_received=1) LIMIT 1", (no,),
    ).fetchone():
        return {**data, "action": "stop", "reason": "客户已经回复，冷跟进不再拥有下一步",
                "score": 0, "touch_count": 0, "signal_confidence": 0,
                "next_due_date": None, "memory": _memory_context(conn, no)}
    if conn.execute(
        "SELECT 1 FROM opportunities WHERE lead_no=? AND stage NOT IN ('won','lost') LIMIT 1", (no,),
    ).fetchone():
        return {**data, "action": "stop", "reason": "已有开放商机，后续应由商机流程负责",
                "score": 0, "touch_count": 0, "signal_confidence": 0,
                "next_due_date": None, "memory": _memory_context(conn, no)}
    if not data["email"] or str(data["email_status"] or "").lower() == "invalid":
        return {**data, "action": "stop", "reason": "邮件地址不可发送",
                "score": 0, "touch_count": 0, "signal_confidence": 0,
                "next_due_date": None, "memory": _memory_context(conn, no)}

    sales = sales_intelligence.score_lead(conn, no, _ensure=False)
    score = int((sales or {}).get("score") or 0)
    signal_confidence, signal_headline = _best_signal(sales)
    touches, latest = _latest_send(conn, no)
    memory_ctx = _memory_context(conn, no)

    # docs/75 R1 — the only reason left to hold a letter back for timing. Everything that
    # used to sit here (the first-touch quality gate, "this sequence has samples and no
    # replies", "N unanswered touches, change angle") judged whether the company was
    # worth writing to, and Allen removed that question from this module entirely.
    if latest:
        earliest = latest + dt.timedelta(days=COOLDOWN_DAYS)
        if earliest > today:
            return {**data, "action": "delay",
                    "reason": f"上一封是 {latest}，同渠道 {COOLDOWN_DAYS} 天内不再发",
                    "score": score, "touch_count": touches,
                    "signal_confidence": signal_confidence, "signal": signal_headline,
                    "next_due_date": earliest.isoformat(), "memory": memory_ctx}

    positives = [f"销售优先级 {score}/100"]
    if signal_confidence >= FRESH_SIGNAL:
        positives.append(f"采购信号 {signal_confidence}/100")
    return {**data, "action": "continue", "reason": "；".join(positives) + "，当前时机可继续跟进",
            "score": score, "touch_count": touches,
            "signal_confidence": signal_confidence, "signal": signal_headline,
            "next_due_date": None, "memory": memory_ctx}


def apply(conn: sqlite3.Connection, decision: dict, *, _ensure: bool = True) -> dict:
    """Apply only machine-owned sequence state and append an audit row."""
    if _ensure:
        _ensure_audit_schema(conn)
    action = decision["action"]
    enrollment_id = int(decision["enrollment_id"])
    applied = False
    next_due = decision.get("next_due_date")
    if action == "delay" and next_due:
        conn.execute(
            "UPDATE sequence_enrollments SET next_due_date=? WHERE id=? AND status='active'",
            (next_due, enrollment_id),
        )
        applied = True
    elif action == "stop":
        conn.execute(
            "UPDATE sequence_enrollments SET status='stopped' WHERE id=? AND status='active'",
            (enrollment_id,),
        )
        applied = True
    elif action == "continue":
        applied = True

    conn.execute(
        "INSERT INTO followup_decisions(enrollment_id,lead_no,sequence_id,action,reason,score,"
        " touch_count,signal_confidence,decided_at,applied,next_due_date)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (enrollment_id, int(decision.get("lead_no") or 0), int(decision.get("sequence_id") or 0),
         action, str(decision.get("reason") or "")[:600], int(decision.get("score") or 0),
         int(decision.get("touch_count") or 0), int(decision.get("signal_confidence") or 0),
         _now(), int(applied), next_due),
    )
    conn.commit()
    return {**decision, "applied": applied}


def evaluate_due(conn: sqlite3.Connection, enrollment_ids: list[int]) -> dict:
    ensure_schema(conn)
    from app.agent import oversight
    weak = oversight.weak_sequence_ids(conn)
    decisions = [evaluate(conn, int(eid), _ensure=False, weak_sequence_ids=weak)
                 for eid in enrollment_ids]
    counts = {key: 0 for key in ("continue", "delay", "stop")}
    for decision in decisions:
        counts[decision["action"]] = counts.get(decision["action"], 0) + 1
    return {"decisions": decisions, **counts}


def recent(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    _ensure_audit_schema(conn)
    return [dict(r) for r in conn.execute(
        "SELECT d.*,l.company_en,s.name sequence_name FROM followup_decisions d"
        " LEFT JOIN leads l ON l.no=d.lead_no LEFT JOIN sequences s ON s.id=d.sequence_id"
        " ORDER BY d.id DESC LIMIT ?", (max(1, min(int(limit), 500)),),
    ).fetchall()]
