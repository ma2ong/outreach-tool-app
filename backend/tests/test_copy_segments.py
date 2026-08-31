"""Which letter a company gets (docs/76).

The order of evidence is the whole design: Allen's own tag beats the classifier's
`target_fit`, which beats the words the company uses about itself. Each step down is
less reliable, and the last step down is to `general` — a neutral letter — rather than
to a guess. A signage company told how their rental business works has already lost the
reader, so not knowing is worth saying nothing about.
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


def test_a_tag_set_by_hand_beats_everything_the_machine_inferred():
    lead = {"tags": "租赁商", "target_fit": "AV集成商 (85)",
            "business": "outdoor billboard operator"}
    assert cs.segment_of(lead) == "rental"


def test_the_machine_tags_in_the_same_column_are_not_customer_types():
    """`icp:signage` is the classifier talking to itself; it must not be read as a type
    Allen chose."""
    assert cs.segment_of({"tags": "icp:signage"}) == "general"


def test_target_fit_is_used_when_no_type_was_set():
    assert cs.segment_of({"target_fit": "租赁公司 (90)"}) == "rental"
    assert cs.segment_of({"target_fit": "AV集成商 (85)"}) == "install"
    assert cs.segment_of({"target_fit": "标识/广告牌 (70)"}) == "outdoor"


@pytest.mark.parametrize("tag", ["透明屏", "代理商", "批发商"])
def test_the_folded_segments_get_the_neutral_letter(tag):
    """These had segments of their own until Allen folded them in: "室内为主，代理批发
    也都归类到中性版". 23 companies do not pay for copy maintained in two languages."""
    assert cs.segment_of({"tags": tag}) == "general"


@pytest.mark.parametrize("text,segment", [
    ("We provide staging and rental LED for concerts", "rental"),
    ("Systems integrator, commercial AV installation", "install"),
    ("Digital billboard and facade advertising", "outdoor"),
    ("무대 렌탈 전문", "rental"),
    ("LED 시공 전문 업체", "install"),
])
def test_what_the_company_says_about_itself_is_the_last_resort(text, segment):
    assert cs.segment_of({"business": text}) == segment


def test_a_company_we_know_nothing_about_gets_the_neutral_letter():
    assert cs.segment_of({}) == "general"
    assert cs.segment_of({"company_en": "Verum AV", "business": "We do great work"}) == "general"


def test_an_end_user_is_not_forced_into_a_segment():
    """终端用户 says who buys, not what they put on a wall — it falls through to the
    business text rather than inventing indoor or outdoor."""
    assert cs.segment_of({"tags": "终端用户"}) == "general"
    assert cs.segment_of({"tags": "终端用户", "business": "stadium facade"}) == "outdoor"


def test_there_are_only_four_segments():
    assert cs.SEGMENTS == ("rental", "install", "outdoor", "general")


def test_every_segment_has_a_label_and_a_sequence():
    from app.seed_sequences import name_for, steps_for
    for segment in cs.SEGMENTS:
        assert segment in cs.LABEL
        for korean in (False, True):
            assert name_for(segment, korean)
            assert len(steps_for(segment, korean)) == 3


def test_counts_covers_the_whole_book_exactly_once(conn):
    conn.executescript("""
        DELETE FROM leads;
        INSERT INTO leads(no, company_en, tags) VALUES
            (1,'A','租赁商'), (2,'B','工程商'), (3,'C',NULL), (4,'D','批发商');
    """)
    conn.commit()
    counts = cs.counts(conn)
    assert sum(counts.values()) == 4
    assert counts["rental"] == 1 and counts["install"] == 1
    # 批发商 and the untagged company both read as general (docs/60 R2)
    assert counts["outdoor"] == 0 and counts["general"] == 2


# --- docs/60 R2: three types, and the old vocabulary still routes -------------------

def test_there_are_only_three_customer_types():
    """Allen cut eight to three: 只保留工程商，租赁商，批发商，其他都删去."""
    from app import customer_types as ct
    assert set(ct.KNOWN) == {"工程商", "租赁商", "批发商"}


@pytest.mark.parametrize("retired,survivor", [
    ("系统集成商", "工程商"),   # both build and install
    ("广告商", "工程商"),       # an outdoor sign is a fixed-install job
    ("代理商", "批发商"),       # both resell; docs/76 already gave them one letter
])
def test_a_retired_type_still_reaches_its_letter(retired, survivor):
    """The book was migrated, but the old words can arrive again on an import. A row
    saying 系统集成商 must not fall quietly through to the neutral letter."""
    assert cs.segment_of({"tags": retired}) == cs.segment_of({"tags": survivor})


@pytest.mark.parametrize("dropped", ["透明屏", "终端用户"])
def test_a_dropped_type_names_no_buyer(dropped):
    """透明屏 is a product and 终端用户 says nothing about how they use a screen."""
    from app import customer_types as ct
    assert ct.canonical_type(dropped) is None
    assert cs.segment_of({"tags": dropped}) == "general"
