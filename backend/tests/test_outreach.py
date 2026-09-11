from app import outreach


def _seed(conn):
    conn.executescript("""
        DELETE FROM outreach;
        DELETE FROM leads;
        INSERT INTO leads(no, company_en, email) VALUES
            (1,'Alpha','a@a.com'),(2,'Beta','b@b.com'),(3,'Gamma',NULL),(4,'Delta','d@d.com');
        INSERT INTO outreach(lead_no, channel, status) VALUES (4,'email','messaged');
    """)
    conn.commit()


def test_eligible_leads_skips_no_email_and_already_sent(conn):
    _seed(conn)
    elig = outreach.eligible_leads(conn, [1, 2, 3, 4], "email")
    assert [l["no"] for l in elig] == [1, 2]


def test_send_campaign_sends_and_marks(conn):
    _seed(conn)
    calls = []
    result = outreach.send_campaign(
        conn, [1, 2, 3, 4], subject="Hi {name}", body="Hello {name}",
        attachment=None, sender=lambda to, s, b, a: calls.append((to, s, b)),
        delay_range=(0, 0))
    assert result["sent"] == 2
    assert result["skipped"] == 2
    assert {c[0] for c in calls} == {"a@a.com", "b@b.com"}
    assert ("a@a.com", "Hi Alpha", "Hello Alpha") in calls
    rows = conn.execute("SELECT lead_no FROM outreach WHERE channel='email' AND status='messaged' ORDER BY lead_no").fetchall()
    assert [r["lead_no"] for r in rows] == [1, 2, 4]


def test_send_campaign_records_failure(conn):
    _seed(conn)

    def boom(to, s, b, a):
        raise RuntimeError("smtp down")

    result = outreach.send_campaign(
        conn, [1], subject="Hi {company}", body="Hello {company}", attachment=None,
        sender=boom, delay_range=(0, 0))
    assert result["sent"] == 0
    assert result["failed"] == 1


def test_uncertain_email_transport_is_not_reentered(conn):
    _seed(conn)
    calls = []

    def accepted_then_timeout(to, *_args, **_kwargs):
        calls.append(to)
        raise TimeoutError("provider response lost")

    first = outreach.send_campaign(
        conn, [1], "Hi {company}", "Hello {company}", None,
        sender=accepted_then_timeout, delay_range=(0, 0), campaign="Manual test")
    second = outreach.send_campaign(
        conn, [1], "Hi {company}", "Hello {company}", None,
        sender=accepted_then_timeout, delay_range=(0, 0), campaign="Manual test")

    assert first["failed"] == 1
    assert second["sent"] == 0
    assert calls == ["a@a.com"]
    intent = conn.execute("SELECT status FROM delivery_intents").fetchone()
    assert intent["status"] == "unknown"


def test_confirming_uncertain_email_as_sent_repairs_crm_without_transport(conn):
    from app import delivery_intents

    _seed(conn)
    outreach.send_campaign(
        conn, [1], "Hi {company}", "Hello {company}", None,
        sender=lambda *_args, **_kwargs: (_ for _ in ()).throw(TimeoutError("unknown")),
        delay_range=(0, 0), campaign="Manual repair")
    intent = delivery_intents.unresolved(conn)[0]

    delivery_intents.resolve(conn, intent["id"], "sent")

    assert conn.execute(
        "SELECT status FROM outreach WHERE lead_no=1 AND channel='email'"
    ).fetchone()["status"] == "messaged"
    log = conn.execute("SELECT campaign,body FROM send_log WHERE lead_no=1").fetchone()
    assert dict(log) == {"campaign": "Manual repair", "body": "Hello Alpha"}


def test_confirming_uncertain_rotating_mailbox_send_reserves_its_daily_slot(conn, monkeypatch):
    from app import delivery_intents, mailboxes

    _seed(conn)
    mailbox_id = mailboxes.add_mailbox(
        conn, "allen@example.com", "smtp.example.com", 465, "allen", "pw", daily_cap=2,
    )
    calls = []

    def accepted_then_timeout(mailbox, to, *_args, **_kwargs):
        calls.append((mailbox["id"], to))
        raise TimeoutError("provider response lost")

    monkeypatch.setattr("app.channels.email_adapter.send_via", accepted_then_timeout)
    result = outreach.send_campaign(
        conn, [1], "Hi {company}", "Hello {company}", None,
        sender=mailboxes.rotating_sender(conn), delay_range=(0, 0), campaign="Rotating",
    )
    intent = delivery_intents.unresolved(conn)[0]
    assert result["failed"] == 1
    assert mailboxes.sent_today(conn, mailbox_id) == 0
    assert calls == [(mailbox_id, "a@a.com")]

    delivery_intents.resolve(conn, intent["id"], "sent")
    assert mailboxes.sent_today(conn, mailbox_id) == 1
    delivery_intents.resolve(conn, intent["id"], "sent")
    assert mailboxes.sent_today(conn, mailbox_id) == 1


def test_send_campaign_progress_callback(conn):
    _seed(conn)
    seen = []
    outreach.send_campaign(
        conn, [1, 2], subject="Hi {company}", body="Hello {company}", attachment=None,
        sender=lambda *a: None, delay_range=(0, 0),
        on_progress=lambda done, total: seen.append((done, total)))
    assert seen[-1] == (2, 2)


def test_eligible_leads_excludes_replied(conn):
    _seed(conn)
    conn.execute("INSERT INTO outreach(lead_no, channel, status) VALUES (1,'email','replied')")
    conn.commit()
    assert [l["no"] for l in outreach.eligible_leads(conn, [1, 2], "email")] == [2]
