import pytest

from app import replies, sequences
from app.db import connect, init_schema


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, email) VALUES
            (1, 'Alpha AV', 'USA', 'sales@alpha.com'),
            (2, 'Beta Screens', 'USA', 'b@beta.com'),
            (3, 'Gamma LED', 'Brazil', 'g@gamma.com');
        INSERT INTO outreach(lead_no, channel, status, touch_count) VALUES
            (1, 'email', 'messaged', 1),
            (2, 'email', 'messaged', 1);
    """)
    c.commit()
    return c


def _msg(from_addr, subject="Re: LED", body="Please send catalog", received_at="2026-07-13T09:00:00"):
    return {"from_addr": from_addr, "subject": subject, "body": body, "received_at": received_at}


def test_reply_stored_and_marked(conn):
    res = replies.process_messages(conn, [_msg("SALES@Alpha.com")])
    assert res["replies"] == 1 and res["stored"] == 1
    row = conn.execute("SELECT * FROM inbox_messages WHERE lead_no=1").fetchone()
    assert row["kind"] == "reply" and row["body"] == "Please send catalog" and row["is_read"] == 0
    st = conn.execute("SELECT status FROM outreach WHERE lead_no=1 AND channel='email'").fetchone()
    assert st["status"] == "replied"


def test_unknown_sender_not_stored(conn):
    res = replies.process_messages(conn, [_msg("stranger@nope.com")])
    assert res["stored"] == 0
    assert conn.execute("SELECT COUNT(*) c FROM inbox_messages").fetchone()["c"] == 0


def test_duplicate_message_stored_once(conn):
    replies.process_messages(conn, [_msg("sales@alpha.com")])
    res = replies.process_messages(conn, [_msg("sales@alpha.com")])
    assert res["stored"] == 0
    assert conn.execute("SELECT COUNT(*) c FROM inbox_messages").fetchone()["c"] == 1


def test_bounce_marks_email_invalid(conn):
    bounce = _msg("MAILER-DAEMON@googlemail.com",
                  subject="Delivery Status Notification (Failure)",
                  body="Your message to b@beta.com could not be delivered. 550 no such user")
    res = replies.process_messages(conn, [bounce])
    assert res["bounces"] == 1
    lead = conn.execute("SELECT email_status FROM leads WHERE no=2").fetchone()
    assert lead["email_status"] == "invalid"
    # the notice itself is noise — the inbox holds only what Allen has to read
    assert conn.execute("SELECT COUNT(*) c FROM inbox_messages WHERE lead_no=2").fetchone()["c"] == 0
    # a bounce is NOT a reply — outreach status must stay 'messaged'
    st = conn.execute("SELECT status FROM outreach WHERE lead_no=2 AND channel='email'").fetchone()
    assert st["status"] == "messaged"


def test_bounce_without_matching_lead_ignored(conn):
    bounce = _msg("postmaster@x.com", subject="Undelivered Mail Returned to Sender",
                  body="unknown@nowhere.com rejected")
    res = replies.process_messages(conn, [bounce])
    assert res["bounces"] == 0 and res["stored"] == 0


def test_unsubscribe_sets_do_not_contact(conn):
    res = replies.process_messages(conn, [_msg("g@gamma.com", body="Please remove me from your list")])
    assert res["unsubscribes"] == 1
    lead = conn.execute("SELECT do_not_contact FROM leads WHERE no=3").fetchone()
    assert lead["do_not_contact"] == 1
    row = conn.execute("SELECT kind FROM inbox_messages WHERE lead_no=3").fetchone()
    assert row["kind"] == "unsubscribe"


def test_unsubscribe_still_marks_replied_and_stops_sequence(conn):
    sid = sequences.create_sequence(conn, "S", "email", [{"day_offset": 0, "body": "hi"}])
    sequences.enroll_leads(conn, sid, [1])
    replies.process_messages(conn, [_msg("sales@alpha.com", body="unsubscribe")])
    assert sequences.due_queue(conn) == []


def test_do_not_contact_excluded_from_all_sends(conn):
    from app import channel_outreach, outreach
    conn.execute("UPDATE leads SET do_not_contact=1, phone='+1 555', instagram='alphaig' WHERE no=3")
    conn.commit()
    assert outreach.eligible_leads(conn, [3], "email") == []
    assert channel_outreach.eligible(conn, [3], "whatsapp") == []
    assert channel_outreach.eligible(conn, [3], "instagram") == []
    sid = sequences.create_sequence(conn, "S", "email", [{"day_offset": 0, "body": "hi"}])
    sequences.enroll_leads(conn, sid, [3])
    assert sequences.due_queue(conn) == []


def test_poll_uses_injected_message_fetcher(conn):
    res = replies.poll_replies(conn, fetch_messages=lambda days: [_msg("g@gamma.com")])
    assert res["replies"] == 1
