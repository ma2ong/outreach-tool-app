import datetime as dt

import pytest

from app.agent import conversation, draft, proposals, run


def _reply(conn, *, intent="spec", channel="email", body="Please send specs."):
    cur = conn.execute(
        "INSERT INTO inbox_messages(lead_no,channel,kind,from_addr,subject,body,received_at,"
        " intent,intent_confidence) VALUES (1,?,'reply','buyer@alpha.com','Re: LED',?,?,?,90)",
        (channel, body, dt.datetime.now(dt.UTC).isoformat(), intent),
    )
    conn.commit()
    return cur.lastrowid


def _draft_result():
    return {
        "subject": "Re: LED", "body": "I will send the missing scan tomorrow.",
        "language": "en", "evidence": [], "open_questions": "cabinet drawing",
        "warnings": [],
        "context": {"lead": {"no": 1}, "quotes": [], "opportunities": [],
                    "history": [], "message": {}},
    }


def test_quote_or_negotiation_immediately_transfers_conversation_to_allen(conn):
    mid = _reply(conn, intent="quote", body="Quote 200sqm outdoor P4.")
    run.act_on_replies(conn)
    state = conversation.get(conn, 1, "email")
    assert state["owner"] == "allen" and state["state"] == "human_takeover"
    assert state["source_message_id"] == mid and "报价" in state["next_action"]


def test_agent_never_drafts_a_later_message_while_allen_owns_the_channel(conn,
                                                                         monkeypatch):
    _reply(conn, intent="quote")
    run.act_on_replies(conn)
    later = _reply(conn, intent="spec", body="Also send the cabinet drawing.")
    monkeypatch.setattr(draft, "build", lambda *a: pytest.fail("Allen owns this thread"))
    result = run.act_on_replies(conn)
    assert result["nudge"] == 1 and result["draft"] == 0
    p = next(p for p in proposals.list_proposals(conn) if p["inbox_message_id"] == later)
    assert p["kind"] == "create_task" and "你正在接管" in p["title"]


def test_explicit_resume_returns_future_simple_replies_to_the_agent(conn, monkeypatch):
    conversation.takeover(conn, 1, "email", "strategic account")
    conversation.resume(conn, 1, "email")
    _reply(conn, intent="spec")
    monkeypatch.setattr(draft, "build", lambda *a: _draft_result())
    monkeypatch.setattr("app.agent.memory.update", lambda *a: "")
    assert run.act_on_replies(conn)["draft"] == 1
    assert conversation.get(conn, 1, "email")["state"] == "waiting_us"


def test_a_sent_reply_records_waiting_state_and_the_promised_next_action(conn,
                                                                         monkeypatch):
    conn.execute(
        "INSERT INTO mailboxes(email,smtp_host,port,username,password,active)"
        " VALUES ('allen@mc.com','smtp.mc.com',465,'allen@mc.com','pw',1)")
    conn.commit()
    monkeypatch.setattr("app.channels.email_adapter.send_via", lambda *a, **k: None)
    mid = _reply(conn)
    p = proposals.create(
        conn, "reply_draft", lead_no=1, inbox_message_id=mid, title="Reply",
        payload={"channel": "email", "to": "buyer@alpha.com", "subject": "Re: LED",
                 "body": "I will confirm tomorrow.", "open_questions": "cabinet drawing",
                 "mailbox_email": "allen@mc.com"},
    )
    assert conversation.get(conn, 1, "email") is None
    done = proposals.approve(conn, p["id"])
    assert done["status"] == "executed"
    state = conversation.get(conn, 1, "email")
    assert state["state"] == "waiting_customer" and state["owner"] == "agent"
    assert state["next_action"] == "补充回答：cabinet drawing"
    task = conn.execute(
        "SELECT title,due_at,priority FROM activities WHERE lead_no=1 ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert "cabinet drawing" in task["title"] and task["priority"] == "high"
    assert task["due_at"] == (dt.date.today() + dt.timedelta(days=1)).isoformat()
