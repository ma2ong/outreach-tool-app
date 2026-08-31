"""What the cold letters must and must not contain (docs/76, docs/75, docs/74).

There are twelve openers now — six segments in two languages — which is exactly why these
rules are asserted rather than trusted to whoever edits the copy next. Three of them pull
against each other:

  * every letter must sell — "还是要继续推销、提产品、提能力". A letter that dodges the
    product gate by not mentioning products spares us the work, not the customer.
  * no letter may price. Pricing is Allen's, never the agent's.
  * no letter may name a pitch the product library does not have (docs/45).

And one that only exists because there are now many: they must not all be the same letter.
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


def test_the_korean_letter_reaches_the_same_gate_as_the_english_one():
    """패널 and 피치 were missing from the pattern, so a Korean letter could claim what
    we manufacture without ever passing the check its English half had to."""
    assert _PRODUCT_CLAIM_RE.search("LED 패널을 직접 만듭니다")
    assert _PRODUCT_CLAIM_RE.search("파인피치 P0.7")


@pytest.mark.parametrize("segment,korean", ALL)
def test_no_letter_carries_a_price(segment, korean):
    lead = {"no": 1, "company_en": "Verum AV", "city": "Houston"}
    for _o, _d, subject, body in seed_sequences.steps_for(segment, korean):
        assert not message_guard.check(body, lead, subject=subject).reason == "pricing"


def test_a_letter_that_did_carry_a_price_would_be_refused():
    lead = {"no": 1, "company_en": "Verum AV", "city": "Houston"}
    verdict = message_guard.check("Rental P2.6 at USD 1200/sqm.", lead, subject="Quote")
    assert verdict.blocked and verdict.reason == "pricing"


@pytest.mark.parametrize("segment,korean", ALL)
def test_every_pitch_quoted_exists_in_the_product_library(conn, segment, korean):
    """docs/45: a claim without a source is not written. The copy may not widen the
    range on its own."""
    conn.executescript("""
        DELETE FROM products;
        INSERT INTO products(model, pixel_pitch, agent_approved) VALUES
            ('Indoor Fine Pitch','P0.7-P1.8',1), ('Indoor Commercial','P2-P3',1),
            ('Indoor Rental','P2.6-P3.9',1), ('Outdoor Rental','P3.9-P4.8',1),
            ('Outdoor Fixed','P4-P10',1);
    """)
    conn.commit()
    bounds = set()
    for row in conn.execute("SELECT pixel_pitch FROM products"):
        bounds.update(re.findall(r"\d+(?:\.\d+)?", row["pixel_pitch"]))
    body = seed_sequences.steps_for(segment, korean)[0][3]
    quoted = set(re.findall(r"P(\d+(?:\.\d+)?)", body))
    assert quoted <= bounds, f"{segment} 里的点间距不在产品库内：{quoted - bounds}"


def test_the_segments_do_not_all_get_the_same_letter():
    """The whole point of docs/76 — "文案不要一模一样". rental and general share a
    subject line on purpose (both ask about the cabinet), so bodies are what must differ."""
    for korean in (False, True):
        bodies = {seed_sequences.steps_for(s, korean)[0][3]
                  for s in copy_segments.SEGMENTS}
        assert len(bodies) == len(copy_segments.SEGMENTS)


def test_the_last_letter_is_deliberately_shared():
    """Differences cost maintenance; by the third letter it no longer matters whether
    they rent or install (docs/76 R2)."""
    from app.seed_sequences import SINGLE_TOUCH
    for korean in (False, True):
        # docs/82 R10: 只发一封的分段没有第三封可比
        closings = {seed_sequences.steps_for(s, korean)[2][3]
                    for s in copy_segments.SEGMENTS
                    if (s, korean) not in SINGLE_TOUCH}
        assert len(closings) == 1


@pytest.mark.parametrize("segment,korean", ALL)
def test_the_steps_obey_the_two_week_rule(segment, korean):
    """The sequence's own schedule cannot outrun the frequency rule (docs/75 R1)."""
    offsets = [offset for _o, offset, _s, _b in seed_sequences.steps_for(segment, korean)]
    assert offsets[0] == 0
    assert all(b - a >= COOLDOWN_DAYS for a, b in zip(offsets, offsets[1:]))


def test_no_sequence_is_named_after_an_angle_any_more():
    for segment, korean in ALL:
        assert "角度" not in seed_sequences.name_for(segment, korean)
