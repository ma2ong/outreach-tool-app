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
    followup_count INTEGER NOT NULL DEFAULT 0,
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
    followup_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conversation_owner ON conversation_states(owner, state);
CREATE INDEX IF NOT EXISTS idx_conversation_events ON conversation_events(lead_no, channel, id);
"""

OWNERS = ("agent", "allen")
STATES = ("waiting_us", "waiting_customer", "human_takeover", "closed")
WARM_FOLLOWUP_DAYS = 7
MAX_WARM_FOLLOWUPS = 2


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def ensure_schema(conn) -> None:
    conn.executescript(SCHEMA)
    for table in ("conversation_states", "conversation_events"):
        columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        if "followup_count" not in columns:
            conn.execute(
                f"ALTER TABLE {table} ADD COLUMN followup_count INTEGER NOT NULL DEFAULT 0"
            )
    conn.commit()


def set_state(conn, lead_no: int, channel: str, *, owner: str, state: str,
              reason: str = "", source_message_id: int | None = None,
              next_action: str = "", due_at: str | None = None,
              followup_count: int | None = None) -> dict:
    ensure_schema(conn)
    if owner not in OWNERS or state not in STATES:
        raise ValueError("invalid conversation owner/state")
    current = conn.execute(
        "SELECT followup_count FROM conversation_states WHERE lead_no=? AND channel=?",
        (lead_no, channel),
    ).fetchone()
    count = int(current["followup_count"] or 0) if current and followup_count is None else int(followup_count or 0)
    now = _now()
    values = (lead_no, channel, owner, state, reason[:500], source_message_id,
              next_action[:300], due_at, count, now)
    conn.execute(
        "INSERT INTO conversation_states(lead_no,channel,owner,state,reason,"
        " source_message_id,next_action,due_at,followup_count,updated_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)"
        " ON CONFLICT(lead_no,channel) DO UPDATE SET owner=excluded.owner,state=excluded.state,"
        " reason=excluded.reason,source_message_id=excluded.source_message_id,"
        " next_action=excluded.next_action,due_at=excluded.due_at,"
        " followup_count=excluded.followup_count,updated_at=excluded.updated_at",
        values,
    )
    conn.execute(
        "INSERT INTO conversation_events(lead_no,channel,owner,state,reason,"
        " source_message_id,next_action,due_at,followup_count,created_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
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
    due = (dt.date.today() + dt.timedelta(days=WARM_FOLLOWUP_DAYS)).isoformat()
    return set_state(conn, lead_no, channel, owner="agent", state="waiting_customer",
                     reason="Allen 已明确把后续交回 Agent",
                     next_action="若客户仍无回复，7 天后准备简短跟进", due_at=due)


def reschedule(conn, lead_no: int, channel: str, *, next_action: str,
               due_at: str) -> dict:
    """Adjust the one durable next action without changing who owns the customer."""
    action = (next_action or "").strip()
    if not action:
        raise ValueError("下一步动作不能为空")
    try:
        dt.date.fromisoformat(due_at)
    except (TypeError, ValueError) as exc:
        raise ValueError("下一步日期必须是 YYYY-MM-DD") from exc
    current = get(conn, lead_no, channel)
    if not current:
        raise ValueError("这个渠道还没有可调整的会话状态")
    reason = (current.get("reason") or "保留当前会话状态").strip()
    if "Allen 调整下一步安排" not in reason:
        reason = f"{reason}；Allen 调整下一步安排"
    return set_state(
        conn, lead_no, channel,
        owner=current["owner"], state=current["state"], reason=reason,
        source_message_id=current.get("source_message_id"), next_action=action,
        due_at=due_at, followup_count=current.get("followup_count"),
    )


def waiting_us(conn, lead_no: int, channel: str, source_message_id: int, *,
               reset_followups: bool = True) -> dict:
    return set_state(conn, lead_no, channel, owner="agent", state="waiting_us",
                     reason="客户消息等待回复", source_message_id=source_message_id,
                     next_action="回复客户",
                     followup_count=0 if reset_followups else None)


def record_sent_reply(conn, lead_no: int, channel: str, source_message_id: int | None,
                      open_questions: str = "", *, is_followup: bool = False) -> dict:
    """A sent reply transfers the turn to the customer and schedules any promise."""
    question = (open_questions or "").strip()
    current = get(conn, lead_no, channel)
    count = int((current or {}).get("followup_count") or 0) + (1 if is_followup else 0)
    if question:
        from app import activities
        due = (dt.date.today() + dt.timedelta(days=1)).isoformat()
        next_action = f"补充回答：{question}"[:300]
        activities.create_commitment_task(conn, lead_no, source_message_id, question, due)
        return set_state(
            conn, lead_no, channel, owner="allen", state="human_takeover",
            reason="已发回复中有待兑现承诺，需要 Allen 提供或确认可靠信息",
            source_message_id=source_message_id, next_action=next_action,
            due_at=due, followup_count=count,
        )
    if count >= MAX_WARM_FOLLOWUPS:
        return set_state(
            conn, lead_no, channel, owner="agent", state="closed",
            reason="本轮客户回复后已完成两次暖跟进；等待新消息或新信号再唤醒",
            source_message_id=source_message_id, followup_count=count,
        )
    due = (dt.date.today() + dt.timedelta(days=WARM_FOLLOWUP_DAYS)).isoformat()
    return set_state(conn, lead_no, channel, owner="agent", state="waiting_customer",
                     reason="已回复，等待客户下一步", source_message_id=source_message_id,
                     next_action="若客户仍无回复，7 天后准备简短跟进", due_at=due,
                     followup_count=count)


def due_followups(conn, *, today: dt.date | None = None, limit: int = 5) -> list[dict]:
    """Customer turns whose bounded warm follow-up is due and not already covered."""
    from app.agent import proposals

    ensure_schema(conn)
    proposals.ensure_schema(conn)
    today = today or dt.date.today()
    rows = conn.execute(
        "SELECT m.*,l.company_en,l.country,c.followup_count,c.due_at AS followup_due_at"
        " FROM conversation_states c"
        " JOIN inbox_messages m ON m.id=c.source_message_id"
        " JOIN leads l ON l.no=c.lead_no"
        " WHERE c.owner='agent' AND c.state='waiting_customer'"
        " AND c.due_at IS NOT NULL AND c.due_at<=? AND c.followup_count<?"
        " AND COALESCE(l.do_not_contact,0)=0 AND m.kind='reply'"
        " AND NOT EXISTS (SELECT 1 FROM inbox_messages newer"
        "                 WHERE newer.lead_no=c.lead_no AND newer.channel=c.channel"
        "                   AND newer.kind='reply' AND newer.id>m.id)"
        " AND NOT EXISTS (SELECT 1 FROM agent_proposals p"
        "                 WHERE p.inbox_message_id=m.id AND p.kind='reply_draft'"
        "                   AND p.status IN ('pending','approved','edited_approved'))"
        " ORDER BY c.due_at,c.lead_no LIMIT ?",
        (today.isoformat(), MAX_WARM_FOLLOWUPS, max(1, min(int(limit), 20))),
    ).fetchall()
    return [dict(row) for row in rows]


def reconcile_followup_states(conn, *, limit: int = 100) -> dict:
    """Resolve terminal warm drafts so waiting_us cannot become a permanent dead end."""
    from app.agent import proposals

    ensure_schema(conn)
    proposals.ensure_schema(conn)
    states = conn.execute(
        "SELECT * FROM conversation_states WHERE owner='agent' AND state='waiting_us'"
        " AND source_message_id IS NOT NULL ORDER BY updated_at LIMIT ?",
        (max(1, min(int(limit), 500)),),
    ).fetchall()
    closed = handed_off = unresolved = 0
    has_delivery_table = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='delivery_intents'"
    ).fetchone() is not None
    for state_row in states:
        state = dict(state_row)
        proposal = None
        ids = conn.execute(
            "SELECT id FROM agent_proposals WHERE kind='reply_draft'"
            " AND inbox_message_id=? ORDER BY id DESC",
            (state["source_message_id"],),
        ).fetchall()
        for row in ids:
            candidate = proposals.get(conn, row["id"])
            if ((candidate or {}).get("payload") or {}).get("followup_kind") == "warm":
                proposal = candidate
                break
        if not proposal or proposal["status"] in proposals.OPEN_STATUSES:
            continue
        if proposal["status"] in ("rejected", "expired"):
            set_state(
                conn, state["lead_no"], state["channel"], owner="agent", state="closed",
                reason=("Allen 已驳回本次暖跟进" if proposal["status"] == "rejected"
                        else "暖跟进草稿已过期，不再追发"),
                source_message_id=state["source_message_id"],
                followup_count=state["followup_count"],
            )
            closed += 1
            continue
        if proposal["status"] == "failed":
            pending = has_delivery_table and conn.execute(
                "SELECT 1 FROM delivery_intents WHERE source_kind='reply' AND source_id=?"
                " AND status IN ('pending','unknown')",
                (proposal["id"],),
            ).fetchone()
            if pending:
                unresolved += 1
                continue
            set_state(
                conn, state["lead_no"], state["channel"], owner="allen",
                state="human_takeover", reason="暖跟进未发送且执行失败，需要 Allen 处理",
                source_message_id=state["source_message_id"],
                next_action=f"检查失败的暖跟进提议 #{proposal['id']}",
                due_at=dt.date.today().isoformat(), followup_count=state["followup_count"],
            )
            handed_off += 1
    return {"closed": closed, "handed_off": handed_off, "unresolved": unresolved}


def takeovers(conn) -> list[dict]:
    ensure_schema(conn)
    return [dict(row) for row in conn.execute(
        "SELECT c.*,l.company_en,l.country FROM conversation_states c"
        " JOIN leads l ON l.no=c.lead_no"
        " WHERE c.owner='allen' AND c.state='human_takeover'"
        " ORDER BY c.updated_at DESC"
    )]
