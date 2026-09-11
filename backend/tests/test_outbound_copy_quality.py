"""Regression checks for the outbound copy rules Allen asked us to keep."""
from app import copy_segments
from app import social_queue
from app.seed_sequences import EN_OPENER, KO_OPENER


def test_social_copy_has_exactly_three_customer_families():
    assert set(social_queue._FAMILIES) == {"rental", "install", "general"}
    assert "outdoor" not in social_queue._FAMILIES


def test_email_copy_has_exactly_three_customer_families():
    expected = set(copy_segments.SEGMENTS)
    assert set(EN_OPENER) == expected == {"rental", "install", "general"}
    assert set(KO_OPENER) == expected


def test_social_copy_avoids_old_salesy_phrases():
    bodies = "\n".join(body for family in social_queue._FAMILIES.values() for body in family).lower()
    for phrase in (
        "worth a conversation",
        "no distributor in between",
        "spec-and-pricing contact",
    ):
        assert phrase not in bodies


def test_social_copy_always_gives_an_easy_next_action():
    for family in social_queue._FAMILIES.values():
        for body in family:
            lower = body.lower()
            assert any(word in lower for word in ("pitch", "application", "project", "size"))
            assert len(body) <= 320


def test_general_copy_can_mention_outdoor_as_product_context():
    # Outdoor is still an important LED application; it is only removed as a buyer type.
    assert "outdoor" in EN_OPENER["general"][1].lower()
    assert copy_segments.segment_of({"business": "outdoor billboard operator"}) == "general"
