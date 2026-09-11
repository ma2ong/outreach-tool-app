"""Outbound customer routing: Rental / Install / General only."""
import pytest

from app import copy_segments as cs


@pytest.mark.parametrize("tag,segment", [
    ("Rental", "rental"),
    ("租赁商", "rental"),
    ("Install", "install"),
    ("工程商", "install"),
    ("General", "general"),
    ("批发商", "general"),
    ("广告商", "general"),
    ("outdoor", "general"),
])
def test_manual_and_legacy_types_route_to_three_segments(tag, segment):
    assert cs.segment_of({"tags": tag}) == segment


def test_manual_type_beats_machine_inference():
    lead = {"tags": "Rental", "target_fit": "AV集成商 (85)",
            "business": "outdoor billboard operator"}
    assert cs.segment_of(lead) == "rental"


def test_mixed_manual_rental_and_install_is_general():
    assert cs.segment_of({"tags": "Rental,Install"}) == "general"
    assert cs.segment_of({"tags": "工程商、租赁客户"}) == "general"


def test_machine_tags_are_not_customer_types():
    assert cs.segment_of({"tags": "icp:signage"}) == "general"


def test_target_fit_only_specialises_clear_rental_or_install():
    assert cs.segment_of({"target_fit": "租赁公司 (90)"}) == "rental"
    assert cs.segment_of({"target_fit": "AV集成商 (85)"}) == "install"
    assert cs.segment_of({"target_fit": "标识/广告牌 (75)"}) == "general"
    assert cs.segment_of({"target_fit": "经销商 (80)"}) == "general"


@pytest.mark.parametrize("text,segment", [
    ("We provide staging and rental LED for concerts", "rental"),
    ("Systems integrator, commercial AV installation", "install"),
    ("Digital billboard and facade advertising", "general"),
    ("무대 렌탈 전문", "rental"),
    ("LED 시공 전문 업체", "install"),
])
def test_business_text_is_last_resort(text, segment):
    assert cs.segment_of({"business": text}) == segment


def test_business_that_does_both_is_general():
    lead = {"business": "AV integration, fixed installation, event staging and rental"}
    assert cs.segment_of(lead) == "general"


def test_unknown_company_is_general():
    assert cs.segment_of({}) == "general"
    assert cs.segment_of({"company_en": "Verum AV", "business": "We do great work"}) == "general"


def test_outdoor_is_a_product_context_not_a_customer_segment():
    assert cs.segment_of({"business": "stadium facade and roadside LED billboards"}) == "general"
    assert "outdoor" not in cs.SEGMENTS


def test_there_are_only_three_segments():
    assert cs.SEGMENTS == ("rental", "install", "general")


def test_every_segment_has_a_label_and_sequence():
    from app.seed_sequences import name_for, steps_for

    for segment in cs.SEGMENTS:
        assert segment in cs.LABEL
        for korean in (False, True):
            assert name_for(segment, korean)
            expected = 1 if (not korean and segment in ("general", "install")) else 3
            assert len(steps_for(segment, korean)) == expected


def test_counts_covers_the_whole_book_exactly_once(conn):
    conn.executescript("""
        DELETE FROM leads;
        INSERT INTO leads(no, company_en, tags) VALUES
            (1,'A','Rental'), (2,'B','Install'), (3,'C',NULL), (4,'D','General'),
            (5,'E','工程商、租赁客户');
    """)
    conn.commit()
    counts = cs.counts(conn)
    assert sum(counts.values()) == 5
    assert counts == {"rental": 1, "install": 1, "general": 3}


def test_customer_type_vocabulary_is_closed_to_three_values():
    from app import customer_types as ct

    assert ct.KNOWN == ("Rental", "Install", "General")
    assert ct.options(conn=None) == ["Rental", "Install", "General"]
