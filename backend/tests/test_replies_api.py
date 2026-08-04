import app.main as main
from app.api import replies as replies_api
from app.db import connect, init_schema
from fastapi.testclient import TestClient


def _client(tmp_path):
    db = str(tmp_path / "t.db")
    c = connect(db)
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, email) VALUES (1, 'Alpha', 'a@alpha.com');
        INSERT INTO outreach(lead_no, channel, status, touch_count) VALUES (1, 'email', 'messaged', 1);
        INSERT INTO mailboxes(email, smtp_host, port, imap_host, imap_port, username, password)
        VALUES ('sales@sender.com', 'smtp.sender.com', 465, 'imap.sender.com', 993,
                'sales@sender.com', 'secret');
    """)
    c.commit()
    c.close()
    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    return TestClient(main.app)


def _fake_fetcher(mailbox, days):
    return [{"from_addr": "a@alpha.com", "subject": "Re: LED wall",
             "body": "Send me a quote for P2.5", "received_at": "2026-07-13T08:00:00"}]


def test_poll_marks_matching_reply(tmp_path):
    client = _client(tmp_path)
    replies_api.FETCHER = _fake_fetcher
    try:
        r = client.post("/api/replies/poll")
        assert r.status_code == 200
        assert r.json()["lead_nos"] == [1]
    finally:
        replies_api.FETCHER = replies_api.replies.fetch_mailbox_messages


def test_poll_then_inbox_lists_message(tmp_path):
    client = _client(tmp_path)
    replies_api.FETCHER = _fake_fetcher
    try:
        client.post("/api/replies/poll")
        r = client.get("/api/inbox")
        assert r.status_code == 200
        items = r.json()
        assert len(items) == 1
        m = items[0]
        assert m["company_en"] == "Alpha" and m["kind"] == "reply"
        assert "P2.5" in m["body"] and m["is_read"] == 0
        # unread badge count
        assert client.get("/api/inbox/unread_count").json()["count"] == 1
        # mark read
        assert client.post(f"/api/inbox/{m['id']}/read").status_code == 200
        assert client.get("/api/inbox/unread_count").json()["count"] == 0
    finally:
        replies_api.FETCHER = replies_api.replies.fetch_mailbox_messages


def test_inbox_unread_only_filter(tmp_path):
    client = _client(tmp_path)
    replies_api.FETCHER = _fake_fetcher
    try:
        client.post("/api/replies/poll")
        m = client.get("/api/inbox").json()[0]
        client.post(f"/api/inbox/{m['id']}/read")
        assert client.get("/api/inbox?unread_only=1").json() == []
        assert len(client.get("/api/inbox").json()) == 1
    finally:
        replies_api.FETCHER = replies_api.replies.fetch_mailbox_messages


def test_read_reply_stays_pending_until_salesperson_finishes_it(tmp_path):
    client = _client(tmp_path)
    replies_api.FETCHER = _fake_fetcher
    try:
        client.post("/api/replies/poll")
        message = client.get("/api/inbox").json()[0]
        assert client.get("/api/inbox/pending_count").json()["count"] == 1
        task = client.get("/api/activities?lead_no=1").json()[0]
        assert task["source_ref"] == f"inbox:{message['id']}" and task["priority"] == "high"

        # Reading is not the same as replying or arranging the next action.
        client.post(f"/api/inbox/{message['id']}/read")
        assert client.get("/api/inbox/unread_count").json()["count"] == 0
        assert client.get("/api/inbox/pending_count").json()["count"] == 1
        assert len(client.get("/api/inbox?pending_only=1").json()) == 1

        assert client.post(f"/api/inbox/{message['id']}/handled").status_code == 200
        assert client.get("/api/inbox/pending_count").json()["count"] == 0
        assert client.get("/api/inbox?pending_only=1").json() == []
        assert client.get("/api/activities?lead_no=1").json() == []
        assert client.get("/api/activities?lead_no=1&status=done").json()[0]["id"] == task["id"]
    finally:
        replies_api.FETCHER = replies_api.replies.fetch_mailbox_messages


def test_legacy_bounces_are_not_sales_inbox_items(tmp_path):
    client = _client(tmp_path)
    override = main.app.dependency_overrides[main.get_conn]
    conn = override()
    conn.execute(
        "INSERT INTO inbox_messages(lead_no, channel, kind, subject, is_read)"
        " VALUES (1, 'email', 'bounce', 'old failure notice', 0)"
    )
    conn.commit(); conn.close()
    assert client.get("/api/inbox").json() == []
    assert client.get("/api/inbox/unread_count").json()["count"] == 0


def test_poll_continues_when_one_mailbox_fails(tmp_path):
    client = _client(tmp_path)
    client.post("/api/mailboxes", json={
        "email": "second@sender.com", "smtp_host": "smtp.sender.com",
        "imap_host": "imap.sender.com", "username": "second@sender.com",
        "password": "secret",
    })

    def mixed(mailbox, days):
        if mailbox["email"] == "sales@sender.com":
            raise OSError("first inbox unavailable")
        return _fake_fetcher(mailbox, days)

    replies_api.FETCHER = mixed
    try:
        body = client.post("/api/replies/poll").json()
        assert body["mailboxes_checked"] == 1
        assert body["mailboxes_total"] == 2
        assert body["lead_nos"] == [1]
        assert body["errors"][0]["email"] == "sales@sender.com"
    finally:
        replies_api.FETCHER = replies_api.replies.fetch_mailbox_messages
