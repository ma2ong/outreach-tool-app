from app import enrich


def test_double_zero_international_prefix_normalizes_to_plus():
    assert enrich.extract_phones("Call tel:0044 20 7123 4567") == ["+442071234567"]


def test_explicit_plus_and_double_zero_dedupe_to_same_number():
    text = "tel:0044 20 7123 4567 or +44 20 7123 4567"
    assert enrich.extract_phones(text) == ["+442071234567"]


def test_product_or_news_country_does_not_relabel_company_identity():
    pages = {
        "https://acme.com/contact": (
            "# Contact Acme AV\n"
            "101 Main St, Fullerton, CA 92831\n"
            "info@acme.com\n"
            "[Products](https://acme.com/products)\n"
            "[News](https://acme.com/news)"
        ),
        "https://acme.com/contact-us": "",
        "https://acme.com": "# Acme AV",
        "https://acme.com/products": (
            "Case study: Shenzhen, China factory installation. "
            "China China China LED display project."
        ),
        "https://acme.com/news": "New distributor project in China.",
    }

    out = enrich.enrich_domain("acme.com", fetch=lambda url: pages.get(url, ""))

    assert out["country"] == "USA"
    # Later pages are still useful for ICP/signals; they simply cannot rewrite identity.
    assert out["pages"] >= 4
