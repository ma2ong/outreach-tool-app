"""Which outbound copy family a company gets (docs/127).

Specialist copy is earned by evidence. Rental and Install are useful only when we know
which side the company mainly works on; uncertainty and mixed rental/install companies
get General. Outdoor is a project fact, not a customer type.
"""
import pytest

from app import copy_segments as cs


@pytest.mark.parametrize("tag,segment", [
    ("租赁商", "rental"),
    ("工程商", "install"),
    ("批发商", "general"),
])
def test_allens_own_tag_decides(tag, segment):
    assert cs.segment_of({"tags": tag}) == segment


def test_a_clear_manual_tag_beats_weaker_machine_inference():
    lead = {"tags": "租赁商", "target_fit": "AV集成商 (85)",
            "business": "commercial AV installation"}
    assert cs.segment_of(lead) == "rental"


def test_two_explicit_customer_types_are_general_not_first_match_wins():
    assert cs.segment_of({"tags": "租赁商,工程商"}) == "general"


def test_machine_tags_in_the_same_column_are_not_customer_types():
    assert cs.segment_of({"tags": "icp:signage"}) == "general"


def test_target_fit_is_used_when_no_type_was_set():
    assert cs.segment_of({"target_fit": "租赁公司 (90)"}) == "rental"
    assert cs.segment_of({"target_fit": "AV集成商 (85)"}) == "install"


def test_a_mixed_target_fit_is_general():
    assert cs.segment_of({"target_fit": "AV integration + event rental (90)"}) == "general"


@pytest.mark.parametrize("text", [
    "标识/广告牌 (70)",
    "outdoor billboard operator",
    "Digital billboard and facade advertising",
    "옥외 LED 전광판 운영",
])
def test_outdoor_alone_never_selects_a_copy_segment(text):
    assert cs.segment_of({"target_fit": text, "business": text}) == "general"


@pytest.mark.parametrize("tag", ["透明屏", "代理商", "批发商"])
def test_folded_or_non_workflow_types_get_general(tag):
    assert cs.segment_of({"tags": tag}) == "general"


@pytest.mark.parametrize("text,segment", [
    ("We provide staging and rental LED for concerts", "rental"),
    ("Systems integrator, commercial AV installation", "install"),
    ("무대 렌탈 전문", "rental"),
    ("LED 시공 전문 업체", "install"),
])
def test_what_the_company_says_about_itself_is_the_last_resort(text, segment):
    assert cs.segment_of({"business": text}) == segment


def test_mixed_company_language_is_general():
    assert cs.segment_of({
        "business": "We provide LED rental for events and permanent AV installation"
    }) == "general"


def test_mixed_evidence_across_business_hook_and_brief_is_general():
    assert cs.segment_of({
        "business": "event staging and rental",
        "brief": "also designs and installs permanent commercial AV systems",
    }) == "general"


def test_a_company_we_know_nothing_about_gets_general():
    assert cs.segment_of({}) == "general"
    assert cs.segment_of({"company_en": "Verum AV", "business": "We do great work"}) == "general"


def test_an_end_user_is_not_forced_into_a_segment():
    assert cs.segment_of({"tags": "终端用户"}) == "general"
    assert cs.segment_of({"tags": "终端用户", "business": "stadium facade"}) == "general"


def test_there_are_exactly_three_segments():
    assert cs.SEGMENTS == ("rental", "install", "general")
    assert "outdoor" not in cs.SEGMENTS


def test_every_segment_has_a_label_and_a_sequence():
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
        INSERT INTO leads(no, company_en, tags, business) VALUES
            (1,'A','租赁商',''),
            (2,'B','工程商',''),
            (3,'C',NULL,''),
            (4,'D','批发商',''),
            (5,'E',NULL,'outdoor billboard operator'),
            (6,'F',NULL,'rental staging and permanent AV installation');
    """)
    conn.commit()
    counts = cs.counts(conn)
    assert sum(counts.values()) == 6
    assert counts == {"rental": 1, "install": 1, "general": 4}


# Old CRM vocabulary can still arrive on imports. It may canonicalize to one of the
# three surviving customer types, but it can never resurrect an Outdoor copy family.

def test_retired_installer_alias_still_reaches_install():
    assert cs.segment_of({"tags": "系统集成商"}) == "install"


def test_retired_reseller_alias_reaches_general():
    assert cs.segment_of({"tags": "代理商"}) == "general"


@pytest.mark.parametrize("dropped", ["透明屏", "终端用户"])
def test_a_dropped_type_names_no_workflow(dropped):
    from app import customer_types as ct
    assert ct.canonical_type(dropped) is None
    assert cs.segment_of({"tags": dropped}) == "general"
