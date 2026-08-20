"""Durable ownership and next-action state for each customer conversation."""
from __future__ import annotations

import datetime as dt

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversation_states (
    lead_no INTEGER NOT NULL,
    channel TEXT NOT NULL,
    owner TEXT NOT NULL,
    state TEXT NOT NULL,
    reason TEXT,
    source_message_id INTEGER,
    next_action TEXT,
    due_at TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (lead_no, channel)
);
CREATE TABLE IF NOT EXISTS conversation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_no INTEGER NOT NULL,
    channel TEXT NOT NULL,
    owner TEXT NOT NULL,
    state TEXT NOT NULL,
    reason TEXT,
    source_message_id INTEGER,
    next_action TEXT,
    due_at TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conversation_owner ON conversation_states(owner, state);
CREATE INDEX IF NOT EXISTS idx_conversation_events ON conversation_events(lead_no, channel, id);
"""

OWNERS = ("agent", "allen")
STATES = ("waiting_us", "waiting_customer", "human_takeover", "closed")


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def ensure_schema(conn) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def set_state(conn, lead_no: int, channel: str, *, owner: str, state: str,
              reason: str = "", source_message_id: int | None = None,
              next_action: str = "", due_at: str | None = None) -> dict:
    ensure_schema(conn)
    if owner not in OWNERS or state not in STATES:
        raise ValueError("invalid conversation owner/state")
    now = _now()
    values = (lead_no, channel, owner, state, reason[:500], source_message_id,
              next_action[:300], due_at, now)
    conn.execute(
        "INSERT INTO conversation_states(lead_no,channel,owner,state,reason,"
        " source_message_id,next_action,due_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)"
        " ON CONFLICT(lead_no,channel) DO UPDATE SET owner=excluded.owner,state=excluded.state,"
        " reason=excluded.reason,source_message_id=excluded.source_message_id,"
        " next_action=excluded.next_action,due_at=excluded.due_at,updated_at=excluded.updated_at",
        values,
    )
    conn.execute(
        "INSERT INTO conversation_events(lead_no,channel,owner,state,reason,"
        " source_message_id,next_action,due_at,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        values,
    )
    conn.commit()
    return get(conn, lead_no, channel)


def get(conn, lead_no: int, channel: str) -> dict | None:
    ensure_schema(conn)
    row = conn.execute(
        "SELECT * FROM conversation_states WHERE lead_no=? AND channel=?",
        (lead_no, channel),
    ).fetchone()
    return dict(row) if row else None


def takeover(conn, lead_no: int, channel: str, reason: str,
             source_message_id: int | None = None, next_action: str = "Allen 接手处理") -> dict:
    return set_state(conn, lead_no, channel, owner="allen", state="human_takeover",
                     reason=reason, source_message_id=source_message_id,
                     next_action=next_action, due_at=dt.date.today().isoformat())


def resume(conn, lead_no: int, channel: str) -> dict:
    return set_state(conn, lead_no, channel, owner="agent", state="waiting_customer",
                     reason="Allen 已明确把后续交回 Agent")


def waiting_us(conn, lead_no: int, channel: str, source_message_id: int) -> dict:
    return set_state(conn, lead_no, channel, owner="agent", state="waiting_us",
                     reason="客户消息等待回复", source_message_id=source_message_id,
                     next_action="回复客户")


def record_sent_reply(conn, lead_no: int, channel: str, source_message_id: int | None,
                      open_questions: str = "") -> dict:
    """A sent reply transfers the turn to the customer and schedules any promise."""
    question = (open_questions or "").strip()
    due = None
    next_action = ""
    if question:
        from app import activities
        due = (dt.date.today() + dt.timedelta(days=1)).isoformat()
        next_action = f"补充回答：{question}"[:300]
        activities.create(conn, lead_no, {
            "title": next_action,
            "type": "task", "due_at": due, "priority": "high",
            "note": "这项内容在已发回复中仍未回答；Agent 已记录承诺，避免忘记补充。",
        })
    return set_state(conn, lead_no, channel, owner="agent", state="waiting_customer",
                     reason="已回复，等待客户下一步", source_message_id=source_message_id,
                     next_action=next_action, due_at=due)


def takeovers(conn) -> list[dict]:
    ensure_schema(conn)
    return [dict(row) for row in conn.execute(
        "SELECT c.*,l.company_en,l.country FROM conversation_states c"
        " JOIN leads l ON l.no=c.lead_no"
        " WHERE c.owner='allen' AND c.state='human_takeover'"
        " ORDER BY c.updated_at DESC"
    )]
