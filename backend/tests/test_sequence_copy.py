"""What the system-owned cold letters must and must not contain (docs/127).

There are only three customer-facing copy families: Rental, Install and General. These
checks are design-time constraints on repo-owned copy, not a new runtime send gate.
"""
import re

import pytest

from app import copy_segments, message_guard, seed_sequences
from app.agent.followup_decision import COOLDOWN_DAYS
from app.agent.send_decision import _PRODUCT_CLAIM_RE

ALL = [(segment, korean) for korean in (False, True)
       for segment in copy_segments.SEGMENTS]


@pytest.mark.parametrize("segment,korean", ALL)
def test_every_opener_names_products_or_capability(segment, korean):
    _order, _offset, subject, body = seed_sequences.steps_for(segment, korean)[0]
    assert _PRODUCT_CLAIM_RE.search(f"{subject}\n{body}"), f"{segment} 开场白不提产品"


def test_there_are_only_three_system_copy_families():
    assert set(seed_sequences.EN_OPENER) == {"rental", "install", "general"}
    assert set(seed_sequences.KO_OPENER) == {"rental", "install", "general"}
    assert set(seed_sequences.EN_SECOND) == {"rental", "install", "general"}
    assert set(seed_sequences.KO_SECOND) == {"rental", "install", "general"}
    assert "outdoor" not in seed_sequences.EN_OPENER
    assert "outdoor" not in seed_sequences.KO_OPENER


def test_the_korean_letter_reaches_the_same_product_gate_as_english():
    assert _PRODUCT_CLAIM_RE.search("LED 패널을 공급합니다")
    assert _PRODUCT_CLAIM_RE.search("파인피치 P0.7")


@pytest.mark.parametrize("segment,korean", ALL)
def test_no_letter_carries_a_price(segment, korean):
    lead = {"no": 1, "company_en": "Verum AV", "city": "Houston"}
    for _o, _d, subject, body in seed_sequences.steps_for(segment, korean):
        assert message_guard.check(body, lead, subject=subject).reason != "pricing"


def test_a_letter_that_did_carry_a_price_would_be_refused():
    lead = {"no": 1, "company_en": "Verum AV", "city": "Houston"}
    verdict = message_guard.check("Rental P2.6 at USD 1200/sqm.", lead, subject="Quote")
    assert verdict.blocked and verdict.reason == "pricing"


@pytest.mark.parametrize("segment,korean", ALL)
def test_every_pitch_quoted_exists_in_the_product_library(conn, segment, korean):
    conn.executescript("""
        DELETE FROM products;
        INSERT INTO products(model, pixel_pitch, agent_approved) VALUES
            ('Indoor Fine Pitch','P0.6-P1.8',1), ('Indoor Commercial','P2-P4',1),
            ('Indoor Rental','P2.6-P3.9',1), ('Outdoor Rental','P3.9-P4.8',1),
            ('Outdoor Fixed','P2.5-P10',1);
    """)
    conn.commit()
    bounds = set()
    for row in conn.execute("SELECT pixel_pitch FROM products"):
        bounds.update(re.findall(r"\d+(?:\.\d+)?", row["pixel_pitch"]))
    body = seed_sequences.steps_for(segment, korean)[0][3]
    quoted = set(re.findall(r"P(\d+(?:\.\d+)?)", body))
    assert quoted <= bounds, f"{segment} 里的点间距不在产品库内：{quoted - bounds}"


def test_the_three_segments_do_not_get_the_same_opener():
    for korean in (False, True):
        bodies = {seed_sequences.steps_for(s, korean)[0][3]
                  for s in copy_segments.SEGMENTS}
        assert len(bodies) == 3


@pytest.mark.parametrize("segment,korean", ALL)
def test_every_opener_ends_with_one_low_friction_question(segment, korean):
    _o, _d, _subject, body = seed_sequences.steps_for(segment, korean)[0]
    assert body.count("?") == 1, f"{segment} opener should ask exactly one question"


@pytest.mark.parametrize("segment,korean", ALL)
def test_openers_do_not_use_the_old_generic_closers(segment, korean):
    body = seed_sequences.steps_for(segment, korean)[0][3].lower()
    for phrase in (
        "worth a conversation",
        "spec-and-pricing contact",
        "whenever it's convenient",
        "no rush on my side",
    ):
        assert phrase not in body


def test_general_opener_asks_which_workflow_the_company_is_in():
    en = seed_sequences.steps_for("general", False)[0][3].lower()
    ko = seed_sequences.steps_for("general", True)[0][3]
    assert "rental" in en and "fixed install" in en and "both" in en
    assert "렌탈" in ko and "고정 설치" in ko and "둘 다" in ko


def test_the_last_letter_is_deliberately_shared_where_a_last_letter_exists():
    for korean in (False, True):
        closings = {steps[2][3] for steps in
                    (seed_sequences.steps_for(s, korean) for s in copy_segments.SEGMENTS)
                    if len(steps) == 3}
        assert len(closings) == 1


@pytest.mark.parametrize("segment,korean", ALL)
def test_the_steps_obey_the_two_week_rule(segment, korean):
    offsets = [offset for _o, offset, _s, _b in seed_sequences.steps_for(segment, korean)]
    assert offsets[0] == 0
    assert all(b - a >= COOLDOWN_DAYS for a, b in zip(offsets, offsets[1:]))


def test_no_sequence_is_named_after_an_angle_any_more():
    for segment, korean in ALL:
        assert "角度" not in seed_sequences.name_for(segment, korean)


def test_shortening_a_sequence_does_not_strand_anyone(conn):
    seq_id = seed_sequences.seed(conn, "测试序列", [
        (0, 0, "one", "body one"), (1, 14, "two", "body two")])
    conn.executemany(
        "INSERT INTO sequence_enrollments(lead_no, sequence_id, current_step, status,"
        " enrolled_at) VALUES (?,?,?,?, '2026-08-01')",
        [(1, seq_id, 1, "active"), (2, seq_id, 0, "active"), (3, seq_id, 1, "blocked")])

    seed_sequences.seed(conn, "测试序列", [(0, 0, "one", "body one")])
    assert seed_sequences.close_orphaned_enrollments(conn) == 1

    status = dict(conn.execute(
        "SELECT lead_no, status FROM sequence_enrollments").fetchall())
    assert status[1] == "completed"
    assert status[2] == "active"
    assert status[3] == "blocked"


@pytest.mark.parametrize("segment,korean", ALL)
def test_the_existing_copy_limits_still_hold(segment, korean):
    _o, _d, subject, body = seed_sequences.steps_for(segment, korean)[0]
    text = f"{subject}\n{body}"
    signature, letter = text.rsplit("Allen Ma ·", 1)[0], text
    assert "{company}" not in text
    assert "Maxcolor" not in signature
    assert "맥스컬러" not in signature
    assert "{fit" not in text
    assert "800-1,200" not in text and "1,000-1,200" not in text
    for phrase in ("build the panels ourselves", "own factory", "자체 공장", "직접 만듭니다"):
        assert phrase not in letter
    for steps in [seed_sequences.steps_for(segment, korean)]:
        for _o2, _d2, _s2, b2 in steps:
            assert "Not your area" not in b2
            assert "담당이 아니시면" not in b2
    expected = 1 if (not korean and segment in ("general", "install")) else 3
    assert len(seed_sequences.steps_for(segment, korean)) == expected
