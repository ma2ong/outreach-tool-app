"""The second angle, the type-aware line, and moving on instead of parking (docs/67).

The first English angle sent 361 letters for one reply. Its middle paragraph — "We
manufacture the panels behind that kind of work, indoor and outdoor, P1.86 through P10"
— is a sentence every LED factory in Shenzhen can send, and it asked the reader to open
a project file before they could answer.

What these tests hold is the machinery that makes a second attempt possible: a line
aimed at this kind of buyer, and a follow-up that switches angle rather than stopping.
"""
import pytest

from app import personalize
from app.agent import followup_decision
from app.db import connect, init_schema


@pytest.mark.parametrize("kind,marker", [
    ("租赁商", "load-in"),
    ("工程商", "spec compliance"),
    ("广告商", "brightness"),
    ("代理商", "margin"),
])
def test_the_line_is_aimed_at_this_kind_of_buyer(kind, marker):
    out = personalize.render("{fit}", {"company_en": "X", "tags": kind})
    assert marker in out


def test_an_unknown_type_says_nothing_rather_than_guessing():
    # A line addressed to the wrong kind of company is worse than a shorter letter.
    assert personalize.render("{fit}", {"company_en": "X", "tags": ""}) == ""
    assert personalize.render("{fit}", {"company_en": "X", "tags": "icp:rental"}) == ""


def test_the_korean_letter_gets_the_korean_line():
    out = personalize.render("{fit_ko}", {"company_en": "X", "tags": "租赁商"})
    assert "렌탈" in out
    assert "load-in" not in out


def test_an_empty_line_does_not_leave_a_hole_in_the_letter():
    # Three blank lines mid-letter reads as a template that failed to fill in.
    body = "Hi {contact},\n\n{hook}\n\n{fit}\n\nWe build panels.\n\nBest"
    out = personalize.render(body, {"company_en": "X", "contact_name": "",
                                    "hook": "Saw the work.", "tags": ""})
    assert "\n\n\n" not in out
    assert "Saw the work.\n\nWe build panels." in out


def test_a_korean_greeting_with_no_name_drops_the_honorific_too():
    """"안녕하세요, 님." is an honorific addressed to nobody, which reads worse in Korean
    than the missing name it was covering."""
    tpl = "안녕하세요, {contact}님.\n\n{hook}"
    out = personalize.render(tpl, {"company_en": "X", "contact_name": "",
                                   "hook": "H."})
    assert out.startswith("안녕하세요.")
    assert "님" not in out.splitlines()[0]


def test_a_korean_name_keeps_its_honorific():
    tpl = "안녕하세요, {contact}님.\n\n{fit_ko}"
    out = personalize.render(tpl, {"company_en": "X", "contact_name": "김종수",
                                   "tags": ""})
    assert out.splitlines()[0] == "안녕하세요, 김종수님."


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, email) VALUES
            (1, 'Verum AV', 'USA', 'a@verumav.com');
        INSERT INTO sequences(id, name, channel) VALUES
            (1, '冷邮件 3 步跟进（英语）', 'email'),
            (2, '冷邮件 3 步跟进（英语·角度二）', 'email'),
            (3, '冷邮件 3 步跟进（韩语）', 'email');
        INSERT INTO sequence_enrollments(id, lead_no, sequence_id, current_step, status,
                                         enrolled_at, next_due_date)
        VALUES (10, 1, 1, 2, 'active', '2026-07-01', '2026-08-01');
    """)
    c.commit()
    return c


def test_a_failing_angle_moves_to_the_next_one_instead_of_parking(conn):
    """Parking was half a decision: the system saw the angle was not working and then
    stopped, and 110 follow-ups sat still for weeks."""
    followup_decision.apply(conn, {"enrollment_id": 10, "action": "change_angle"})
    row = conn.execute(
        "SELECT sequence_id, status, current_step FROM sequence_enrollments WHERE id=10"
    ).fetchone()
    assert row["sequence_id"] == 2
    assert row["status"] == "active"
    assert row["current_step"] == 0     # a new opener, not the next line of the old one


def test_it_does_not_wander_into_another_language(conn):
    conn.execute("UPDATE sequence_enrollments SET sequence_id=3 WHERE id=10")
    conn.commit()
    followup_decision.apply(conn, {"enrollment_id": 10, "action": "change_angle"})
    row = conn.execute(
        "SELECT sequence_id, status FROM sequence_enrollments WHERE id=10").fetchone()
    # No Korean angle two exists here, so it parks rather than switching to English.
    assert row["sequence_id"] == 3
    assert row["status"] == "quality_hold"


def test_with_no_further_angle_parking_is_a_real_answer(conn):
    conn.execute("UPDATE sequence_enrollments SET sequence_id=2 WHERE id=10")
    conn.commit()
    followup_decision.apply(conn, {"enrollment_id": 10, "action": "change_angle"})
    status = conn.execute(
        "SELECT status FROM sequence_enrollments WHERE id=10").fetchone()[0]
    assert status == "quality_hold"
