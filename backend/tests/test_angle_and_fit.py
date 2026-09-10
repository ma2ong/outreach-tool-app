"""Type-aware fit copy and follow-up ownership tests."""
import pytest

from app import personalize
from app.agent import followup_decision
from app.db import connect, init_schema


@pytest.mark.parametrize("kind,marker", [
    ("Rental", "reload every week"),
    ("Install", "three years after the install"),
    ("General", "broad LED range"),
    # Legacy tags must canonicalise into the same three outward types.
    ("广告商", "broad LED range"),
    ("代理商", "broad LED range"),
])
def test_the_line_is_aimed_at_the_three_customer_types(kind, marker):
    out = personalize.render("{fit}", {"company_en": "X", "tags": kind})
    assert marker in out


def test_an_unknown_type_says_nothing_rather_than_guessing():
    # An ICP marker alone is not a manually/canonically assigned customer type here.
    assert personalize.render("{fit}", {"company_en": "X", "tags": ""}) == ""
    assert personalize.render("{fit}", {"company_en": "X", "tags": "icp:rental"}) == ""


def test_the_korean_letter_gets_the_korean_rental_line():
    out = personalize.render("{fit_ko}", {"company_en": "X", "tags": "Rental"})
    assert "캐비닛" in out
    assert "reload" not in out


def test_an_empty_line_does_not_leave_a_hole_in_the_letter():
    body = "Hi {contact},\n\n{hook}\n\n{fit}\n\nWe build panels.\n\nBest"
    out = personalize.render(body, {"company_en": "X", "contact_name": "",
                                    "hook": "Saw the work.", "tags": ""})
    assert "\n\n\n" not in out
    assert "I noticed the work.\n\nWe build panels." in out


def test_a_korean_greeting_with_no_name_drops_the_honorific_too():
    tpl = "안녕하세요, {contact}님.\n\n{hook}"
    out = personalize.render(tpl, {"company_en": "X", "contact_name": "",
                                   "hook": "H."})
    assert out.startswith("안녕하세요.")
    assert "님" not in out.splitlines()[0]


def test_a_korean_name_is_never_spoken_but_a_known_title_is():
    tpl = "안녕하세요, {contact}님.\n\n{fit_ko}"
    base = {"company_en": "X", "contact_name": "김종수", "tags": ""}
    named = personalize.render(tpl, base).splitlines()[0]
    titled = personalize.render(tpl, {**base, "title": "대표"}).splitlines()[0]
    assert named == "안녕하세요."
    assert titled == "안녕하세요, 대표님."


@pytest.mark.parametrize("hook,expected_fragment", [
    ("Saw P1, P2 and P2.5 panels listed on your site.", "P1, P2, P2.5"),
    ("Saw the LED signage work you do around Hwaseong.", "LED 전광판"),
    ("Saw the rental and events work on your site.", "렌탈 · 행사"),
])
def test_the_korean_letter_gets_a_korean_opener(hook, expected_fragment):
    out = personalize.render("{hook_ko}", {"company_en": "X", "hook": hook})
    assert expected_fragment in out
    assert "Saw" not in out


@pytest.mark.parametrize("hook", ["Saw the widget work on your site.", "", None])
def test_an_unfamiliar_opener_falls_back_to_the_generic_korean_line(hook):
    from app.backfill_hooks import GENERIC_HOOK_KO

    lead = {"company_en": "X", "hook": hook}
    assert personalize.hook_ko(lead) == ""
    out = personalize.render("{hook_ko}", lead)
    assert out == GENERIC_HOOK_KO
    assert "Saw" not in out


def test_a_dash_with_nothing_after_it_goes_too():
    out = personalize.render("We build panels — {fit}.", {"company_en": "X", "tags": ""})
    assert out == "We build panels."


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


def test_a_delay_moves_the_due_date_and_nothing_else(conn):
    followup_decision.apply(conn, {"enrollment_id": 10, "action": "delay",
                                   "next_due_date": "2026-09-15"})
    row = conn.execute(
        "SELECT sequence_id, status, current_step, next_due_date"
        " FROM sequence_enrollments WHERE id=10").fetchone()
    assert row["status"] == "active"
    assert row["next_due_date"] == "2026-09-15"
    assert (row["sequence_id"], row["current_step"]) == (1, 2)


def test_nothing_parks_any_more(conn):
    followup_decision.apply(conn, {"enrollment_id": 10, "action": "delay",
                                   "next_due_date": "2026-09-15"})
    assert conn.execute(
        "SELECT COUNT(*) FROM sequence_enrollments WHERE status='quality_hold'"
    ).fetchone()[0] == 0
