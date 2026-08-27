"""Deterministic worth-now policy for automatic email sequence follow-up.

A sequence due date is permission to consider a follow-up, not permission to send one.
This module decides whether automatic follow-up should continue, wait, change angle or
stop. It never writes customer-facing copy and never interprets silence as rejection.

Sequence step zero is still a first touch. It reuses PR #20's stricter first-touch gate
(with only the current enrollment ignored as a blocker) so sequences cannot become a
back door around autonomous first-touch quality.
"""
from __future__ import annotations

import datetime as dt
import sqlite3

from app import sales_intelligence

MIN_FOLLOWUP_SCORE = 50
HOLD_SCORE = 35
ANGLE_AFTER_UNANSWERED = 3
FRESH_SIGNAL = 60
STRONG_FRESH_SIGNAL = 70

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


def _spacing_days(touches: int) -> int:
    if touches <= 1:
        return 3
    if touches == 2:
        return 5
    return 8


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
    """Return one of continue/delay/change_angle/stop without mutating the enrollment."""
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

    # Compute Oversight once for an automatic batch; standalone evaluation remains safe.
    if weak_sequence_ids is None:
        from app.agent import oversight
        weak_sequence_ids = oversight.weak_sequence_ids(conn)
    if data["sequence_id"] in weak_sequence_ids:
        return {**data, "action": "change_angle",
                "reason": "当前序列已有足够发送样本但零回复，停止重复同一角度",
                "score": score, "touch_count": touches,
                "signal_confidence": signal_confidence, "signal": signal_headline,
                "next_due_date": None, "memory": memory_ctx}

    # Sequence step zero is a first touch, not a follow-up. Reuse PR #20 exactly, with
    # this enrollment ignored so it does not disqualify itself.
    if int(data["current_step"] or 0) == 0 and touches == 0:
        from app.agent import send_decision
        first = send_decision.evaluate(
            conn, no, subject=data["step_subject"], body=data["step_body"],
            sales=sales, allow_active_sequence=True,
        )
        if not first["ready"]:
            return {**data, "action": "change_angle",
                    "reason": "序列首封未通过自主首触质量门：" + "；".join(first["blockers"][:4]),
                    "score": score, "touch_count": 0,
                    "signal_confidence": signal_confidence, "signal": signal_headline,
                    "next_due_date": None, "memory": memory_ctx,
                    "first_touch_decision": send_decision.compact(first)}
        return {**data, "action": "continue",
                "reason": "序列首封通过 PR #20 自主首触质量门",
                "score": score, "touch_count": 0,
                "signal_confidence": signal_confidence, "signal": signal_headline,
                "next_due_date": None, "memory": memory_ctx,
                "first_touch_decision": send_decision.compact(first)}

    # Repeated silence changes the angle, never the inferred intent.
    if touches >= ANGLE_AFTER_UNANSWERED and signal_confidence < FRESH_SIGNAL:
        return {**data, "action": "change_angle",
                "reason": f"已连续 {touches} 次邮件触达无真人回复且没有新的高可信采购信号，先换角度",
                "score": score, "touch_count": touches,
                "signal_confidence": signal_confidence, "signal": signal_headline,
                "next_due_date": None, "memory": memory_ctx}

    if score < HOLD_SCORE:
        return {**data, "action": "change_angle",
                "reason": f"当前销售优先级仅 {score}/100，继续同一冷序列价值过低，先补证据",
                "score": score, "touch_count": touches,
                "signal_confidence": signal_confidence, "signal": signal_headline,
                "next_due_date": None, "memory": memory_ctx}
    if score < MIN_FOLLOWUP_SCORE:
        delayed_to = today + dt.timedelta(days=14)
        return {**data, "action": "delay",
                "reason": f"销售优先级 {score}/100，未达到自主跟进阈值 {MIN_FOLLOWUP_SCORE}，14 天后重评",
                "score": score, "touch_count": touches,
                "signal_confidence": signal_confidence, "signal": signal_headline,
                "next_due_date": delayed_to.isoformat(), "memory": memory_ctx}

    # Fresh strong intent may follow the sequence's explicit due date; otherwise enforce
    # a minimum gap from the last actual send so an old/bad due date cannot cause spam.
    if latest and signal_confidence < STRONG_FRESH_SIGNAL:
        earliest = latest + dt.timedelta(days=_spacing_days(touches))
        if earliest > today:
            return {**data, "action": "delay",
                    "reason": f"距上次邮件太近；按第 {max(1, touches)} 次触达节奏至少间隔 {_spacing_days(touches)} 天",
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


# Angle N of a language lives in a sequence whose name ends with 角度N; the first angle
# has no suffix. Adding a new angle means adding a sequence, not editing a list here.
_ANGLE_SUFFIX = "·角度"


def _switch_angle(conn, enrollment_id: int) -> bool:
    """Re-open this follow-up on the next angle for the same language, if there is one."""
    row = conn.execute(
        "SELECT e.id, s.name FROM sequence_enrollments e"
        " JOIN sequences s ON s.id = e.sequence_id WHERE e.id=?", (enrollment_id,)).fetchone()
    if row is None:
        return False
    # 冷邮件 3 步跟进（英语） and 冷邮件 3 步跟进（英语·角度二） share everything up to the
    # closing bracket, so the bracket has to come off before the prefix will match.
    base = row["name"].split(_ANGLE_SUFFIX)[0].rstrip("）)")
    nxt = conn.execute(
        "SELECT id FROM sequences WHERE name LIKE ? AND name <> ? ORDER BY id LIMIT 1",
        (f"{base}{_ANGLE_SUFFIX}%", row["name"])).fetchone()
    if nxt is None:
        return False   # angles exhausted — parking is a real answer now, and reportable
    conn.execute(
        "UPDATE sequence_enrollments SET sequence_id=?, current_step=0, status='active',"
        " next_due_date=date('now') WHERE id=? AND status='active'",
        (nxt["id"], enrollment_id))
    return True


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
    elif action == "change_angle":
        # Move to the next angle rather than parking (docs/67 R3). Parking was half a
        # decision: the system correctly saw the angle was not working, then stopped
        # instead of changing it, and 110 follow-ups sat still for weeks.
        moved = _switch_angle(conn, enrollment_id)
        if not moved:
            conn.execute(
                "UPDATE sequence_enrollments SET status='quality_hold'"
                " WHERE id=? AND status='active'", (enrollment_id,))
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
    counts = {key: 0 for key in ("continue", "delay", "change_angle", "stop")}
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
