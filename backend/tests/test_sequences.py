import datetime as _dt

import pytest

from app import sequences, repository
from app.db import connect, init_schema


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, email) VALUES
            (1, 'Alpha AV', 'USA', 'a@alpha.com'),
            (2, 'Beta Screens', 'USA', 'b@beta.com'),
            (3, 'Gamma LED', 'Brazil', 'g@gamma.com');
    """)
    c.commit()
    return c


def _seq(conn, channel="email"):
    return sequences.create_sequence(conn, "Cold 3-touch", channel, [
        {"day_offset": 0, "subject": "LED panel specs", "body": "First touch to {name}"},
        {"day_offset": 3, "subject": "Re: LED panel specs", "body": "Second touch"},
        {"day_offset": 7, "body": "Last touch"},
    ])


def test_create_and_list(conn):
    sid = _seq(conn)
    seqs = sequences.list_sequences(conn)
    assert len(seqs) == 1
    assert seqs[0]["id"] == sid
    assert len(seqs[0]["steps"]) == 3
    assert seqs[0]["steps"][1]["day_offset"] == 3


def test_enroll_makes_step0_due_today(conn):
    sid = _seq(conn)
    n = sequences.enroll_leads(conn, sid, [1, 2])
    assert n == 2
    due = sequences.due_queue(conn)
    assert {d["lead_no"] for d in due} == {1, 2}
    assert all(d["step_order"] == 0 for d in due)
    assert due[0]["body"] == "First touch to {name}"


def test_enroll_skips_already_replied(conn):
    sid = _seq(conn)
    repository.mark_replied(conn, 1, "email")
    n = sequences.enroll_leads(conn, sid, [1, 2])
    assert n == 1  # lead 1 skipped
    assert {d["lead_no"] for d in sequences.due_queue(conn)} == {2}


def test_enroll_is_idempotent(conn):
    sid = _seq(conn)
    sequences.enroll_leads(conn, sid, [1])
    assert sequences.enroll_leads(conn, sid, [1]) == 0


def test_advance_moves_to_next_step_not_due_yet(conn):
    sid = _seq(conn)
    sequences.enroll_leads(conn, sid, [1])
    eid = sequences.due_queue(conn)[0]["enrollment_id"]
    sequences.advance_enrollment(conn, eid)
    # step 1 is day_offset 3 -> not due today
    assert sequences.due_queue(conn) == []
    row = conn.execute("SELECT current_step, status, next_due_date FROM sequence_enrollments"
                       " WHERE id=?", (eid,)).fetchone()
    assert row["current_step"] == 1
    assert row["status"] == "active"
    assert row["next_due_date"] > _dt.date.today().isoformat()


def test_advance_past_last_step_completes(conn):
    sid = _seq(conn)
    sequences.enroll_leads(conn, sid, [1])
    eid = sequences.due_queue(conn)[0]["enrollment_id"]
    sequences.advance_enrollment(conn, eid)
    sequences.advance_enrollment(conn, eid)  # -> step 2
    sequences.advance_enrollment(conn, eid)  # past last -> completed
    row = conn.execute("SELECT status FROM sequence_enrollments WHERE id=?", (eid,)).fetchone()
    assert row["status"] == "completed"


def test_reply_stops_active_enrollment(conn):
    sid = _seq(conn)
    sequences.enroll_leads(conn, sid, [1, 2])
    repository.mark_replied(conn, 1, "email")
    assert {d["lead_no"] for d in sequences.due_queue(conn)} == {2}
    row = conn.execute("SELECT status FROM sequence_enrollments WHERE lead_no=1").fetchone()
    assert row["status"] == "replied"


def test_reply_on_other_channel_does_not_stop(conn):
    sid = _seq(conn, "email")
    sequences.enroll_leads(conn, sid, [1])
    repository.mark_replied(conn, 1, "whatsapp")  # different channel
    assert {d["lead_no"] for d in sequences.due_queue(conn)} == {1}


def test_due_queue_filters_by_channel(conn):
    email_sid = _seq(conn, "email")
    wa_sid = sequences.create_sequence(conn, "WA", "whatsapp", [{"day_offset": 0, "body": "hi"}])
    sequences.enroll_leads(conn, email_sid, [1])
    sequences.enroll_leads(conn, wa_sid, [2])
    assert {d["lead_no"] for d in sequences.due_queue(conn, "email")} == {1}
    assert {d["lead_no"] for d in sequences.due_queue(conn, "whatsapp")} == {2}


def test_block_unsendable_parks_dead_email_enrollments(conn):
    sid = _seq(conn)
    sequences.enroll_leads(conn, sid, [1, 2, 3])
    conn.execute("UPDATE leads SET email_status='invalid' WHERE no=2")
    conn.execute("UPDATE leads SET email='' WHERE no=3")
    conn.commit()
    assert sequences.block_unsendable(conn) == 2
    # only the lead we can still mail stays in today's work
    assert {d["lead_no"] for d in sequences.due_queue(conn)} == {1}
    parked = conn.execute(
        "SELECT lead_no FROM sequence_enrollments WHERE status='blocked'").fetchall()
    assert {r["lead_no"] for r in parked} == {2, 3}


def test_block_unsendable_is_channel_aware(conn):
    """A missing phone must not park an email enrollment (and vice versa)."""
    email_sid = _seq(conn, "email")
    wa_sid = sequences.create_sequence(conn, "WA", "whatsapp", [{"day_offset": 0, "body": "hi"}])
    sequences.enroll_leads(conn, email_sid, [1])
    sequences.enroll_leads(conn, wa_sid, [2])   # lead 2 has an email but no phone
    assert sequences.block_unsendable(conn) == 1
    assert {d["lead_no"] for d in sequences.due_queue(conn)} == {1}


def test_block_unsendable_is_idempotent(conn):
    sid = _seq(conn)
    sequences.enroll_leads(conn, sid, [1, 2])
    conn.execute("UPDATE leads SET email_status='invalid' WHERE no=2")
    conn.commit()
    assert sequences.block_unsendable(conn) == 1
    assert sequences.block_unsendable(conn) == 0


def test_blocked_enrollment_is_not_counted_as_enrolled(conn):
    sid = _seq(conn)
    sequences.enroll_leads(conn, sid, [1, 2])
    conn.execute("UPDATE leads SET email_status='invalid' WHERE no=2")
    conn.commit()
    sequences.block_unsendable(conn)
    assert sequences.get_sequence(conn, sid)["enrolled"] == 1


def test_reopen_sendable_restores_a_repaired_address(conn):
    """A transient DNS failure parks an enrollment; re-verification must free it again."""
    sid = _seq(conn)
    sequences.enroll_leads(conn, sid, [1, 2])
    conn.execute("UPDATE leads SET email_status='invalid' WHERE no=2")
    conn.commit()
    sequences.block_unsendable(conn)
    assert {d["lead_no"] for d in sequences.due_queue(conn)} == {1}

    conn.execute("UPDATE leads SET email_status='valid' WHERE no=2")   # re-verified good
    conn.commit()
    assert sequences.reopen_sendable(conn) == 1
    assert {d["lead_no"] for d in sequences.due_queue(conn)} == {1, 2}


def test_reopen_never_revives_a_replied_or_completed_enrollment(conn):
    sid = _seq(conn)
    sequences.enroll_leads(conn, sid, [1, 2])
    repository.mark_replied(conn, 1, "email")          # -> 'replied'
    conn.execute("UPDATE sequence_enrollments SET status='completed' WHERE lead_no=2")
    conn.commit()
    assert sequences.reopen_sendable(conn) == 0
    assert sequences.due_queue(conn) == []


def test_reopen_leaves_a_still_dead_address_parked(conn):
    sid = _seq(conn)
    sequences.enroll_leads(conn, sid, [1, 2])
    conn.execute("UPDATE leads SET email='' WHERE no=1")
    conn.execute("UPDATE leads SET email_status='invalid' WHERE no=2")
    conn.commit()
    sequences.block_unsendable(conn)
    assert sequences.reopen_sendable(conn) == 0
    assert sequences.due_queue(conn) == []


def test_park_and_reopen_together_settle(conn):
    """Running both every round must reach a fixed point, not flip rows back and forth."""
    sid = _seq(conn)
    sequences.enroll_leads(conn, sid, [1, 2, 3])
    conn.execute("UPDATE leads SET email_status='invalid' WHERE no=2")
    conn.commit()
    for _ in range(3):
        sequences.block_unsendable(conn)
        sequences.reopen_sendable(conn)
    assert {d["lead_no"] for d in sequences.due_queue(conn)} == {1, 3}


def _korean_sequence(conn):
    return sequences.create_sequence(conn, "冷邮件 3 步跟进（韩语）", "email", [
        {"day_offset": 0, "subject": "한국 LED 디스플레이 납품 사례",
         "body": "안녕하세요, 저희는 LED 디스플레이를 공급합니다."}])


def test_korean_sequence_refuses_non_korean_leads(conn):
    """Regression: on 2026-08-13 fifty Brazilian/Chilean leads were enrolled in the
    Korean sequence right after the English one — the lead selection was never cleared
    between the two clicks. A Brazilian integrator must not be sent Korean cold email."""
    sid = _korean_sequence(conn)
    assert sequences.enroll_leads(conn, sid, [1, 2, 3]) == 0
    assert sequences.language_blocked(conn, sid, [1, 2, 3]) == [1, 2, 3]


def test_korean_sequence_accepts_korean_leads(conn):
    conn.execute("UPDATE leads SET country='South Korea' WHERE no=1")
    sid = _korean_sequence(conn)
    assert sequences.enroll_leads(conn, sid, [1, 2]) == 1
    assert sequences.language_blocked(conn, sid, [1, 2]) == [2]


def test_english_sequence_accepts_everyone(conn):
    """English is the working language of the trade — a Korean buyer reading an English
    email is normal, so only the Korean direction is restricted."""
    conn.execute("UPDATE leads SET country='South Korea' WHERE no=1")
    sid = sequences.create_sequence(conn, "冷邮件 3 步跟进（英语）", "email",
                                    [{"day_offset": 0, "body": "Hi, we supply LED"}])
    assert sequences.enroll_leads(conn, sid, [1, 2]) == 2
    assert sequences.language_blocked(conn, sid, [1, 2]) == []
