"""No letter offers to go away (docs/82).

Allen banned the whole shape after one went out:

    If ours won't mix with your stock I'll say so and leave it there.

His reasoning is the right one, and it is worth keeping next to the tests: a cold email
from an unknown Shenzhen factory puts the reader under no pressure at all, so offering
a way out of a pressure that does not exist only says the quiet part for them. Three
thousand letters in his own hand contain none of it.

Two layers are tested, because copy is data: the seed copy must be clean, and the guard
on the send path must refuse it even when the copy came from an edited database row.
"""
import pytest

from app import message_guard, seed_sequences
from app.copy_segments import SEGMENTS

LEAD = {"no": 1, "company_en": "Verum AV", "website": "verumav.com",
        "city": "Austin", "hook": "Saw the rental work on your site.",
        "contact_name": "Sam"}


def _rendered(segment, korean):
    from app.personalize import render
    for _order, _offset, subject, body in seed_sequences.steps_for(segment, korean):
        yield render(subject, LEAD), render(body, LEAD)


@pytest.mark.parametrize("korean", [False, True])
@pytest.mark.parametrize("segment", SEGMENTS)
def test_no_step_of_any_sequence_offers_to_stop(segment, korean):
    for subject, body in _rendered(segment, korean):
        verdict = message_guard.check(body, LEAD, subject=subject)
        assert not verdict.blocked, f"{segment}/{'ko' if korean else 'en'}: {verdict.detail}"


@pytest.mark.parametrize("korean", [False, True])
@pytest.mark.parametrize("segment", SEGMENTS)
def test_every_opener_names_the_factory_and_a_product(segment, korean):
    """docs/82 R2: who we are, a spec they can react to, and something concrete on
    offer. Not a fixed phrase — Allen took the "same day" promise out because the
    close read as an instruction rather than an offer."""
    subject, body = next(iter(_rendered(segment, korean)))
    text = " ".join((subject + " " + body).split())
    assert "Maxcolor" in text or "맥스컬러" in text, "the letter never says who is writing"
    assert "P0.7" in text or "P2" in text or "P4" in text, "no pitch to react to"
    assert any(w in text for w in ("spec", "sheet", "사양")), "nothing concrete offered"


@pytest.mark.parametrize("line", [
    "If ours won't mix with your stock I'll say so and leave it there.",
    "Last note. If panels aren't on your plan, that's a fine answer.",
    "Not your area? Point me at whoever handles displays and I'll stop here.",
    "I don't want to fill up your inbox.",
    "that tells me whether we're worth your time",
    "기존 장비와 안 맞으면 솔직히 말씀드리고 더 연락드리지 않겠습니다.",
    "마지막 메일입니다.",
    "如果打扰到您，我以后不再联系。",
])
def test_the_guard_refuses_an_exit_line_on_any_channel(line):
    """The rule lives on the send path, not only in the seed file: copy is rows in a
    database and can be edited from the UI."""
    for channel in ("email", "instagram", "whatsapp", "facebook"):
        verdict = message_guard.check(f"Verum AV — {line}", LEAD, channel=channel)
        assert verdict.blocked and verdict.reason == "exit_line", (channel, line)


def test_a_letter_in_allens_own_shape_passes():
    body = ("Hi Sam,\n\nSaw the rental work on your site.\n\n"
            "This is Allen from Shenzhen Maxcolor Visual, an LED display manufacturer\n"
            "in Shenzhen.\n\n"
            "For rental work we run P2.6-P3.9 indoor at 600-800 nits, die-cast\n"
            "cabinets, front and rear service.\n\n"
            "If any of this is close to what you use, I'd be glad to send the spec sheet.")
    assert not message_guard.check(body, LEAD, subject="rental LED specs").blocked


# --- docs/82 R4, R5, R6: three more shapes the guard now refuses ---------------------

@pytest.mark.parametrize("line,reason", [
    # R6 迎合：回答一个没人提出的抱怨，把自己放在让步的位置
    ("Shipping to Brazil? No problem at all, we do it weekly.", "hedging"),
    ("If the pitch is not right we can change it, that is fine to adjust later.", "hedging"),
    ("배송은 문제 없습니다.", "hedging"),
    ("这个没问题，我们每周都发。", "hedging"),
    # R4 强调自己造：替一个没人提出的质疑辩护
    ("We build the panels ourselves.", "self_made"),
    ("Everything is made in our own factory in Shenzhen.", "self_made"),
    ("저희는 자체 공장에서 패널을 직접 만듭니다.", "self_made"),
    ("The specs come from us rather than from a trader passing on a datasheet.", "self_made"),
    # R5 派活：在对方还没同意做生意之前先要信息
    ("Tell me the pitch and size and I'll send the spec sheet.", "instruction"),
    ("Send me two things about the job and you will have them back.", "instruction"),
    ("Please confirm the cabinet size you use.", "instruction"),
])
def test_the_guard_refuses_the_three_later_shapes(line, reason):
    # 句首才算派活："…and I'll send you the sheet, tell me the size" 不是同一回事
    verdict = message_guard.check(f"Verum AV. {line}", LEAD, channel="email")
    assert verdict.blocked and verdict.reason == reason, (line, verdict.reason)


@pytest.mark.parametrize("line", [
    # 说能力，不说让步
    "We ship to Brazil weekly.",
    # 报身份，不强调
    "This is Allen from Shenzhen Maxcolor Visual, an LED display manufacturer in Shenzhen.",
    "저는 심천 LED 디스플레이 제조업체 맥스컬러의 Allen입니다.",
    # 提供，不指派
    "Happy to send the spec sheet for whichever pitch you use, whenever it is useful.",
    "관심 있으신 사양이 있으시면 사양서 기꺼이 보내드리겠습니다.",
    "If any of this is close to what you use, I'd be glad to send the spec sheet.",
])
def test_the_shapes_that_replace_them_still_pass(line):
    assert not message_guard.check(f"Verum AV — {line}", LEAD, channel="email").blocked


def test_every_stored_piece_of_copy_would_actually_send(conn_with_copy):
    """The whole point: 46 stored templates and steps, none refused."""
    from app import copy_health
    out = copy_health.scan(conn_with_copy)
    assert out["refused"] == [], out["by_reason"]


@pytest.fixture
def conn_with_copy(tmp_path):
    from app import seeds, seed_sequences
    from app.db import connect, init_schema
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    seeds.seed_templates(c)
    for segment in SEGMENTS:
        for korean in (False, True):
            seed_sequences.seed(c, seed_sequences.name_for(segment, korean),
                                seed_sequences.steps_for(segment, korean))
    c.commit()
    return c
