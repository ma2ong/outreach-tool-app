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
            ('Indoor Fine Pitch','P0.6-P1.8',1), ('Indoor Commercial','P2-P4',1),
            ('Indoor Rental','P2.6-P3.9',1), ('Outdoor Rental','P3.9-P4.8',1),
            ('Outdoor Fixed','P2.5-P10',1);
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
    for korean in (False, True):
        closings = {steps[2][3] for steps in
                    (seed_sequences.steps_for(s, korean) for s in copy_segments.SEGMENTS)
                    if len(steps) == 3}
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


def test_shortening_a_sequence_does_not_strand_anyone(conn):
    """The English neutral and fixed-install letters 2 and 3 were deleted outright, and
    88 companies were parked on them. The due queue joins on step_order, so they would
    have gone quiet without ever leaving 'active'."""
    seq_id = seed_sequences.seed(conn, "测试序列", [
        (0, 0, "one", "body one"), (1, 14, "two", "body two")])
    conn.executemany(
        "INSERT INTO sequence_enrollments(lead_no, sequence_id, current_step, status,"
        " enrolled_at) VALUES (?,?,?,?, '2026-08-01')",
        [(1, seq_id, 1, "active"), (2, seq_id, 0, "active"), (3, seq_id, 1, "blocked")])

    seed_sequences.seed(conn, "测试序列", [(0, 0, "one", "body one")])
    assert seed_sequences.close_orphaned_enrollments(conn) == 1

    status = dict(conn.execute(
        "SELECT lead_no, status FROM sequence_enrollments").fetchall())
    assert status[1] == "completed"   # was waiting on the deleted letter
    assert status[2] == "active"      # still has a step to send
    assert status[3] == "blocked"     # not ours to reopen


@pytest.mark.parametrize("segment,korean", ALL)
def test_the_seven_limits_hold(segment, korean):
    """Allen's seven, as limits rather than as copy: 这7样都要按照我说的删掉或者改掉，
    不能出现那7样. Six are visible in the text; the seventh is the letter count."""
    _o, _d, subject, body = seed_sequences.steps_for(segment, korean)[0]
    text = f"{subject}\n{body}"
    signature, letter = text.rsplit("Allen Ma ·", 1)[0], text
    assert "{company}" not in text                       # 1 主题正文都不出现公司名
    assert "Maxcolor" not in signature                   # 2 品牌只留在签名档
    assert "맥스컬러" not in signature
    assert "{fit" not in text                            # 3 {fit} 是废话
    assert "800-1,200" not in text and "1,000-1,200" not in text   # 4 室内 600-800
    for phrase in ("build the panels ourselves", "own factory",    # 5 不强调自己造
                   "자체 공장", "직접 만듭니다"):
        assert phrase not in letter
    for steps in [seed_sequences.steps_for(segment, korean)]:
        for _o2, _d2, _s2, b2 in steps:
            assert "Not your area" not in b2             # 6 「Not your area?」
            assert "담당이 아니시면" not in b2
    # 7 英文中性版和固定安装只发一封
    expected = 1 if (not korean and segment in ("general", "install")) else 3
    assert len(seed_sequences.steps_for(segment, korean)) == expected
