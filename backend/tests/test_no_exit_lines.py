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
            "This is Allen from Shenzhen Maxcolor — we build the panels ourselves.\n"
            "Our R3 rental series runs P2.6-P3.9 indoor at 1,000-1,200 nits.\n\n"
            "Tell me the pitch you work with and I'll send the spec sheet the same day.")
    assert not message_guard.check(body, LEAD, subject="Maxcolor R3 rental").blocked
