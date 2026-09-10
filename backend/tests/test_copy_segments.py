"""Outbound-copy routing: Rental / Install / General only (docs/127).

Specialised copy requires clear evidence.  Outdoor/indoor is a project attribute, not a
customer type; mixed or uncertain accounts must stay General rather than being guessed
into one side.
"""
import pytest

from app import copy_segments as cs


@pytest.mark.parametrize("tag,segment", [
    ("租赁商", "rental"),
    ("租赁客户", "rental"),
    ("工程商", "install"),
    ("系统集成商", "install"),
    ("批发商", "general"),
    ("代理商", "general"),
])
def test_explicit_customer_type_tags_route_copy(tag, segment):
    assert cs.segment_of({"tags": tag}) == segment


def test_explicit_rental_or_install_tag_beats_weaker_business_text():
    assert cs.segment_of({
        "tags": "租赁商",
        "target_fit": "AV集成商 (85)",
        "business": "fixed installation contractor",
    }) == "rental"


def test_mixed_rental_and_install_tags_use_general():
    assert cs.segment_of({"tags": "租赁商、工程商"}) == "general"


def test_machine_tags_do_not_become_customer_type_copy():
    assert cs.segment_of({"tags": "icp:signage"}) == "general"


@pytest.mark.parametrize("fit,segment", [
    ("租赁公司 (90)", "rental"),
    ("AV集成商 (85)", "install"),
    ("fixed installation contractor", "install"),
    ("rental and fixed installation", "general"),
    ("标识/广告牌 (70)", "general"),
    ("AV", "general"),
])
def test_target_fit_is_conservative(fit, segment):
    assert cs.segment_of({"target_fit": fit}) == segment


@pytest.mark.parametrize("tag", ["outdoor", "户外", "广告商", "透明屏", "终端用户"])
def test_environment_or_non_buyer_tags_do_not_create_a_copy_segment(tag):
    assert cs.segment_of({"tags": tag}) == "general"


def test_outdoor_tag_does_not_hide_clear_rental_evidence():
    assert cs.segment_of({"tags": "outdoor", "business": "LED rental company"}) == "rental"


@pytest.mark.parametrize("text,segment", [
    ("We are an LED rental company for live events", "rental"),
    ("Systems integrator and commercial AV installer", "install"),
    ("Rental inventory plus fixed-install projects", "general"),
    ("Digital billboard and facade advertising", "general"),
    ("Concert and festival production", "general"),
    ("Church and auditorium AV", "general"),
    ("무대 렌탈 전문", "rental"),
    ("LED 설치 전문 업체", "install"),
])
def test_company_description_is_used_only_when_it_clearly_identifies_business_model(text, segment):
    assert cs.segment_of({"business": text}) == segment


def test_unknown_company_gets_general():
    assert cs.segment_of({}) == "general"
    assert cs.segment_of({"company_en": "Verum AV", "business": "We do great work"}) == "general"


def test_there_are_exactly_three_copy_segments():
    assert cs.SEGMENTS == ("rental", "install", "general")
    assert set(cs.LABEL) == set(cs.SEGMENTS)


def test_every_copy_segment_has_email_sequences():
    from app.seed_sequences import name_for, steps_for
    for segment in cs.SEGMENTS:
        for korean in (False, True):
            assert name_for(segment, korean)
            expected = 1 if (not korean and segment in ("general", "install")) else 3
            assert len(steps_for(segment, korean)) == expected


def test_counts_covers_the_whole_book_exactly_once(conn):
    conn.executescript("""
        DELETE FROM leads;
        INSERT INTO leads(no, company_en, tags, business) VALUES
            (1,'A','租赁商',''),
            (2,'B','工程商',''),
            (3,'C',NULL,'outdoor billboard operator'),
            (4,'D','批发商',''),
            (5,'E','租赁商、工程商','');
    """)
    conn.commit()
    counts = cs.counts(conn)
    assert sum(counts.values()) == 5
    assert counts == {"rental": 1, "install": 1, "general": 3}
