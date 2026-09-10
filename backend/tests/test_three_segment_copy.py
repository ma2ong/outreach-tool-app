"""Cross-channel contract for docs/127.

These are design-time checks on repo-owned copy. They do not add a runtime quality gate.
"""
from app import copy_segments, seeds, social_queue


def test_social_has_exactly_the_three_customer_families():
    assert tuple(social_queue._FAMILIES) == copy_segments.SEGMENTS
    assert set(social_queue._FAMILIES) == {"rental", "install", "general"}


def test_every_social_variant_is_short_and_asks_one_question():
    for segment, family in social_queue._FAMILIES.items():
        assert len(family) >= 3, segment
        for body in family:
            assert body.count("?") == 1, (segment, body)
            assert len(body.split()) <= 40, (segment, body)


def test_social_copy_drops_the_old_generic_sales_closers():
    retired = ("worth a conversation", "spec-and-pricing contact", "send specs and pricing")
    for family in social_queue._FAMILIES.values():
        for body in family:
            low = body.lower()
            assert not any(phrase in low for phrase in retired)


def test_general_social_copy_qualifies_instead_of_guessing():
    for body in social_queue._FAMILIES["general"]:
        low = body.lower()
        assert "rental" in low
        assert "install" in low
        assert "both" in low or "mix" in low


def test_old_outdoor_social_templates_are_retired_from_the_library():
    retired = set(seeds.RETIRED_TEMPLATES)
    for suffix in ("WA", "IG", "FB"):
        assert f"私信 · 户外为主（英语） · {suffix}" in retired


def test_new_bundled_dm_templates_have_no_outdoor_customer_family():
    names = [name for name, _channel, _subject, _body, _lang in seeds._bundled_templates()]
    assert not any("户外为主" in name for name in names)
