import json

from fastapi import APIRouter, Depends, HTTPException

from app.main_deps import get_conn

router = APIRouter(prefix="/api/inbox")

VISIBLE_KINDS = ("reply", "unsubscribe", "auto", "attachment")
_VISIBLE_SQL = ",".join("?" for _ in VISIBLE_KINDS)


@router.get("")
def list_inbox(unread_only: int = 0, pending_only: int = 0,
               limit: int = 200, conn=Depends(get_conn)):
    from app import contacts
    contacts.ensure_schema(conn)
    sql = (
        "SELECT m.id, m.lead_no, m.contact_id, m.channel, m.kind, m.from_addr, m.subject, m.body,"
        "       m.received_at, m.is_read, m.handled_at, m.intent, m.intent_confidence,"
        "       m.rfc_message_id, m.attachments_json,"
        "       l.company_en, l.country,"
        "       c.name AS contact_name"
        " FROM inbox_messages m JOIN leads l ON l.no = m.lead_no"
        " LEFT JOIN contacts c ON c.id=m.contact_id"
        f" WHERE m.kind IN ({_VISIBLE_SQL})")
    params: list = [*VISIBLE_KINDS]
    if unread_only:
        sql += " AND m.is_read = 0"
    if pending_only:
        sql += " AND m.kind = 'reply' AND m.handled_at IS NULL"
    sql += " ORDER BY m.received_at DESC, m.id DESC LIMIT ?"
    params.append(limit)
    result = []
    for row in conn.execute(sql, params):
        item = dict(row)
        try:
            item["attachments"] = json.loads(item.pop("attachments_json") or "[]")
        except (TypeError, ValueError):
            item["attachments"] = []
        result.append(item)
    return result


@router.get("/unread_count")
def unread_count(conn=Depends(get_conn)):
    row = conn.execute(
        f"SELECT COUNT(*) c FROM inbox_messages WHERE is_read=0 AND kind IN ({_VISIBLE_SQL})",
        VISIBLE_KINDS,
    ).fetchone()
    return {"count": row["c"]}


@router.get("/pending_count")
def pending_count(conn=Depends(get_conn)):
    row = conn.execute(
        "SELECT COUNT(*) c FROM inbox_messages"
        " WHERE kind='reply' AND handled_at IS NULL"
    ).fetchone()
    return {"count": row["c"]}


@router.post("/{message_id}/read")
def mark_read(message_id: int, conn=Depends(get_conn)):
    cur = conn.execute("UPDATE inbox_messages SET is_read = 1 WHERE id = ?", (message_id,))
    conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="message not found")
    return {"ok": True}


@router.post("/{message_id}/handled")
def mark_handled(message_id: int, conn=Depends(get_conn)):
    cur = conn.execute(
        "UPDATE inbox_messages SET handled_at=datetime('now'), is_read=1"
        " WHERE id=? AND kind='reply'",
        (message_id,),
    )
    if cur.rowcount == 0:
        conn.commit()
        raise HTTPException(status_code=404, detail="actionable reply not found")
    from app import activities
    activities.complete_reply_task(conn, message_id)
    conn.commit()
    return {"ok": True}
