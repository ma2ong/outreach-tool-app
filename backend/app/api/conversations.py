"""Per-customer correspondence: the timeline, and replying into it (docs/56)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.main_deps import get_conn

router = APIRouter(prefix="/api/conversations")


class Reply(BaseModel):
    body: str
    subject: str | None = None
    # Set only after the guard has already refused once and Allen chose to send anyway.
    override: bool = False


@router.get("")
def list_conversations(waiting_only: int = 0, limit: int = 100, conn=Depends(get_conn)):
    """Customers with any correspondence, the ones we owe a reply to first.

    Ordering is the whole point of the list: `waiting_us` means the ball is on our side,
    and that is the only group where looking at it should lead to doing something.
    """
    from app.agent.conversation import ensure_schema

    ensure_schema(conn)
    sql = """
        SELECT l.no, l.company_en, l.country, l.stage,
               cs.owner, cs.state, cs.next_action, cs.due_at,
               (SELECT COUNT(*) FROM send_log s WHERE s.lead_no=l.no) AS sent_count,
               (SELECT COUNT(*) FROM inbox_messages m
                 WHERE m.lead_no=l.no AND m.kind='reply') AS reply_count,
               (SELECT COUNT(*) FROM inbox_messages m
                 WHERE m.lead_no=l.no AND m.kind='reply' AND m.is_read=0) AS unread,
               MAX(COALESCE((SELECT MAX(s.sent_at) FROM send_log s WHERE s.lead_no=l.no), ''),
                   COALESCE((SELECT MAX(m.received_at) FROM inbox_messages m
                              WHERE m.lead_no=l.no), '')) AS last_at
        FROM leads l
        LEFT JOIN conversation_states cs ON cs.lead_no = l.no
        WHERE EXISTS (SELECT 1 FROM send_log s WHERE s.lead_no=l.no)
           OR EXISTS (SELECT 1 FROM inbox_messages m WHERE m.lead_no=l.no)
    """
    if waiting_only:
        sql += " AND (cs.state='waiting_us' OR (cs.state IS NULL AND unread > 0))"
    sql += """
        ORDER BY CASE WHEN cs.state='waiting_us' THEN 0
                      WHEN unread > 0 THEN 1 ELSE 2 END,
                 last_at DESC
        LIMIT ?
    """
    return [dict(r) for r in conn.execute(sql, (limit,))]


@router.get("/{no}")
def get_conversation(no: int, conn=Depends(get_conn)):
    from app import conversation_view
    from app.agent import project_facts

    lead = conn.execute(
        "SELECT no, company_en, company_local, country, email, contact_name, title,"
        " stage, tags, do_not_contact FROM leads WHERE no=?", (no,)).fetchone()
    if lead is None:
        raise HTTPException(404, "线索不存在")
    return {
        "lead": dict(lead),
        **conversation_view.summary(conn, no),
        "requirements": project_facts.for_lead(conn, no),
    }


@router.post("/{no}/reply")
def send_reply(no: int, payload: Reply, conn=Depends(get_conn)):
    """Reply by email, down the same path the Agent sends on.

    A hand-written reply feels safer than an automated one and is not: the guard exists
    because pricing must not go out this way, and Allen is the one likely to type a
    price. Overriding is allowed but has to be said out loud (docs/56 R3).
    """
    from app import campaigns, message_guard
    from app.agent import conversation as conversation_state
    from app.api import send as send_api

    lead = conn.execute("SELECT * FROM leads WHERE no=?", (no,)).fetchone()
    if lead is None:
        raise HTTPException(404, "线索不存在")
    if not lead["email"]:
        raise HTTPException(400, "这条线索没有邮箱地址")
    if lead["do_not_contact"]:
        raise HTTPException(400, "这个客户标了不再联系")

    body = payload.body.strip()
    if not body:
        raise HTTPException(400, "回复内容是空的")
    subject = (payload.subject or "").strip()
    if not subject:
        latest = conn.execute(
            "SELECT subject FROM inbox_messages WHERE lead_no=? AND kind='reply'"
            " AND COALESCE(subject,'')!='' ORDER BY received_at DESC, id DESC LIMIT 1",
            (no,),
        ).fetchone()
        original = str(latest["subject"] if latest else "LED display").strip()
        subject = original if original.lower().startswith("re:") else f"Re: {original}"

    # This is an answer inside an existing conversation, not a cold first touch. Keep
    # every commercial/safety rule, but do not demand first-touch personalization.
    verdict = message_guard.check(body, dict(lead), subject=subject, step_order=1)
    if verdict.blocked and not payload.override:
        # 428: the request is fine, it needs a decision first.
        raise HTTPException(428, {"reason": verdict.reason, "detail": verdict.detail})

    # The same rotating sender the daily run uses: one mailbox, one set of caps.
    send_api.pick_sender(conn)(lead["email"], subject, body, None)
    campaigns.log_send(conn, no, "email", "手动回复", subject=subject, body=body)
    # A conversation a person has answered is a conversation the Agent stops driving.
    conversation_state.set_state(
        conn, no, "email", owner="allen", state="human_takeover",
        reason="Allen 在客户对话里手动回复")
    conn.commit()
    return {"ok": True, "overridden": bool(verdict.blocked)}
