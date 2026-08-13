from app.personalize import render

LEAD = {"company_en": "Alpha AV", "contact_name": "John Smith",
        "country": "USA", "city": "Miami"}


def test_all_tokens():
    out = render("Hi {contact} of {name} in {city}, {country}", LEAD)
    assert out == "Hi John of Alpha AV in Miami, USA"


def test_company_alias():
    assert render("{company}", LEAD) == "Alpha AV"


def test_a_missing_contact_leaves_a_clean_greeting():
    """"Hi there," announced a mass send on every lead with no contact name, which is
    most of them. Dropping the token pulls the comma back to the greeting instead."""
    assert render("Hi {contact},", {"company_en": "X"}) == "Hi,"
    assert render("Hi {contact},", {"company_en": "X", "contact_name": "  "}) == "Hi,"
    assert render("Hi {contact},", {"company_en": "X", "contact_name": "Dave Miller"}) == "Hi Dave,"


def test_missing_fields_render_empty():
    assert render("{country}{city}", {"company_en": "X"}) == ""


def test_unknown_token_left_intact():
    # A stray {price} in a template must never crash the send (old .format KeyError bug)
    assert render("Deal {price} for {name}", LEAD) == "Deal {price} for Alpha AV"


def test_none_and_empty_text():
    assert render("", LEAD) == ""
    assert render(None, LEAD) == ""
