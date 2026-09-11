from app import seed_sequences, social_queue
from app.personalize import greeting, hook_ko, natural_hook, render


def test_korean_customer_uses_verified_title_and_never_name():
    lead = {
        "company_en": "Han AV",
        "country": "South Korea",
        "contact_name": "김민수",
        "title": "부장",
    }
    assert greeting(lead) == "안녕하세요, 부장님."
    assert "김민수" not in render("{greeting}", lead)


def test_korean_customer_without_known_title_gets_plain_hello_even_with_name():
    lead = {
        "company_en": "Han AV",
        "country": "South Korea",
        "contact_name": "김민수",
        "title": "International Sales",
    }
    assert greeting(lead) == "안녕하세요."
    assert render("{greeting}", lead) == "안녕하세요."


def test_non_korean_customer_uses_only_a_verified_first_name():
    assert greeting({"country": "USA", "contact_name": "John Smith"}) == "Hi John,"
    assert greeting({"country": "USA", "contact_name": "Sales Team"}) == "Hi,"
    assert greeting({"country": "Germany", "contact_name": ""}) == "Hi,"


def test_email_sequences_delegate_the_whole_greeting_to_personalization():
    for opener in (seed_sequences.EN_OPENER, seed_sequences.KO_OPENER):
        for _subject, body in opener.values():
            assert body.startswith("{greeting}\n\n")
            assert "Hi {contact}" not in body
            assert "{contact}님" not in body

    for korean in (False, True):
        for segment in seed_sequences.SEGMENTS:
            for _order, _offset, _subject, body in seed_sequences.steps_for(segment, korean):
                assert body.startswith("{greeting}\n\n")


def test_legacy_generic_hook_is_naturalized_at_send_time():
    lead = {"hook": "Saw that your company works with LED displays."}
    assert natural_hook(lead) == (
        "I came across your company and noticed you work with LED displays."
    )


def test_legacy_category_hooks_are_naturalized_without_changing_the_fact():
    assert natural_hook({"hook": "Saw the rental work on your site."}) == (
        "I was looking through your website and noticed your rental work."
    )
    assert natural_hook({"hook": "Saw the AV integration work you do around Miami."}) == (
        "I came across your AV integration work around Miami."
    )
    assert natural_hook({"hook": "Saw P2.6 and P3.9 panels listed on your site."}) == (
        "I noticed P2.6 and P3.9 panels on your website."
    )


def test_verified_old_saw_hook_keeps_its_fact_but_loses_the_canned_opener():
    lead = {"hook": "Saw the scoreboard you installed at Estadio Nacional."}
    assert natural_hook(lead) == "I noticed the scoreboard you installed at Estadio Nacional."


def test_old_korean_observation_becomes_a_reason_for_contact():
    lead = {"hook_ko": "잠실 실내체육관 메인 스크린 시공 사례를 봤습니다."}
    out = hook_ko(lead)
    assert out == "잠실 실내체육관 메인 스크린 시공 사례를 보고 연락드렸습니다."


def test_social_dm_uses_the_same_country_aware_greeting():
    korean = {
        "no": 4,
        "company_en": "Han AV",
        "country": "South Korea",
        "contact_name": "김민수",
        "title": "부장",
        "hook": "Saw the rental work on your site.",
        "tags": "Rental",
    }
    body = social_queue._compose(korean)
    assert body.startswith("안녕하세요, 부장님. ")
    assert "김민수" not in body
    assert "Saw the" not in body

    unknown_title = dict(korean, title="International Sales")
    assert social_queue._compose(unknown_title).startswith("안녕하세요. ")

    american = dict(korean, country="USA", contact_name="John Smith", title="")
    assert social_queue._compose(american).startswith("Hi John, ")
