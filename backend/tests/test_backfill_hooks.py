"""Every lead gets an opener, and none of them claims anything (docs/85)."""
import pytest

from app import backfill_hooks as bh
from app import message_guard, personalize, seed_sequences


def test_the_vocabulary_can_all_be_said_in_korean():
    """An unglossed term empties the whole Korean opener, so the two tables have to
    agree — this is the check that keeps them agreeing."""
    missing = [term for _p, term in bh._CATEGORY
               if term not in personalize._HOOK_GLOSS_KO]
    assert not missing, f"没有韩文对照：{missing}"


@pytest.mark.parametrize("business,expected", [
    ("LED display & digital signage solutions", ["digital signage", "LED panels"]),
    ("LED multimedia panel sales & rental (Goiânia)", ["rental", "panel sales"]),
    ("Outdoor LED screen (since 2004)", ["LED panels"]),
    ("Transparent & rental LED screens", ["rental", "LED panels"]),
    ("LED panel distributor", ["distribution", "LED panels"]),
    ("", []),
    (None, []),
])
def test_a_company_is_read_from_what_it_says_about_itself(business, expected):
    assert bh.categories(business) == expected


def test_at_most_two_categories():
    busy = "LED rental screens for events, signage, billboards and fixed installation"
    assert len(bh.categories(busy)) == 2


@pytest.mark.parametrize("lead,expected", [
    ({"business": "LED rental screens", "city": "Goiânia, GO"},
     "Saw the rental work you do around Goiânia."),
    ({"business": "LED rental screens", "website": "x.com"},
     "Saw the rental work on your site."),
    ({"business": "LED rental screens"},
     "Saw the rental work you do."),
    # Nothing quotable: the generic line, never an empty hook.
    ({"business": "since 1998", "city": "Seoul"}, bh.GENERIC_HOOK),
    ({}, bh.GENERIC_HOOK),
])
def test_the_shape_is_one_hook_ko_can_read(lead, expected):
    hook = bh.hook_for(lead)
    assert hook == expected
    assert personalize.hook_ko({"hook": hook}), f"韩语译不出来：{hook}"


def test_korea_reads_the_korean_generic():
    assert personalize.hook_ko({"hook": bh.GENERIC_HOOK}) == bh.GENERIC_HOOK_KO


def test_neither_generic_line_says_anything_about_them():
    """docs/45. Both sentences are about us looking, not about what they do."""
    for line in (bh.GENERIC_HOOK, bh.GENERIC_HOOK_KO):
        assert "your work" not in line.lower()
        assert "{" not in line


def test_a_deliberate_generic_hook_may_be_sent_but_a_missing_one_may_not():
    """docs/85 R4. The exemption is the stored hook, not the sentence — otherwise any
    letter could pass by quoting it."""
    from app.personalize import render

    _o, _d, subject, body = seed_sequences.steps_for("rental", False)[0]
    marked = {"no": 1, "company_en": "Verum AV", "hook": bh.GENERIC_HOOK}
    blank = {"no": 2, "company_en": "Verum AV"}
    assert not message_guard.check(
        render(body, marked), marked, subject=render(subject, marked)).blocked
    assert message_guard.check(
        render(body, blank), blank, subject=render(subject, blank)).blocked
    # And the sentence alone does not buy a pass for a lead nobody looked at.
    assert message_guard.check(bh.GENERIC_HOOK, blank, subject="x").blocked


def test_a_district_in_brackets_is_not_part_of_the_place():
    """"around Seoul (Seocho-gu)" and "around CABA (Pichincha 188)" read as a pasted
    address; the city column holds both shapes."""
    lead = {"business": "LED rental screens", "city": "Seoul (Seocho-gu)"}
    assert bh.hook_for(lead) == "Saw the rental work you do around Seoul."
