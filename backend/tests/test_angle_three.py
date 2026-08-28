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


# --- the copy has to keep selling (docs/74 R4) --------------------------------------

def test_every_angle_names_products_and_capability():
    """Allen rejected the first angle three for dropping the pitch: "还是要继续推销、
    提产品、提能力". Writing around the product gate spares us the work, not the customer,
    so this is asserted rather than left to whoever edits the copy next."""
    from app.agent.send_decision import _PRODUCT_CLAIM_RE
    from app import seed_angle2, seed_angle3
    for label, steps in (("角度二 EN", seed_angle2.EN_STEPS),
                         ("角度二 KO", seed_angle2.KO_STEPS),
                         ("角度三 EN", seed_angle3.EN_STEPS),
                         ("角度三 KO", seed_angle3.KO_STEPS)):
        opener = steps[0][2] + "\n" + steps[0][3]
        assert _PRODUCT_CLAIM_RE.search(opener), f"{label} 的开场白不提产品"


def test_every_pitch_quoted_traces_to_the_product_library(conn):
    """docs/45: a claim without a source is not written. The letter may only name pitches
    that exist as rows, so nobody can widen the range in the copy alone."""
    import re
    from app import seed_angle3
    conn.executescript("""
        DELETE FROM products;
        INSERT INTO products(model, pixel_pitch, agent_approved) VALUES
            ('Indoor Fine Pitch','P0.7-P1.8',1), ('Indoor Commercial','P2-P3',1),
            ('Indoor Rental','P2.6-P3.9',1), ('Outdoor Rental','P3.9-P4.8',1),
            ('Outdoor Fixed','P4-P10',1);
    """)
    conn.commit()
    bounds = set()
    for row in conn.execute("SELECT pixel_pitch FROM products"):
        bounds.update(re.findall(r"\d+(?:\.\d+)?", row["pixel_pitch"]))
    quoted = set(re.findall(r"P(\d+(?:\.\d+)?)", seed_angle3.EN_STEPS[0][3]))
    assert quoted and quoted <= bounds, f"信里的点间距不在产品库内：{quoted - bounds}"


def test_a_letter_carrying_a_price_is_still_refused():
    # ref_price_sqm never leaves the library, and the guard is the second lock.
    from app import message_guard
    lead = {"no": 1, "company_en": "Verum AV", "city": "Houston"}
    verdict = message_guard.check("Rental P2.6 at USD 1200/sqm.", lead, subject="Quote")
    assert verdict.blocked and verdict.reason == "pricing"
