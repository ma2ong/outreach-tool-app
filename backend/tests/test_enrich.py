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


def test_the_page_s_own_links_are_followed_when_no_spec_was_found():
    """Guessing paths does not work: rgbkorea.com keeps every word about itself at
    /shopinfo/company.html, a convention no list of English guesses would contain. The
    navigation shell links to it, so the link is read instead of guessed."""
    pages = {
        "https://acme.co.kr": ("# Acme\n"
                               "[About Us](https://acme.co.kr/shopinfo/company.html)\n"
                               "[Instagram](https://instagram.com/acme)"),
        "https://acme.co.kr/shopinfo/company.html": "LED panel P2.5 and LED panel P4",
    }
    fetched = []

    def fetch(url):
        fetched.append(url)
        return pages.get(url, "")

    out = enrich.enrich_domain("acme.co.kr", fetch=fetch)
    assert out["hook"] == "Saw P2.5 and P4 panels listed on your site."
    assert "https://acme.co.kr/shopinfo/company.html" in fetched


def test_korean_navigation_is_scored_by_the_same_table_as_english():
    """No per-country branch: 회사소개 scores exactly the way "about" does."""
    pages = {
        "https://hanul.co.kr": "# Hanul\n[회사소개](https://hanul.co.kr/sub/intro.html)",
        "https://hanul.co.kr/sub/intro.html": "LED 전광판 P6 패널",
    }
    out = enrich.enrich_domain("hanul.co.kr", fetch=lambda u: pages.get(u, ""))
    assert out["hook"] == "Saw P6 panels listed on your site."


def test_links_to_other_companies_are_never_followed():
    """A partner's catalogue would describe the wrong company."""
    page = ("# Acme\n[Products](https://supplier-partner.com/products)\n"
            "[Products](https://acme.com/products)")
    links = enrich._content_links(page, "acme.com", set())
    assert links == ["https://acme.com/products"]


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


def test_local_format_phone_keeps_its_local_form():
    """Regression: eidim.com's 'tel:877.773.4346' became '+8777734346' — a US toll-free
    number wearing an invented country code, which no one can dial back."""
    got = enrich.extract_phones("call us tel:877.773.4346 today")
    assert got == ["877.773.4346"]


def test_whatsapp_link_number_is_still_international():
    assert enrich.extract_phones("wa.me/5511956635316") == ["+5511956635316"]


def test_enrich_domain_reports_the_country_on_the_page():
    pages = {"https://eidim.com/contact":
             "1015 S Placentia Ave, Fullerton, CA 92831 hello@eidim.com"}
    out = enrich.enrich_domain("eidim.com", fetch=lambda url: pages.get(url, ""))
    assert out["country"] == "USA"


def test_enrich_domain_country_is_none_when_unknown():
    out = enrich.enrich_domain("mystery.com", fetch=lambda url: "we make screens")
    assert out["country"] is None
