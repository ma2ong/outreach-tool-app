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
        conn, [1, 2, 3, 4], subject="LED panel specs", body="Hello {name}",
        attachment=None, sender=lambda to, s, b, a: calls.append((to, s, b)),
        delay_range=(0, 0))
    assert result["sent"] == 2
    assert result["skipped"] == 2
    assert {c[0] for c in calls} == {"a@a.com", "b@b.com"}
    assert ("a@a.com", "LED panel specs", "Hello Alpha") in calls
    rows = conn.execute("SELECT lead_no FROM outreach WHERE channel='email' AND status='messaged' ORDER BY lead_no").fetchall()
    assert [r["lead_no"] for r in rows] == [1, 2, 4]


def test_send_campaign_records_failure(conn):
    _seed(conn)

    def boom(to, s, b, a):
        raise RuntimeError("smtp down")

    result = outreach.send_campaign(
        conn, [1], subject="LED panel specs", body="Hello {company}", attachment=None,
        sender=boom, delay_range=(0, 0))
    assert result["sent"] == 0
    assert result["failed"] == 1


def test_send_campaign_progress_callback(conn):
    _seed(conn)
    seen = []
    outreach.send_campaign(
        conn, [1, 2], subject="LED panel specs", body="Hello {company}", attachment=None,
        sender=lambda *a: None, delay_range=(0, 0),
        on_progress=lambda done, total: seen.append((done, total)))
    assert seen[-1] == (2, 2)


def test_eligible_leads_excludes_replied(conn):
    _seed(conn)
    conn.execute("INSERT INTO outreach(lead_no, channel, status) VALUES (1,'email','replied')")
    conn.commit()
    assert [l["no"] for l in outreach.eligible_leads(conn, [1, 2], "email")] == [2]
