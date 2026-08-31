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


def test_an_empty_fit_line_does_not_leave_a_comma_holding_its_place():
    """"…ourselves, {fit}." with no customer type used to render "…ourselves,."."""
    from app.personalize import render
    lead = {"company_en": "Verum AV", "tags": "", "hook": "Saw the rental work."}
    out = render("This is Allen from Shenzhen Maxcolor — we build the panels "
                 "ourselves, {fit}.", lead)
    assert ",." not in out and ", ." not in out
    assert out.endswith("ourselves.")


def test_a_known_type_still_gets_its_line():
    from app.personalize import render
    lead = {"company_en": "Verum AV", "tags": "租赁商", "hook": ""}
    out = render("we build the panels ourselves, {fit}.", lead)
    assert len(out) > len("we build the panels ourselves.")


# --- docs/82 R11: the hook may not contradict the segment ----------------------------

def test_a_rental_hook_is_dropped_from_an_install_letter():
    """Allen: 都固定安装版了还说 Saw the rental and touring work…？是不是明显有错的。

    23 companies are tagged 工程商 by hand while their site talks about rental. Neither
    source is overruled — his tag is a judgement, the hook is evidence — the hook is
    just left out, and the letter closes the gap the way it does for any company that
    never had one.
    """
    from app.personalize import render
    lead = {"company_en": "Vu Volumes", "tags": "工程商",
            "hook": "Saw the rental and touring work you do around Tampa."}
    out = render("Hi,\n\n{hook}\n\nFor fixed work we run P2-P3 indoor.", lead)
    assert "rental" not in out
    assert "For fixed work" in out


def test_a_matching_hook_survives():
    from app.personalize import render
    lead = {"company_en": "Vu Volumes", "tags": "工程商",
            "hook": "Saw the installation work you do around Tampa."}
    assert "installation" in render("{hook}", lead)


def test_an_untyped_company_keeps_whatever_hook_it_has():
    """`general` exists because we do not know what they do — nothing to contradict."""
    from app.personalize import render
    lead = {"company_en": "Vu Volumes", "tags": "",
            "hook": "Saw the rental work on your site."}
    assert "rental" in render("{hook}", lead)
