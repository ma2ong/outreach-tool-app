"""The last check a message passes before it leaves — on the rendered text, not the template."""
import pytest

from app import message_guard


def _lead(**over) -> dict:
    return {"no": 1, "company_en": "Verum AV Solutions", "country": "USA",
            "city": "Houston, TX", "website": "verumav.com",
            "hook": "Saw the rental work on your site.", **over}


# ---------------------------------------------------------------- pricing

def test_a_price_never_leaves_without_allen():
    """AGENTS.md rule one: Allen owns every number. Until now that lived only in a
    prompt, and both a hand-written template and a model draft can carry a price."""
    for body in ("We can offer USD 1,200 per sqm.",
                 "Our price is $850/sqm for P2.5.",
                 "Around €900 per panel, delivered.",
                 "P2.5 at 1200 USD/sqm, 30 days lead time.",
                 "报价 8000 元/平米"):
        verdict = message_guard.check(body, _lead())
        assert verdict.blocked, body
        assert verdict.reason == "pricing"


def test_ordinary_product_talk_is_not_a_price():
    """P2.5, 200 sqm and a phone number are numbers a normal cold email carries."""
    for body in ("We deliver P1.86, P2.5 and P3.91 displays.",
                 "Saw the 200 sqm video wall on your site.",
                 "WhatsApp: +86 135-7087-1001",
                 "Completed 40 projects in 2025."):
        # step_order=1 isolates the pricing rule from the personalisation one.
        assert not message_guard.check(body, _lead(), step_order=1).blocked, body


# ---------------------------------------------------------------- personalisation

def test_a_message_with_nothing_about_this_company_is_held():
    """544 of these went out and came back with zero human replies. A cold email that
    could have been addressed to anyone is not outreach, it is postage."""
    body = ("Hi,\n\nI'd like to share some recent LED display projects we delivered.\n"
            "We have completed indoor and outdoor projects including P2.5 and P10.\n"
            "Best regards,\nAllen Ma")
    verdict = message_guard.check(body, _lead())
    assert verdict.blocked and verdict.reason == "impersonal"


def test_naming_the_company_is_enough():
    body = "Hi,\n\nVerum AV Solutions came up while I was looking at Houston AV firms."
    assert not message_guard.check(body, _lead()).blocked


def test_the_hook_we_already_collected_is_enough():
    """69% of the leads carry a hook read off their own site, and no template used it."""
    body = "Hi,\n\nSaw the rental work on your site. We supply the panels behind that kind of work."
    assert not message_guard.check(body, _lead()).blocked


def test_a_follow_up_is_not_asked_to_reintroduce_the_company():
    """Step 2 and 3 sit under the first mail's subject; repeating the hook there reads
    like a bot, so the personalisation rule applies to the opening touch only."""
    body = "Just following up on the note I sent earlier. Anything coming up?"
    assert not message_guard.check(body, _lead(), step_order=1).blocked


def test_a_lead_with_nothing_to_personalise_from_is_not_punished_for_it():
    """No hook, no city, only a domain-derived name: hold the message, but say the
    reason is missing evidence rather than a badly written template."""
    verdict = message_guard.check("Hi,\n\nWe supply LED displays.", _lead(hook=None, city=None))
    assert verdict.blocked and verdict.reason == "impersonal"
    assert "verum" in verdict.detail.lower() or "线索" in verdict.detail


# ---------------------------------------------------------------- wiring

def test_guard_is_off_for_channels_that_are_not_cold_email():
    """A WhatsApp reply inside a live conversation is not a cold opening."""
    assert not message_guard.check("Sure, sending now.", _lead(), channel="whatsapp").blocked
