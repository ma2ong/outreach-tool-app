"""One customer's correspondence, and replying into it (docs/56).

The rule these guard is that the view must not invent our half of the conversation.
624 emails went out before bodies were stored; re-rendering their templates with today's
hooks would produce letters nobody received, and Allen would follow up on sentences the
customer never read.
"""
import pytest

import app.main as main
from app.db import connect, init_schema
from fastapi.testclient import TestClient

SENT = []


@pytest.fixture(autouse=True)
def _no_real_smtp(monkeypatch):
    """No test may reach a mail server. A reply test that actually sends is a test that
    mails a customer."""
    from app.api import send as send_api
    SENT.clear()
    monkeypatch.setattr(send_api, "pick_sender",
                        lambda conn: lambda *a: SENT.append(a))


def _client(tmp_path):
    db = str(tmp_path / "t.db")
    c = connect(db)
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, email, hook) VALUES
            (1,'Verum AV','USA','info@verumav.com','Saw the rental work.'),
            (2,'Quiet Co','USA','x@quiet.com',NULL),
            (3,'Untouched','USA','n@new.com',NULL);
        INSERT INTO send_log(lead_no, channel, campaign, sent_at, subject, body) VALUES
            (1,'email','序列:冷邮件','2026-08-01T09:00:00Z',NULL,NULL),
            (1,'email','序列:冷邮件','2026-08-10T09:00:00Z','Follow up','Second note.');
        INSERT INTO inbox_messages(lead_no, channel, kind, from_addr, subject, body,
                                   received_at, is_read) VALUES
            (1,'email','reply','bob@verumav.com','Re: LED','Send specs.',
             '2026-08-05T10:00:00Z',0),
            (1,'email','auto','bob@verumav.com','Out of office','Back Monday.',
             '2026-08-02T10:00:00Z',1),
            (2,'email','bounce','postmaster@x','Undeliverable','550',
             '2026-08-03T10:00:00Z',1);
    """)
    c.commit()
    c.close()
    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    return TestClient(main.app)


def test_events_are_in_the_order_they_happened(tmp_path):
    events = _client(tmp_path).get("/api/conversations/1").json()["events"]
    assert [e["at"] for e in events] == sorted(e["at"] for e in events)


def test_a_send_with_no_stored_body_says_so_instead_of_guessing(tmp_path):
    events = _client(tmp_path).get("/api/conversations/1").json()["events"]
    old = next(e for e in events if e["at"].startswith("2026-08-01"))
    assert old["body_missing"] is True
    assert old["body"] is None
    # The hook is right there on the lead; the point is that it must not be used here.
    assert "rental" not in str(old)


def test_a_send_with_a_stored_body_shows_it(tmp_path):
    events = _client(tmp_path).get("/api/conversations/1").json()["events"]
    recent = next(e for e in events if e["at"].startswith("2026-08-10"))
    assert (recent["body_missing"], recent["body"]) == (False, "Second note.")


def test_autoresponders_are_kept_but_folded_away(tmp_path):
    events = _client(tmp_path).get("/api/conversations/1").json()["events"]
    auto = next(e for e in events if e.get("message_kind") == "auto")
    reply = next(e for e in events if e.get("message_kind") == "reply")
    assert (auto["quiet"], reply["quiet"]) == (True, False)


def test_a_customer_who_only_bounced_still_has_a_conversation(tmp_path):
    # The bounce is why that thread went quiet; hiding it hides the explanation.
    body = _client(tmp_path).get("/api/conversations/2").json()
    assert body["reply_count"] == 0
    assert len(body["events"]) == 1


def test_the_summary_counts_what_we_cannot_show(tmp_path):
    body = _client(tmp_path).get("/api/conversations/1").json()
    assert (body["sent_count"], body["reply_count"], body["missing_bodies"]) == (2, 1, 1)


def test_leads_nobody_ever_wrote_to_are_not_conversations(tmp_path):
    rows = _client(tmp_path).get("/api/conversations").json()
    assert {r["no"] for r in rows} == {1, 2}


def test_customers_waiting_on_us_come_first(tmp_path):
    rows = _client(tmp_path).get("/api/conversations").json()
    assert rows[0]["no"] == 1  # unread reply; #2 only bounced


def test_a_missing_lead_is_404(tmp_path):
    assert _client(tmp_path).get("/api/conversations/999").status_code == 404


def test_a_reply_carrying_a_price_is_refused_until_allen_insists(tmp_path):
    client = _client(tmp_path)
    priced = {"body": "Happy to help — the P3.9 panel is $450 per square meter."}
    blocked = client.post("/api/conversations/1/reply", json=priced)
    assert blocked.status_code == 428


def test_an_empty_reply_is_refused(tmp_path):
    r = _client(tmp_path).post("/api/conversations/1/reply", json={"body": "   "})
    assert r.status_code == 400


def test_a_lead_with_no_address_cannot_be_replied_to(tmp_path):
    client = _client(tmp_path)
    conn = main.app.dependency_overrides[main.get_conn]()
    conn.execute("UPDATE leads SET email=NULL WHERE no=1")
    conn.commit()
    r = client.post("/api/conversations/1/reply", json={"body": "Hello there."})
    assert r.status_code == 400
    assert SENT == []


def test_a_clean_reply_goes_out_and_hands_the_thread_to_allen(tmp_path):
    client = _client(tmp_path)
    r = client.post("/api/conversations/1/reply",
                    json={"body": "Thanks — specs attached, let me know the pitch."})
    assert r.status_code == 200
    assert len(SENT) == 1
    body = client.get("/api/conversations/1").json()
    assert body["state"]["owner"] == "allen"
    assert body["state"]["state"] == "human_takeover"
    # The reply is now part of the record, with its text.
    assert any(e["kind"] == "sent" and e["body"] and "specs attached" in e["body"]
               for e in body["events"])
