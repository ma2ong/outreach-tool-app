import datetime

from app import outreach, sequence_send, sequences
from app.db import connect, init_schema


def _conn(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    init_schema(conn)
    conn.execute(
        "INSERT INTO leads(no,company_en,country,city,email,website,hook) VALUES"
        " (1,'Verum AV Solutions','USA','Houston, TX','hello@verumav.com','verumav.com',"
        "  'Saw the rental work on your site.')"
    )
    conn.commit()
    return conn


def test_campaign_holds_generic_opening_without_marking_sent(tmp_path):
    conn = _conn(tmp_path)
    calls = []
    result = outreach.send_campaign(
        conn, [1], "LED display supply", "We manufacture indoor and outdoor LED displays.",
        None, lambda *args: calls.append(args), delay_range=(0, 0),
    )
    assert result["sent"] == 0
    assert result["held"] == 1
    assert result["holds"][0]["reason"] == "impersonal"
    assert calls == []
    assert conn.execute("SELECT 1 FROM outreach WHERE lead_no=1").fetchone() is None
    conn.close()


def test_campaign_sends_exact_rendered_personalized_text(tmp_path):
    conn = _conn(tmp_path)
    calls = []
    result = outreach.send_campaign(
        conn, [1], "LED display supply",
        "{hook}\n\nWe manufacture LED displays for integrators.", None,
        lambda to, subject, body, attachment: calls.append((to, subject, body)),
        delay_range=(0, 0),
    )
    assert result["sent"] == 1
    assert result["held"] == 0
    assert calls == [(
        "hello@verumav.com",
        "LED display supply",
        "Saw the rental work on your site.\n\nWe manufacture LED displays for integrators.",
    )]
    conn.close()


def test_sequence_hold_does_not_advance_or_mark_messaged(tmp_path):
    conn = _conn(tmp_path)
    sid = sequences.create_sequence(conn, "generic", "email", [{
        "day_offset": 0,
        "subject": "LED display supply",
        "body": "We manufacture indoor and outdoor LED displays.",
    }])
    sequences.enroll_leads(conn, sid, [1])
    due = sequences.due_queue(conn)
    eid = due[0]["enrollment_id"]
    calls = []
    result = sequence_send.send_due(
        conn, [eid], sender=lambda *args: calls.append(args), email_delay=(0, 0)
    )
    assert result["sent"] == 0
    assert result["held"] == 1
    assert calls == []
    enrollment = conn.execute(
        "SELECT current_step,status FROM sequence_enrollments WHERE id=?", (eid,)
    ).fetchone()
    assert enrollment["current_step"] == 0
    assert enrollment["status"] == "active"
    assert conn.execute("SELECT 1 FROM outreach WHERE lead_no=1").fetchone() is None
    conn.close()


def test_follow_up_step_can_be_generic_but_price_is_still_held(tmp_path):
    conn = _conn(tmp_path)
    sid = sequences.create_sequence(conn, "followup", "email", [
        {"day_offset": 0, "subject": "LED panel specs", "body": "First note for {company}."},
        {"day_offset": 1, "subject": "Re: LED", "body": "A cabinet data sheet is available."},
    ])
    sequences.enroll_leads(conn, sid, [1])
    eid = sequences.due_queue(conn)[0]["enrollment_id"]
    sequence_send.send_due(conn, [eid], sender=lambda *args: None, email_delay=(0, 0))
    conn.execute(
        "UPDATE sequence_enrollments SET next_due_date=? WHERE id=?",
        (datetime.date.today().isoformat(), eid),
    )
    conn.execute("UPDATE send_log SET sent_at=datetime('now','-1 day') WHERE lead_no=1")
    conn.commit()
    log = []
    result = sequence_send.send_due(
        conn, [eid], sender=lambda to, subject, body, image: log.append(body), email_delay=(0, 0)
    )
    assert result["sent"] == 1
    assert log == ["A cabinet data sheet is available."]

    # A commercial number is held even on later steps.
    sid2 = sequences.create_sequence(conn, "price", "email", [
        {"day_offset": 0, "subject": "LED panel specs", "body": "First note for {company}."},
        {"day_offset": 1, "subject": "Re", "body": "Price is USD 900/sqm."},
    ])
    # use another lead so the completed first sequence does not interfere with enrollment
    conn.execute(
        "INSERT INTO leads(no,company_en,country,city,email,website,hook) VALUES"
        " (2,'Beta AV','USA','Austin, TX','hello@beta.example','beta.example','Saw your AV work.')"
    )
    conn.commit()
    sequences.enroll_leads(conn, sid2, [2])
    eid2 = sequences.due_queue(conn)[0]["enrollment_id"]
    sequence_send.send_due(conn, [eid2], sender=lambda *args: None, email_delay=(0, 0))
    conn.execute(
        "UPDATE sequence_enrollments SET next_due_date=? WHERE id=?",
        (datetime.date.today().isoformat(), eid2),
    )
    conn.execute("UPDATE send_log SET sent_at=datetime('now','-1 day') WHERE lead_no=2")
    conn.commit()
    result2 = sequence_send.send_due(conn, [eid2], sender=lambda *args: None, email_delay=(0, 0))
    assert result2["sent"] == 0
    assert result2["held"] == 1
    assert result2["holds"][0]["reason"] == "pricing"
    conn.close()
