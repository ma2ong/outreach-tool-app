"""Rendered-message guard unit tests. No network and no production DB."""
from app import message_guard


def _lead(**over) -> dict:
    return {
        "no": 1,
        "company_en": "Verum AV Solutions",
        "country": "USA",
        "city": "Houston, TX",
        "website": "verumav.com",
        "hook": "Saw the rental work on your site.",
        **over,
    }


def test_price_never_leaves_cold_email():
    for body in (
        "We can offer USD 1,200 per sqm.",
        "Our price is $850/sqm for P2.5.",
        "Around €900 per panel.",
        "报价 8000 元/平米",
    ):
        verdict = message_guard.check(body, _lead())
        assert verdict.blocked, body
        assert verdict.reason == "pricing"


def test_ordinary_product_numbers_are_not_prices():
    for body in (
        "We deliver P1.86, P2.5 and P3.91 displays.",
        "Saw the 200 sqm video wall on your site.",
        "WhatsApp: +86 135-7087-1001",
        "Completed 40 projects in 2025.",
    ):
        assert not message_guard.check(body, _lead(), step_order=1).blocked, body


def test_generic_first_touch_is_held():
    body = "Hi,\n\nWe manufacture indoor and outdoor LED displays. Let me know if you need anything."
    verdict = message_guard.check(body, _lead())
    assert verdict.blocked
    assert verdict.reason == "impersonal"


def test_company_name_or_domain_makes_opening_specific():
    assert not message_guard.check(
        "Hi,\n\nI came across Verum while looking at AV integrators in Houston.", _lead()
    ).blocked
    assert not message_guard.check(
        "Hi,\n\nI was reviewing verumav and wanted to share a relevant LED reference.", _lead()
    ).blocked


def test_sourced_hook_term_makes_opening_specific():
    body = "Hi,\n\nSaw the rental work on your site. We supply LED panels to integrators."
    assert not message_guard.check(body, _lead()).blocked


def test_follow_up_does_not_need_to_repeat_personalization():
    body = "Just following up on the note I sent earlier. Anything coming up?"
    assert not message_guard.check(body, _lead(), step_order=1).blocked


def test_non_email_channel_is_not_subject_to_cold_opening_rule():
    assert not message_guard.check(
        "Sure, sending that over now.", _lead(), channel="whatsapp"
    ).blocked
