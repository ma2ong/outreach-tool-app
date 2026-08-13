from app import personalize
from app.brief import build

# Shaped like the real pages this was verified against: the pitch is always printed next
# to the product it is a spec of ("painel de LED P3"), never on its own.
RENTAL_PAGE = """
# Sunrise Visual
We are an LED rental and staging company working on concert and festival production.
Our inventory: LED panel P3.9 and LED panel P2.6 for touring work.
"""


def test_brief_quotes_the_site_and_names_its_pitches():
    out = build(RENTAL_PAGE, icp={"icp_type": "rental", "hits": ["rental", "staging", "concert"]})
    assert out["brief"] == \
        'The site mentions "rental", "staging" and "concert", and lists P2.6 and P3.9 panels.'
    # The line a rep would be embarrassed to repeat on a call never gets written.
    for word in ("leading", "seasoned", "passionate", "well-known", "premier"):
        assert word not in out["brief"].lower()


def test_the_brief_never_restates_the_company_name_or_category():
    """An early draft opened with "<name> is <category>" and, on a /contact page whose
    title was "Contact", wrote "Contact is a signage company" onto the record."""
    out = build(RENTAL_PAGE, icp={"icp_type": "rental", "hits": ["rental", "staging"]})
    assert out["brief"].startswith("The site ")
    assert "rental company" not in out["brief"]


def test_hook_is_a_whole_sentence_built_from_pitches_only():
    out = build(RENTAL_PAGE, icp={"icp_type": "rental", "hits": ["rental", "staging"]})
    assert out["hook"] == "Saw P2.6 and P3.9 panels listed on your site."


def test_a_site_with_no_pitches_still_gets_a_hook_from_what_it_does():
    page = "Pantallas LED: signage, digital sign, publicidad exterior"
    out = build(page, icp={"icp_type": "signage",
                           "hits": ["signage", "digital sign", "publicidad exterior"]})
    assert out["brief"] == \
        'The site mentions "signage", "digital sign" (digital signage) and ' \
        '"publicidad exterior" (outdoor advertising).'
    assert out["hook"] == "Saw the signage work on your site."


def test_a_full_product_line_reads_as_a_range():
    page = "MODELOS: Painel de LED P1, Painel de LED P2, Painel de LED P5, Painel de LED P10"
    out = build(page, icp={"icp_type": "rental", "hits": ["rental"]})
    assert out["hook"] == "Saw P1–P10 panels listed on your site."


def test_a_pitch_only_counts_next_to_an_led_context_word():
    """A bare "P3" is a heading or a product code on most of the web."""
    assert build("Chapter P3 of the manual, see P4 for details.",
                 icp={"icp_type": "rental", "hits": ["rental"]})["brief"] == ""
    anchored = build("pantalla-electronica-led-para-exterior-p8-smd",
                     icp={"icp_type": "reseller", "hits": ["distributor", "wholesale"]})
    assert "P8" in anchored["hook"]


def test_pitches_outside_a_real_product_range_are_dropped():
    out = build("LED panel P0.9, LED page P50, LED ref P99",
                icp={"icp_type": "reseller", "hits": ["distributor", "wholesale"]})
    assert "P0.9" in out["brief"] and "P50" not in out["brief"]


def test_category_alone_writes_no_brief():
    """target_fit already shows the category — a brief that only repeats it costs
    attention and returns none, so the floor is one published spec or two site facts."""
    out = build("# Generic Co\nWe do signage.", icp={"icp_type": "signage", "hits": ["signage"]})
    assert out["brief"] == ""


def test_korean_matches_are_glossed_not_dropped():
    """Korea is a primary market. Dropping its keywords for reading nicely in English
    would blank out the brief and the hook for every Korean site."""
    page = "LED 전광판 대리점"
    out = build(page, icp={"icp_type": "reseller", "hits": ["전광판", "대리점"]})
    assert out["brief"] == 'The site mentions "전광판" (LED signage) and "대리점" (dealership).'
    # The message goes out in English, so the hook uses the gloss alone.
    assert out["hook"] == "Saw the LED signage work on your site."


def test_a_single_keyword_still_earns_a_hook_but_not_a_brief():
    """The two have different readers: repeating the ICP grade is noise on Allen's
    screen and news on the customer's."""
    out = build("LED 전광판", icp={"icp_type": "signage", "hits": ["전광판"]})
    assert out["brief"] == ""
    assert out["hook"] == "Saw the LED signage work on your site."


def test_a_self_referring_term_is_readable_but_never_sent():
    out = build("Our church needs a wall", icp={"icp_type": "end-user",
                                                "hits": ["our church", "house of worship"]})
    assert out["brief"] == 'The site mentions "our church" and "house of worship".'
    assert out["hook"] == ""


def test_render_drops_an_empty_hook_without_leaving_a_gap():
    lead = {"company_en": "Acme", "contact_name": "", "hook": ""}
    assert personalize.render("Hi {contact}, {hook} We build LED panels.", lead) == \
        "Hi, We build LED panels."


def test_render_inserts_the_hook_when_there_is_one():
    lead = {"company_en": "Acme", "contact_name": "Carlos Ruiz",
            "hook": "Saw P3.9 panels listed on your site."}
    assert personalize.render("Hi {contact}, {hook} We build LED panels.", lead) == \
        "Hi Carlos, Saw P3.9 panels listed on your site. We build LED panels."


def test_the_brief_is_not_a_sendable_token():
    """It is written in the third person for Allen; a template that sent it would quote
    the customer's own website back at them."""
    lead = {"company_en": "Acme", "contact_name": "Carlos",
            "brief": 'The site mentions "rental".'}
    assert personalize.render("{brief}", lead) == "{brief}"


def test_render_leaves_deliberate_spacing_alone_when_nothing_is_dropped():
    lead = {"company_en": "Acme", "contact_name": "Carlos", "hook": "Saw your site."}
    assert personalize.render("{contact}:   two blanks", lead) == "Carlos:   two blanks"


def test_two_spellings_of_the_same_word_are_quoted_once():
    """app.icp carries "locação" and "locacao" so a Brazilian site matches either way;
    a page with both was producing 'mentions "locação" (rental) and "locacao" (rental)'."""
    out = build("locação e locacao de paineis para eventos",
                icp={"icp_type": "rental", "hits": ["locação", "locacao", "eventos"]})
    assert out["brief"] == 'The site mentions "locação" (rental) and "eventos" (events).'


def test_every_icp_keyword_has_an_english_gloss():
    """Adding a keyword without a gloss silently keeps it out of the hook — which is how
    Korean integrators stayed invisible while the category matched."""
    from app.brief import _TERM
    from app.icp import _CATEGORIES

    missing = [k for _, keywords in _CATEGORIES.values() for k in keywords if k not in _TERM]
    assert missing == [], f"缺释义：{missing}"
