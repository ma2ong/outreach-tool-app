import app.main as main
from app import jobs
from app.db import connect, init_schema
from fastapi.testclient import TestClient


def _client(tmp_path):
    db = str(tmp_path / "t.db")
    c = connect(db)
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, email) VALUES
            (1,'Alpha','a@a.com'),(2,'Beta','b@b.com'),(3,'Gamma','g@g.com');
    """)
    c.commit()
    c.close()
    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    return TestClient(main.app), db


def test_mailbox_crud_hides_password(tmp_path):
    client, _ = _client(tmp_path)
    r = client.post("/api/mailboxes", json={
        "email": "s1@x.com", "smtp_host": "smtp.x.com", "port": 465,
        "username": "s1@x.com", "password": "secret", "daily_cap": 40})
    assert r.status_code == 200
    assert "password" not in r.json()
    mid = r.json()["id"]
    assert client.get("/api/mailboxes").json()[0]["email"] == "s1@x.com"
    assert client.patch(f"/api/mailboxes/{mid}", json={"active": False}).status_code == 200
    assert client.delete(f"/api/mailboxes/{mid}").status_code == 200
    assert client.get("/api/mailboxes").json() == []


def test_mailbox_validation(tmp_path):
    client, _ = _client(tmp_path)
    assert client.post("/api/mailboxes", json={"email": "", "smtp_host": "h", "username": "u", "password": "p"}).status_code == 400
    assert client.delete("/api/mailboxes/999").status_code == 404


def test_email_send_rotates_across_mailboxes(tmp_path):
    import app.api.send as send_api
    jobs.clear()
    client, db = _client(tmp_path)
    send_api.DB_PATH = db
    # two mailboxes, cap 1 each -> total capacity 2, so 1 of 3 leads is deferred
    client.post("/api/mailboxes", json={"email": "s1@x.com", "smtp_host": "smtp.x.com",
                "username": "s1@x.com", "password": "p", "daily_cap": 1})
    client.post("/api/mailboxes", json={"email": "s2@x.com", "smtp_host": "smtp.x.com",
                "username": "s2@x.com", "password": "p", "daily_cap": 1})
    used = []
    send_api.email_adapter.send_via = lambda mbx, to, s, b, a: used.append(mbx["email"])
    send_api.DELAY_RANGE = (0, 0)
    r = client.post("/api/send/email", json={"lead_nos": [1, 2, 3], "subject": "Hi", "body": "yo"})
    assert r.json()["will_send"] == 2
    job = client.get(f"/api/send/jobs/{r.json()['job_id']}").json()
    assert job["status"] == "done"
    assert job["result"]["sent"] == 2 and job["result"]["deferred"] == 1
    assert set(used) == {"s1@x.com", "s2@x.com"}  # rotated across both


def test_mailbox_test_endpoint_reports_bad_credentials(tmp_path, monkeypatch):
    client, _ = _client(tmp_path)
    client.post("/api/mailboxes", json={"email": "a@x.com", "smtp_host": "smtp.x.com",
                                        "port": 465, "username": "a", "password": "wrong",
                                        "daily_cap": 40})
    from app.channels import email_adapter
    monkeypatch.setattr(email_adapter, "test_mailbox",
                        lambda mbx: (_ for _ in ()).throw(RuntimeError("535 auth failed")))
    r = client.post("/api/mailboxes/1/test")
    assert r.status_code == 400 and "535" in r.json()["detail"]


def test_mailbox_test_endpoint_ok(tmp_path, monkeypatch):
    client, _ = _client(tmp_path)
    client.post("/api/mailboxes", json={"email": "a@x.com", "smtp_host": "smtp.x.com",
                                        "port": 465, "username": "a", "password": "right",
                                        "daily_cap": 40})
    from app import replies
    from app.channels import email_adapter
    monkeypatch.setattr(email_adapter, "test_mailbox", lambda mbx: None)
    monkeypatch.setattr(replies, "test_mailbox", lambda mbx: None)
    assert client.post("/api/mailboxes/1/test").json() == {
        "ok": True, "smtp": True, "imap": True,
    }


def test_mailbox_test_404(tmp_path):
    client, _ = _client(tmp_path)
    assert client.post("/api/mailboxes/999/test").status_code == 404


def test_send_only_mailbox_is_skipped_by_the_reply_poll(tmp_path):
    """A mailbox whose plan withholds IMAP must not turn every sweep into an error."""
    from app import mailboxes as mb, replies
    _, db = _client(tmp_path)
    conn = connect(db)
    mb.add_mailbox(conn, "send@only.com", "smtp.only.com", 465, "send@only.com", "pw",
                   imap_enabled=False)
    mb.add_mailbox(conn, "both@ok.com", "smtp.ok.com", 465, "both@ok.com", "pw")
    polled = []

    def fetcher(mailbox, since_days):
        polled.append(mailbox["email"])
        return []

    result = replies.poll_all_replies(conn, fetcher=fetcher)
    assert polled == ["both@ok.com"]
    assert result["errors"] == [] and result["mailboxes_checked"] == 1


def test_only_send_only_mailboxes_falls_back_to_the_legacy_gmail(tmp_path, monkeypatch):
    """Otherwise configuring a send-only box would silently stop all reply detection."""
    from app import mailboxes as mb, replies
    from app.channels.email_adapter import GMAIL_USER
    _, db = _client(tmp_path)
    conn = connect(db)
    mb.add_mailbox(conn, "send@only.com", "smtp.only.com", 465, "send@only.com", "pw",
                   imap_enabled=False)
    monkeypatch.setattr("app.replies.get_password", lambda: "gmail-pw")
    polled = []

    def fetcher(mailbox, since_days):
        polled.append(mailbox["email"])
        return []

    replies.poll_all_replies(conn, fetcher=fetcher)
    assert polled == [GMAIL_USER]


def test_test_endpoint_skips_imap_for_a_send_only_mailbox(tmp_path, monkeypatch):
    from app import mailboxes as mb
    client, db = _client(tmp_path)
    monkeypatch.setattr("app.channels.email_adapter.test_mailbox", lambda box: None)
    monkeypatch.setattr("app.replies.test_mailbox",
                        lambda box: (_ for _ in ()).throw(AssertionError("must not run")))
    conn = connect(db)
    mid = mb.add_mailbox(conn, "send@only.com", "smtp.only.com", 465, "send@only.com",
                         "pw", imap_enabled=False)
    r = client.post(f"/api/mailboxes/{mid}/test")
    assert r.status_code == 200 and r.json() == {"ok": True, "smtp": True, "imap": False}
