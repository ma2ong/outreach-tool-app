"""Spec 107 B1/B2: durable transport claims; uncertainty never auto-retries."""
import datetime as dt
import hashlib
import json


def ensure_schema(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS delivery_intents (
        id INTEGER PRIMARY KEY,
        enrollment_id INTEGER NOT NULL DEFAULT 0,
        step INTEGER NOT NULL DEFAULT 0,
        lead_no INTEGER NOT NULL,
        channel TEXT NOT NULL,
        target TEXT NOT NULL,
        subject TEXT,
        body TEXT NOT NULL,
        operation_key TEXT,
        source_kind TEXT NOT NULL DEFAULT 'sequence',
        source_id INTEGER,
        metadata_json TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        last_error TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")
    columns = {row[1] for row in conn.execute("PRAGMA table_info(delivery_intents)")}
    additions = {
        "operation_key": "TEXT",
        "source_kind": "TEXT NOT NULL DEFAULT 'sequence'",
        "source_id": "INTEGER",
        "metadata_json": "TEXT",
    }
    for name, declaration in additions.items():
        if name not in columns:
            conn.execute(f"ALTER TABLE delivery_intents ADD COLUMN {name} {declaration}")
    # The first sequence-only version treated every row as an enrollment. Replies use
    # enrollment_id=0, so keep the sequence mutex scoped to actual enrollments.
    conn.execute("DROP INDEX IF EXISTS delivery_unresolved_enrollment")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS delivery_unresolved_enrollment"
                 " ON delivery_intents(enrollment_id)"
                 " WHERE enrollment_id > 0 AND status IN ('pending','unknown')")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS delivery_unresolved_operation"
                 " ON delivery_intents(operation_key)"
                 " WHERE operation_key IS NOT NULL AND status IN ('pending','unknown')")
    conn.commit()


def claim(conn, item, *, target, subject=None, body, metadata: dict | None = None):
    """Commit before network I/O. A unique key rejects even stale queue snapshots."""
    stamp = dt.datetime.now(dt.UTC).isoformat()
    cur = conn.execute(
        "INSERT INTO delivery_intents(enrollment_id,step,lead_no,channel,target,"
        "subject,body,operation_key,source_kind,source_id,metadata_json,created_at,updated_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"
        " ON CONFLICT DO NOTHING",
        (item["enrollment_id"], item["current_step"], item["lead_no"],
         item["channel"], target, subject, body,
         f"sequence:{item['enrollment_id']}:{item['current_step']}", "sequence",
         item["enrollment_id"], json.dumps(metadata or {}, ensure_ascii=False), stamp, stamp))
    conn.commit()
    return cur.lastrowid if cur.rowcount else None


def claim_action(conn, *, operation_key: str, source_kind: str, source_id: int | None,
                 lead_no: int, channel: str, target: str, subject: str | None,
                 body: str, metadata: dict | None = None,
                 initialize: bool = True) -> int | None:
    """Claim a non-sequence send after all guards and before transport."""
    if initialize:
        ensure_schema(conn)
    stamp = dt.datetime.now(dt.UTC).isoformat()
    cur = conn.execute(
        "INSERT INTO delivery_intents(enrollment_id,step,lead_no,channel,target,subject,"
        " body,operation_key,source_kind,source_id,metadata_json,created_at,updated_at)"
        " VALUES (0,0,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
        (lead_no, channel, target, subject, body, operation_key, source_kind, source_id,
         json.dumps(metadata or {}, ensure_ascii=False), stamp, stamp),
    )
    conn.commit()
    return cur.lastrowid if cur.rowcount else None


def content_key(source_kind: str, *, lead_no: int, channel: str, target: str,
                subject: str | None, body: str, source_id: int | None = None) -> str:
    """Stable key for a rendered outbound action, without storing content in the key."""
    encoded = json.dumps(
        [lead_no, channel, target, subject or "", body],
        ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()[:24]
    owner = str(source_id) if source_id is not None else str(lead_no)
    return f"{source_kind}:{owner}:{digest}"


def claim_block_reason(conn, operation_key: str) -> str:
    row = conn.execute(
        "SELECT status,last_error FROM delivery_intents WHERE operation_key=?"
        " AND status IN ('pending','unknown') ORDER BY id DESC LIMIT 1",
        (operation_key,),
    ).fetchone()
    if row and row["last_error"]:
        return f"待核对上次发送结果：{row['last_error']}"
    return "这条消息已有待核对的发送结果，未重复发送"


def update_metadata(conn, intent_id: int, **patch) -> None:
    row = conn.execute(
        "SELECT metadata_json FROM delivery_intents WHERE id=?", (intent_id,)
    ).fetchone()
    if row is None:
        return
    try:
        metadata = json.loads(row["metadata_json"] or "{}")
    except (TypeError, ValueError):
        metadata = {}
    metadata.update(patch)
    conn.execute(
        "UPDATE delivery_intents SET metadata_json=?,updated_at=? WHERE id=?",
        (json.dumps(metadata, ensure_ascii=False), dt.datetime.now(dt.UTC).isoformat(), intent_id),
    )
    conn.commit()


def finish(conn, intent_id, *, error=None):
    conn.execute(
        "UPDATE delivery_intents SET status=?,last_error=?,updated_at=? WHERE id=?",
        ("unknown" if error else "sent", str(error)[:2000] if error else None,
         dt.datetime.now(dt.UTC).isoformat(), intent_id))
    conn.commit()


def unresolved(conn):
    ensure_schema(conn)
    return [dict(row) for row in conn.execute(
        "SELECT d.*,l.company_en FROM delivery_intents d"
        " LEFT JOIN leads l ON l.no=d.lead_no"
        " WHERE d.status IN ('pending','unknown') ORDER BY d.created_at")]


def resolve(conn, intent_id: int, outcome: str):
    """Human reconciliation is explicit; only not_sent makes a new claim possible."""
    if outcome not in ("sent", "not_sent"):
        raise ValueError("outcome must be sent or not_sent")
    ensure_schema(conn)
    row = conn.execute("SELECT * FROM delivery_intents WHERE id=?", (intent_id,)).fetchone()
    if row is None:
        raise LookupError("delivery intent not found")
    if row["status"] not in ("pending", "unknown"):
        return dict(row)
    if outcome == "sent":
        _reconcile_mailbox_counter(conn, dict(row))
    if outcome == "sent" and row["source_kind"] == "sequence":
        from app import campaigns, channel_outreach, outreach, sequences
        today = dt.date.today().isoformat()
        already_marked = conn.execute(
            "SELECT 1 FROM outreach WHERE lead_no=? AND channel=?"
            " AND status='messaged' AND message_sent_date=?",
            (row["lead_no"], row["channel"], today)).fetchone()
        if not already_marked:
            if row["channel"] == "email":
                outreach._mark_messaged(conn, row["lead_no"], today)
            else:
                channel_outreach._mark_messaged(conn, row["lead_no"], row["channel"], today)
        logged = conn.execute(
            "SELECT 1 FROM send_log WHERE lead_no=? AND channel=?"
            " AND COALESCE(subject,'')=COALESCE(?, '') AND COALESCE(body,'')=? LIMIT 1",
            (row["lead_no"], row["channel"], row["subject"], row["body"])).fetchone()
        enrollment = conn.execute(
            "SELECT e.current_step,s.name FROM sequence_enrollments e"
            " JOIN sequences s ON s.id=e.sequence_id WHERE e.id=?",
            (row["enrollment_id"],)).fetchone()
        if not logged:
            campaigns.log_send(
                conn, row["lead_no"], row["channel"],
                f"序列:{enrollment['name']}" if enrollment else "序列:人工核对",
                subject=row["subject"], body=row["body"],
                variant=enrollment["name"] if enrollment else None, step=row["step"])
        if enrollment and enrollment["current_step"] == row["step"]:
            sequences.advance_enrollment(conn, row["enrollment_id"])
    elif outcome == "sent" and row["source_kind"] == "reply":
        _reconcile_reply(conn, dict(row))
    elif outcome == "sent" and row["source_kind"] in {
            "email_campaign", "channel_campaign", "social_queue", "social_prepared"}:
        _reconcile_outbound(conn, dict(row))
    if row["source_kind"] == "reply" and row["source_id"]:
        stamp = dt.datetime.now(dt.UTC).isoformat()
        if outcome == "sent":
            conn.execute(
                "UPDATE agent_proposals SET status='executed',executed_at=?,"
                " execution_result=?,updated_at=? WHERE id=?",
                (stamp, "人工核对：消息已发送，CRM 状态已补记", stamp, row["source_id"]),
            )
        else:
            conn.execute(
                "UPDATE agent_proposals SET status='pending',decided_at=NULL,executed_at=NULL,"
                " execution_result=NULL,updated_at=? WHERE id=?",
                (stamp, row["source_id"]),
            )
    conn.execute("UPDATE delivery_intents SET status=?,last_error=NULL,updated_at=? WHERE id=?",
                 (outcome, dt.datetime.now(dt.UTC).isoformat(), intent_id))
    conn.commit()
    return dict(conn.execute("SELECT * FROM delivery_intents WHERE id=?", (intent_id,)).fetchone())


def _reconcile_outbound(conn, intent: dict) -> None:
    """Repair a confirmed campaign/queue send without entering any transport."""
    from app import campaigns, channel_outreach, outreach

    try:
        metadata = json.loads(intent.get("metadata_json") or "{}")
    except (TypeError, ValueError):
        metadata = {}
    current = conn.execute(
        "SELECT status,message_sent_date FROM outreach WHERE lead_no=? AND channel=?",
        (intent["lead_no"], intent["channel"]),
    ).fetchone()
    # A reply may arrive while Allen is reconciling the earlier send. Never downgrade
    # that stronger customer state back to merely messaged.
    if current is None or current["status"] != "replied":
        today = dt.date.today().isoformat()
        if intent["channel"] == "email":
            outreach._mark_messaged(conn, intent["lead_no"], today)
        else:
            channel_outreach._mark_messaged(
                conn, intent["lead_no"], intent["channel"], today)
    logged = conn.execute(
        "SELECT 1 FROM send_log WHERE lead_no=? AND channel=?"
        " AND COALESCE(subject,'')=COALESCE(?, '') AND COALESCE(body,'')=? LIMIT 1",
        (intent["lead_no"], intent["channel"], intent["subject"], intent["body"]),
    ).fetchone()
    if not logged:
        campaigns.log_send(
            conn, intent["lead_no"], intent["channel"],
            metadata.get("campaign") or campaigns.default_label(intent["channel"]),
            subject=intent["subject"], body=intent["body"],
            variant=metadata.get("variant"),
        )
    queue_id = metadata.get("queue_id")
    if queue_id:
        conn.execute(
            "UPDATE social_dm_queue SET status='sent' WHERE id=? AND status='ready'",
            (queue_id,),
        )
        conn.commit()


def _reconcile_mailbox_counter(conn, intent: dict) -> None:
    """Reserve one mailbox slot for any email Allen confirms was delivered."""
    if intent.get("channel") != "email":
        return
    from app import mailboxes
    try:
        metadata = json.loads(intent.get("metadata_json") or "{}")
    except (TypeError, ValueError):
        metadata = {}
    if metadata.get("mailbox_id") and not metadata.get("mailbox_counted"):
        mailboxes.record_send(conn, int(metadata["mailbox_id"]))
        update_metadata(conn, intent["id"], mailbox_counted=True)


def _reconcile_reply(conn, intent: dict) -> None:
    """Repair CRM state only. Never enter a transport during human reconciliation."""
    from app import repository
    from app.agent import conversation, proposals

    try:
        metadata = json.loads(intent.get("metadata_json") or "{}")
    except (TypeError, ValueError):
        metadata = {}
    proposal = proposals.get(conn, int(intent.get("source_id") or 0)) or {}
    payload = proposal.get("payload") or {}
    inbox_id = proposal.get("inbox_message_id") or metadata.get("inbox_message_id")
    if inbox_id:
        conn.execute(
            "UPDATE inbox_messages SET handled_at=COALESCE(handled_at,?),is_read=1 WHERE id=?",
            (dt.datetime.now(dt.UTC).isoformat(), inbox_id),
        )
        conn.commit()
    state = conversation.get(conn, intent["lead_no"], intent["channel"])
    if not state or state.get("source_message_id") != inbox_id or state.get("state") == "waiting_us":
        conversation.record_sent_reply(
            conn, intent["lead_no"], intent["channel"], inbox_id,
            payload.get("open_questions") or "",
            is_followup=payload.get("followup_kind") == "warm",
        )
    note_text = (
        f"{intent['channel']} 回复（Agent 起草，人工核对为已发送）：{intent['body'][:300]}"
    )
    if not conn.execute(
        "SELECT 1 FROM notes WHERE lead_no=? AND text=? LIMIT 1",
        (intent["lead_no"], note_text),
    ).fetchone():
        repository.add_note(conn, intent["lead_no"], note_text)
