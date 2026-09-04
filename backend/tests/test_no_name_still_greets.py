# -*- coding: utf-8 -*-
"""不知道对方叫什么，信照发（Allen 09-04）。

> 没有人名就统一用 Hi（针对韩国以外的国籍），或者 안녕하세요（只针对韩国）。

这条今天已经成立。钉成测试是因为它是「什么都没发生」型的保证 —— 坏掉的时候不会报错，
只会有一封信悄悄没发出去，或者一句「Hi ,」发出去。docs/77 和 docs/91 都是这个形状。
"""
from app import message_guard, personalize
from app.backfill_hooks import GENERIC_HOOK

EN = "Hi {contact},\n\n{hook}\n\nThis is Allen from Shenzhen Maxcolor.\n\nAllen Ma"
KO = "안녕하세요, {contact}님.\n\n{hook_ko}\n\n저는 심천의 LED 제조업체입니다.\n\nAllen Ma"


def _first_line(tpl, lead):
    return personalize.render(tpl, lead).splitlines()[0]


def test_no_name_outside_korea_is_just_hi():
    lead = {"no": 1, "company_en": "Acme", "country": "USA", "hook": GENERIC_HOOK}
    assert _first_line(EN, lead) == "Hi,"
    # 「Hi ,」和「Hi there,」都不行：前者是没填上的模板，后者是群发的签名
    assert _first_line(EN, lead) != "Hi ,"
    assert "there" not in _first_line(EN, lead)


def test_no_title_in_korea_is_just_the_greeting():
    lead = {"no": 1, "company_en": "A", "country": "South Korea", "contact_name": "윤주영"}
    assert _first_line(KO, lead) == "안녕하세요."


def test_a_letter_is_never_held_just_because_nobody_is_named():
    """守卫拦的是「这封信没说他们任何事」，不是「不知道他叫什么」。"""
    for country, tpl in (("USA", EN), ("South Korea", KO)):
        lead = {"no": 1, "company_en": "Acme", "country": country, "city": "Austin",
                "hook": GENERIC_HOOK}
        body = personalize.render(tpl, lead)
        verdict = message_guard.check(body, lead, subject="S", step_order=0)
        assert not verdict.blocked, f"{country}: {verdict.reason} {verdict.detail}"


def test_an_empty_hook_becomes_the_generic_one_instead_of_a_hold(conn):
    """Allen 09-04：「空 hook 也不要拦，直接用通用 hook。」

    原来空开场白会让首封被拦成 impersonal —— 一封信因为我们没查到东西而不发，代价落在
    客户开发上，而 docs/85 早就备好了那句人人都能用的话。现在渲染时就补上，
    「没有 hook」和「hook 是通用句」在信里是同一封信。
    """
    from app.backfill_hooks import GENERIC_HOOK, GENERIC_HOOK_KO

    conn.execute("UPDATE leads SET hook='' WHERE no=1")
    conn.commit()
    lead = dict(conn.execute("SELECT * FROM leads WHERE no=1").fetchone())
    lead["country"] = "USA"
    body = personalize.render(EN, lead)
    assert GENERIC_HOOK in body
    assert not message_guard.check(body, lead, subject="S", step_order=0).blocked

    lead["country"] = "South Korea"
    assert GENERIC_HOOK_KO in personalize.render(KO, lead)
