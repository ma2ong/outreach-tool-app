from app import enrich


def test_extract_emails_filters_junk():
    text = "Contact info@acme.com or sales@acme.com. img@2x.png sentry@abc.io a@b.jpg"
    got = enrich.extract_emails(text)
    assert got == ["info@acme.com", "sales@acme.com"]


def test_enrich_domain_picks_best_email():
    pages = {
        "https://acme.com/contact": "reach info@acme.com",
        "https://acme.com": "home",
    }
    out = enrich.enrich_domain("acme.com", fetch=lambda url: pages.get(url, ""))
    assert out["domain"] == "acme.com"
    assert out["email"] == "info@acme.com"
    assert "info@acme.com" in out["emails"]


def test_enrich_domain_no_email():
    out = enrich.enrich_domain("none.com", fetch=lambda url: "no address here")
    assert out["email"] is None
    assert out["emails"] == []


def test_extract_phones_wa_me_first():
    text = ("Call us tel:+55-11-2115-3091 or https://wa.me/5511956635316 "
            "or +55 11 3044-4609")
    got = enrich.extract_phones(text)
    assert got[0] == "+5511956635316"
    assert "+551121153091" in got
    assert "+551130444609" in got


def test_extract_phones_whatsapp_api_link():
    text = "https://api.whatsapp.com/send?phone=5215512345678&text=hi"
    assert enrich.extract_phones(text) == ["+5215512345678"]


def test_extract_phones_dedupes_and_ignores_short():
    text = "tel:+5511956635316 wa.me/5511956635316 call 123456"
    assert enrich.extract_phones(text) == ["+5511956635316"]


def test_extract_socials_handles():
    text = ("https://www.instagram.com/ledwave/ "
            "https://instagram.com/p/Cxyz123/ "
            "https://facebook.com/ledwavesaopaulo "
            "https://www.facebook.com/sharer.php?u=x "
            "https://www.linkedin.com/company/ledwave/about")
    got = enrich.extract_socials(text)
    assert got["instagram"] == "ledwave"
    assert got["facebook"] == "ledwavesaopaulo"
    assert got["linkedin"] == "linkedin.com/company/ledwave"


def test_extract_socials_none():
    got = enrich.extract_socials("nothing social here")
    assert got == {"instagram": None, "facebook": None, "linkedin": None}


def test_enrich_domain_returns_phone_and_socials():
    pages = {
        "https://acme.com/contact": ("reach info@acme.com wa.me/5511956635316 "
                                     "instagram.com/acmeled facebook.com/acmeledpage "
                                     "linkedin.com/in/acme-founder"),
    }
    out = enrich.enrich_domain("acme.com", fetch=lambda url: pages.get(url, ""))
    assert out["phone"] == "+5511956635316"
    assert out["instagram"] == "acmeled"
    assert out["facebook"] == "acmeledpage"
    assert out["linkedin"] == "linkedin.com/in/acme-founder"


def test_enrich_domain_no_contacts_has_none_fields():
    out = enrich.enrich_domain("none.com", fetch=lambda url: "plain page")
    assert out["phone"] is None
    assert out["instagram"] is None
    assert out["facebook"] is None
    assert out["linkedin"] is None


def test_extract_emails_drops_noreply():
    got = enrich.extract_emails("noreply@acme.com no-reply@acme.com sales@acme.com donotreply@x.com")
    assert got == ["sales@acme.com"]


def test_extract_company_name_from_markdown_title():
    assert enrich.extract_company_name("# LED Factory Chile | Pantallas LED\nbody") == "LED Factory Chile"
    assert enrich.extract_company_name("Title: Acme LED - Home") == "Acme LED"
    assert enrich.extract_company_name("no heading here at all") is None


def test_enrich_domain_returns_company_guess():
    out = enrich.enrich_domain("acme.com", fetch=lambda url: "# Acme Displays – LED walls\ninfo@acme.com")
    assert out["company"] == "Acme Displays"


def test_blocked_page_raises_and_enrich_survives():
    import pytest
    from app.jina import _BLOCK_MARKERS, BlockedPage
    from app import enrich as enrich_mod

    def blocked_fetch(url):
        raise BlockedPage(url)

    # enrich treats a blocked page like an unreachable one: empty result, no crash
    info = enrich_mod.enrich_domain("blocked.com", fetch=blocked_fetch)
    assert info["email"] is None and info["icp_type"] == "unknown"


def test_page_titles_that_name_the_page_are_not_company_names():
    """The contact page is fetched first, so without this a quick-added website lands in
    the book as a company called "Contact"."""
    for title in ("# Contact", "# Contact Us", "# Inicio", "Title: Página não encontrada",
                  "# 문의", "# 404"):
        assert enrich.extract_company_name(title) is None


def test_company_name_comes_from_the_homepage_not_the_contact_page():
    pages = {
        "https://acme.com/contact": "# Contact Us\ninfo@acme.com",
        "https://acme.com": "# Acme Displays | LED walls",
    }
    out = enrich.enrich_domain("acme.com", fetch=lambda url: pages.get(url, ""))
    assert out["company"] == "Acme Displays"


def test_product_pages_are_read_when_the_contact_pass_found_no_spec():
    """Pitches live on the product page, and 6 of 8 real customer sites published none
    on the pages enrich used to read."""
    pages = {
        "https://acme.com/contact": "# Contact\ninfo@acme.com rental staging",
        "https://acme.com": "# Acme\nrental staging",
        "https://acme.com/products": "LED panel P2.5 and LED panel P4",
    }
    fetched = []

    def fetch(url):
        fetched.append(url)
        return pages.get(url, "")

    out = enrich.enrich_domain("acme.com", fetch=fetch)
    assert out["hook"] == "Saw P2.5 and P4 panels listed on your site."
    assert "https://acme.com/products" in fetched


def test_product_pages_are_skipped_when_a_spec_is_already_in_hand():
    pages = {"https://acme.com/contact": "LED panel P3.9 info@acme.com"}
    fetched = []

    def fetch(url):
        fetched.append(url)
        return pages.get(url, "")

    enrich.enrich_domain("acme.com", fetch=fetch)
    assert not [u for u in fetched if "product" in u]


def test_enrich_reports_how_many_pages_answered():
    pages = {"https://acme.com": "# Acme\ninfo@acme.com"}
    assert enrich.enrich_domain("acme.com", fetch=lambda url: pages.get(url, ""))["pages"] > 0

    def dead(url):
        raise OSError("unreachable")

    assert enrich.enrich_domain("dead.com", fetch=dead)["pages"] == 0
