"""The third angle, and the parked letters waiting for it (docs/74 R4).

`_switch_angle` had nowhere to go while angle two was the last one, so 75 enrollments
parked in `quality_hold` — invisible to `due_queue`, which reads only `active`. Adding an
angle fixes nothing by itself; something has to go and get them.
"""
import pytest

from app import sequences
from app.agent import followup_decision as fd


def _angles(conn, *names):
    return [sequences.create_sequence(conn, n, "email", [
        {"step_index": 0, "day_offset": 0, "subject": "s", "body": "b"}]) for n in names]


@pytest.fixture(autouse=True)
def _clean(conn):
    conn.executescript("DELETE FROM sequence_enrollments; DELETE FROM sequence_steps;"
                       " DELETE FROM sequences; DELETE FROM leads;")
    conn.execute("INSERT INTO leads(no, company_en, email) VALUES (1,'Verum','v@v.com')")
    conn.commit()


def _enrol(conn, sid, status="active"):
    return conn.execute(
        "INSERT INTO sequence_enrollments(lead_no, sequence_id, current_step, status,"
        " next_due_date) VALUES (1,?,0,?,date('now'))", (sid, status)).lastrowid


def test_angle_two_moves_on_to_angle_three(conn):
    a2, a3 = _angles(conn, "冷邮件（英语·角度二）", "冷邮件（英语·角度三）")
    eid = _enrol(conn, a2)
    assert fd._switch_angle(conn, eid) is True
    assert conn.execute("SELECT sequence_id FROM sequence_enrollments WHERE id=?",
                        (eid,)).fetchone()[0] == a3


def test_angles_never_go_backwards(conn):
    """Order-by-id alone would send angle three back to angle two, and round forever."""
    a2, a3 = _angles(conn, "冷邮件（英语·角度二）", "冷邮件（英语·角度三）")
    eid = _enrol(conn, a3)
    assert fd._switch_angle(conn, eid) is False
    assert conn.execute("SELECT sequence_id FROM sequence_enrollments WHERE id=?",
                        (eid,)).fetchone()[0] == a3


def test_a_language_never_switches_into_another_language(conn):
    _en2, _en3 = _angles(conn, "冷邮件（英语·角度二）", "冷邮件（英语·角度三）")
    ko2, = _angles(conn, "冷邮件（韩语·角度二）")
    eid = _enrol(conn, ko2)
    assert fd._switch_angle(conn, eid) is False


def test_parked_letters_are_brought_back_when_an_angle_appears(conn):
    a2, a3 = _angles(conn, "冷邮件（英语·角度二）", "冷邮件（英语·角度三）")
    eid = _enrol(conn, a2, status="quality_hold")
    assert fd.revive_parked(conn) == 1
    row = conn.execute("SELECT sequence_id, status, current_step FROM sequence_enrollments"
                       " WHERE id=?", (eid,)).fetchone()
    assert (row["sequence_id"], row["status"], row["current_step"]) == (a3, "active", 0)


def test_a_revived_letter_is_visible_to_the_send_queue_again(conn):
    # Parking made them invisible; being revived has to actually put them back in front
    # of the sender, not merely change a column.
    a2, _a3 = _angles(conn, "冷邮件（英语·角度二）", "冷邮件（英语·角度三）")
    _enrol(conn, a2, status="quality_hold")
    assert sequences.due_queue(conn, "email") == []
    fd.revive_parked(conn)
    assert len(sequences.due_queue(conn, "email")) == 1


def test_nothing_is_revived_when_there_is_no_further_angle(conn):
    a3, = _angles(conn, "冷邮件（英语·角度三）")
    _enrol(conn, a3, status="quality_hold")
    assert fd.revive_parked(conn) == 0
