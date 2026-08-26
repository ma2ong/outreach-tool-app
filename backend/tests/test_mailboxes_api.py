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
    client.post("/api/mailboxes", json={"email": "s1@x.com", "smtp_host": "smtp.x.com",
                "username": "s1@x.com", "password": "p", "daily_cap": 1})
    client.post("/api/mailboxes", json={"email": "s2@x.com", "smtp_host": "smtp.x.com",
                "username": "s2@x.com", "password": "p", "daily_cap": 1})
    used = []
    send_api.email_adapter.send_via = lambda mbx, to, s, b, a: used.append(mbx["email"])
    send_api.DELAY_RANGE = (0, 0)
    r = client.post("/api/send/email", json={
        "lead_nos": [1, 2, 3], "subject": "Hi {company}", "body": "Hello {company}"})
    assert r.json()["will_send"] == 2
    job = client.get(f"/api/send/jobs/{r.json()['job_id']}").json()
    assert job["status"] == "done"
    assert job["result"]["sent"] == 2 and job["result"]["deferred"] == 1
    assert set(used) == {"s1@x.com", "s2@x.com"}


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


def test_a_mailbox_password_can_be_changed_without_deleting_it(tmp_path):
    """Until this existed the only way to fix a password was delete-and-re-add, so the
    obvious move — type in the password box, press Test — was filling in the *new
    mailbox* form while testing the old row."""
    client, _ = _client(tmp_path)
    created = client.post("/api/mailboxes", json={
        "email": "allen@maxcolorvisual.com", "smtp_host": "smtp.qiye.163.com",
        "username": "allen@maxcolorvisual.com", "password": "first", "daily_cap": 30})
    mid = created.json()["id"]
    assert client.put(f"/api/mailboxes/{mid}/password", json={"password": "second"}).status_code == 200
    assert client.put(f"/api/mailboxes/{mid}/password", json={"password": "  "}).status_code == 400
    assert client.put("/api/mailboxes/9999/password", json={"password": "x"}).status_code == 404


def test_testing_a_mailbox_with_no_password_says_so(tmp_path):
    """NetEase answers an empty credential by closing the socket, which surfaces as
    'Connection unexpectedly closed' — indistinguishable from a network fault."""
    from app.db import connect
    client, db = _client(tmp_path)
    created = client.post("/api/mailboxes", json={
        "email": "allen@maxcolorvisual.com", "smtp_host": "smtp.qiye.163.com",
        "username": "allen@maxcolorvisual.com", "password": "x", "daily_cap": 30})
    mid = created.json()["id"]
    conn = connect(db)
    conn.execute("UPDATE mailboxes SET password='' WHERE id=?", (mid,))
    conn.commit()
    conn.close()
    r = client.post(f"/api/mailboxes/{mid}/test")
    assert r.status_code == 400 and "还没有密码" in r.json()["detail"]


def _seed_first_touch(db: str) -> None:
    from app.db import connect
    conn = connect(db)
    conn.execute("UPDATE leads SET hook='Saw the rental work on your site.',"
                 " website='alpha.com', city='Houston, TX' WHERE no=1")
    sid = conn.execute(
        "INSERT INTO sequences(name, channel, active, created_at)"
        " VALUES ('冷邮件 3 步跟进（英语）','email',1,'2026-08-01')").lastrowid
    conn.execute(
        "INSERT INTO sequence_steps(sequence_id, step_order, day_offset, subject, body)"
        " VALUES (?,0,0,'{company} — LED display supply','Hi,\n\n{hook}\n\nAllen')", (sid,))
    conn.commit()
    conn.close()


def test_the_test_mail_is_the_real_opening_email(tmp_path, monkeypatch):
    """A deliverability score is only worth having on the message customers actually get.
    A mail reading "test" scores differently on content and wording than the real first
    touch, and it is the real one whose score we need."""
    from app.channels import email_adapter

    client, db = _client(tmp_path)
    _seed_first_touch(db)
    mid = client.post("/api/mailboxes", json={
        "email": "allen@maxcolorvisual.com", "smtp_host": "smtp.qiye.163.com",
        "username": "allen@maxcolorvisual.com", "password": "pw", "daily_cap": 30}).json()["id"]

    sent = {}
    monkeypatch.setattr(email_adapter, "send_via",
                        lambda box, to, subject, body, att: sent.update(
                            {"box": box["email"], "to": to, "subject": subject, "body": body}))
    r = client.post(f"/api/mailboxes/{mid}/send-test", json={"to": "score@mail-tester.com"})
    assert r.status_code == 200
    assert sent["to"] == "score@mail-tester.com"
    assert sent["box"] == "allen@maxcolorvisual.com"
    # Rendered, not raw: placeholders must be gone before this measures anything.
    assert "{company}" not in sent["subject"] and "{hook}" not in sent["body"]
    assert "Saw the rental work" in sent["body"]
    assert r.json()["guard_blocked"] is False


def test_a_test_mail_is_not_counted_as_prospecting(tmp_path, monkeypatch):
    """Nobody was prospected, so it must not spend the daily cap or land in send_log."""
    from app.db import connect
    from app.channels import email_adapter

    client, db = _client(tmp_path)
    _seed_first_touch(db)
    mid = client.post("/api/mailboxes", json={
        "email": "a@b.com", "smtp_host": "smtp.qiye.163.com", "username": "a@b.com",
        "password": "pw", "daily_cap": 30}).json()["id"]
    monkeypatch.setattr(email_adapter, "send_via", lambda *a, **k: None)
    client.post(f"/api/mailboxes/{mid}/send-test", json={"to": "x@mail-tester.com"})
    conn = connect(db)
    assert conn.execute("SELECT COUNT(*) c FROM send_log").fetchone()["c"] == 0
    assert conn.execute("SELECT COUNT(*) c FROM mailbox_sends").fetchone()["c"] == 0
    conn.close()


def test_a_test_mail_needs_a_password_and_a_real_address(tmp_path):
    client, db = _client(tmp_path)
    _seed_first_touch(db)
    mid = client.post("/api/mailboxes", json={
        "email": "a@b.com", "smtp_host": "smtp.qiye.163.com", "username": "a@b.com",
        "password": "pw", "daily_cap": 30}).json()["id"]
    assert client.post(f"/api/mailboxes/{mid}/send-test", json={"to": "nonsense"}).status_code == 400
    assert client.post("/api/mailboxes/9999/send-test", json={"to": "x@y.com"}).status_code == 404
