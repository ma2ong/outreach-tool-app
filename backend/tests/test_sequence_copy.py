"""What the cold letter must and must not contain (docs/75 R4, docs/74 R4).

The angle machinery is gone, so what used to be "angle two" is simply the sequence. Its
copy still carries two standing rules from Allen, and they pull in opposite directions,
which is why both are asserted here rather than left to whoever edits the text next:

  * it must sell — "还是要继续推销、提产品、提能力". A letter that dodges the product
    gate by not mentioning products spares us the work, not the customer.
  * it must not price — pricing is Allen's, never the agent's.
"""
import re

import pytest

from app import message_guard, seed_angle2
from app.agent.send_decision import _PRODUCT_CLAIM_RE


def test_both_languages_name_products_and_capability():
    for label, steps in (("英语", seed_angle2.EN_STEPS), ("韩语", seed_angle2.KO_STEPS)):
        opener = steps[0][2] + "\n" + steps[0][3]
        assert _PRODUCT_CLAIM_RE.search(opener), f"{label}开场白不提产品"


def test_the_korean_letter_reaches_the_same_gate_as_the_english_one():
    """패널 and 피치 were missing from the pattern, so a Korean letter could claim what
    we manufacture without ever passing the check its English half had to."""
    assert _PRODUCT_CLAIM_RE.search("LED 패널을 직접 만듭니다")
    assert _PRODUCT_CLAIM_RE.search("파인피치 P0.7")


def test_a_letter_carrying_a_price_is_refused():
    lead = {"no": 1, "company_en": "Verum AV", "city": "Houston"}
    verdict = message_guard.check("Rental P2.6 at USD 1200/sqm.", lead, subject="Quote")
    assert verdict.blocked and verdict.reason == "pricing"


@pytest.mark.parametrize("steps", [seed_angle2.EN_STEPS, seed_angle2.KO_STEPS])
def test_the_steps_obey_the_two_week_rule(steps):
    """The sequence's own schedule cannot outrun the frequency rule (docs/75 R1)."""
    from app.agent.followup_decision import COOLDOWN_DAYS
    offsets = [offset for _order, offset, _s, _b in steps]
    assert offsets[0] == 0
    gaps = [b - a for a, b in zip(offsets, offsets[1:])]
    assert all(g >= COOLDOWN_DAYS for g in gaps), f"步距 {offsets} 小于 {COOLDOWN_DAYS} 天"


def test_no_angle_sequences_are_seeded_any_more():
    assert "角度" not in seed_angle2.EN_NAME and "角度" not in seed_angle2.KO_NAME
