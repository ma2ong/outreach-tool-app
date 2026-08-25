"""Who this system says it is when it talks to a customer.

maxcolorvisual.com is the company Allen sells as. mcvisualled.com is where this tool is
hosted, and a supplier that cannot keep its own name straight is not one anyone places a
purchase order with.
"""
from app import identity, quote, seeds
from app.channels import email_adapter


def _customer_facing() -> dict[str, str]:
    return {
        "英语签名": seeds.SIGNOFF,
        "韩语签名": seeds.KO_SIGNOFF,
        "报价联系行": quote._CONTACT,
        "报价抬头": f"{identity.BRAND} {identity.COMPANY}",
        "发件地址": email_adapter.FALLBACK_SENDER,
        **{f"邮件模板 {name}": body for name, _lang, _subj, body in seeds.EMAIL_TEMPLATES},
    }


def test_nothing_a_customer_reads_mentions_the_hosting_domain():
    for where, text in _customer_facing().items():
        assert "mcvisualled" not in text.lower(), where
        assert "mcvisual" not in text.lower().replace("maxcolorvisual", ""), where


def test_no_personal_gmail_goes_out_under_the_company_name():
    for where, text in _customer_facing().items():
        assert "gmail.com" not in text.lower(), where


def test_the_sender_address_is_the_company_one():
    assert identity.SENDER_EMAIL == "allen@maxcolorvisual.com"
    assert email_adapter.FALLBACK_SENDER == identity.SENDER_EMAIL


def test_both_sign_offs_carry_the_company_and_the_address():
    for signoff in (seeds.SIGNOFF, seeds.KO_SIGNOFF):
        assert identity.COMPANY in signoff
        assert identity.SENDER_EMAIL in signoff
