import pytest

from app import sequence_send, sequences
from app.browser_engine import FakeEngine
from app.db import connect, init_schema


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, email, phone) VALUES
            (1, 'Alpha', 'a@alpha.com', '+1 555 111 2222'),
            (2, 'Beta', 'b@beta.com', '+1 555 333 4444');
    """)
    c.commit()
    return c


def _email_seq(conn):
    return sequences.create_sequence(conn, "S", "email", [
        {"day_offset": 0, "subject": "LED panel specs", "body": "First to {name}"},
        {"day_offset": 3, "subject": "Re", "body": "Second"},
    ])


def test_send_due_sends_and_advances(conn):
    sid = _email_seq(conn)
    sequences.enroll_leads(conn, sid, [1, 2])
    due = sequences.due_queue(conn)
    sent_log = []
    res = sequence_send.send_due(
        conn, [d["enrollment_id"] for d in due],
        sender=lambda to, subj, body, img: sent_log.append((to, subj, body)),
        email_delay=(0, 0))
    assert res["sent"] == 2
    assert ("a@alpha.com", "LED panel specs", "First to Alpha") in sent_log
    # both advanced to step 1 (due in 3 days) -> queue now empty today
    assert sequences.due_queue(conn) == []
    row = conn.execute("SELECT current_step FROM sequence_enrollments WHERE lead_no=1").fetchone()
    assert row["current_step"] == 1


def test_send_due_marks_messaged(conn):
    sid = _email_seq(conn)
    sequences.enroll_leads(conn, sid, [1])
    eid = sequences.due_queue(conn)[0]["enrollment_id"]
    sequence_send.send_due(conn, [eid], sender=lambda *a: None, email_delay=(0, 0))
    row = conn.execute("SELECT status, touch_count FROM outreach WHERE lead_no=1 AND channel='email'").fetchone()
    assert row["status"] == "messaged" and row["touch_count"] == 1


def test_second_step_reaches_already_messaged_lead(conn):
    """The key: a follow-up step must NOT be blocked by the messaged exclusion."""
    sid = _email_seq(conn)
    sequences.enroll_leads(conn, sid, [1])
    eid = sequences.due_queue(conn)[0]["enrollment_id"]
    sequence_send.send_due(conn, [eid], sender=lambda *a: None, email_delay=(0, 0))
    # force step 1 due now
    conn.execute("UPDATE sequence_enrollments SET next_due_date=date('now') WHERE id=?", (eid,))
    # Simulate the next eligible day; the global cadence guard intentionally prevents
    # two bulk touches to the same lead on one local day.
    conn.execute("UPDATE send_log SET sent_at=datetime('now', '-1 day') WHERE lead_no=1")
    conn.commit()
    log = []
    sequence_send.send_due(conn, [eid], sender=lambda to, s, b, i: log.append(b), email_delay=(0, 0))
    assert log == ["Second"]  # step 2 delivered despite lead already messaged
    assert conn.execute("SELECT touch_count FROM outreach WHERE lead_no=1").fetchone()["touch_count"] == 2


def test_channel_send_respects_daily_cap(conn):
    sid = sequences.create_sequence(conn, "WA", "whatsapp", [{"day_offset": 0, "body": "hi {name}"}])
    sequences.enroll_leads(conn, sid, [1, 2])
    # pretend WA daily cap already reached
    conn.executemany("INSERT INTO outreach(lead_no, channel, status, message_sent_date)"
                     " VALUES (?, 'whatsapp', 'messaged', date('now'))",
                     [(100 + i,) for i in range(co_cap(conn))])
    conn.commit()
    eng = FakeEngine()
    due = sequences.due_queue(conn, "whatsapp")
    res = sequence_send.send_due(conn, [d["enrollment_id"] for d in due], engine=eng, channel_delay=(0, 0))
    assert res["sent"] == 0 and res["deferred"] == 2
    assert eng.sent == []


def co_cap(conn):
    from app import channel_outreach
    return channel_outreach.DAILY_CAP["whatsapp"]
