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


def test_the_generic_line_claims_only_what_the_book_supports():
    """docs/45 asks for a source, not for silence. Every row in this book is here
    because it was identified as an LED company or already bought panels, so "you work
    with LED displays" is sourced — and nothing narrower than that is."""
    assert "LED display" in bh.GENERIC_HOOK
    assert "LED 디스플레이" in bh.GENERIC_HOOK_KO
    for line in (bh.GENERIC_HOOK, bh.GENERIC_HOOK_KO):
        assert "{" not in line
    # No claim about a segment, a city or a project — those are the things it cannot know.
    for word in ("rental", "outdoor", "install", "signage"):
        assert word not in bh.GENERIC_HOOK.lower()


def test_a_missing_hook_is_now_the_generic_one_rather_than_a_hold():
    """docs/100 推翻了这条测试原来的下半段。

    Allen 09-04：「空 hook 也不要拦，直接用通用 hook。」渲染时空开场白就变成同一句
    通用句，所以「刻意标记的通用 hook」和「还没查到东西」在信里是同一封信 —— 判成
    两种结果没有道理，而代价是一封本来该发的信没发。

    没变的是 docs/85 R4 的另一半：光在正文里引用那句话，不能替一封什么都没说的信买路。
    """
    from app.personalize import render

    _o, _d, subject, body = seed_sequences.steps_for("rental", False)[0]
    marked = {"no": 1, "company_en": "Verum AV", "hook": bh.GENERIC_HOOK}
    blank = {"no": 2, "company_en": "Verum AV"}
    for lead in (marked, blank):
        assert not message_guard.check(
            render(body, lead), lead, subject=render(subject, lead)).blocked
    # 没变的那一半：一家我们查到过真开场白的公司，信里必须写着**它自己**那句话；
    # 光抄那句人人都有的通用句买不到路。
    real = {"no": 3, "company_en": "Verum AV", "hook": "Saw the arena screen you built."}
    assert message_guard.check(bh.GENERIC_HOOK, real, subject="x").blocked


def test_a_district_in_brackets_is_not_part_of_the_place():
    """"around Seoul (Seocho-gu)" and "around CABA (Pichincha 188)" read as a pasted
    address; the city column holds both shapes."""
    lead = {"business": "LED rental screens", "city": "Seoul (Seocho-gu)"}
    assert bh.hook_for(lead) == "Saw the rental work you do around Seoul."
