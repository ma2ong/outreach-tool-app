from app import screening


def test_china_phone_flags_peer():
    r = screening.screen({"domain": "gldled.com", "phone": "+8613809866355"})
    assert r["country"] == "China" and r["excluded"]
    assert "同行" in r["exclude_reason"]


def test_china_phone_with_00_prefix():
    # real data had +008675523570137 (enbon.com)
    r = screening.screen({"domain": "enbon.com", "phone": "+008675523570137"})
    assert r["country"] == "China" and r["excluded"]


def test_cn_tld_flags_peer_without_phone():
    assert screening.screen({"domain": "szled.cn"})["country"] == "China"


def test_chinese_email_domain_flags_peer():
    r = screening.screen({"domain": "some-host.com", "email": "sales@sz-led.cn"})
    assert r["country"] == "China" and r["excluded"]


def test_directory_site_excluded():
    for host in ("alibaba.com", "justdial.com", "kompass.com", "aeroleads.com", "korea.tradekey.com"):
        r = screening.screen({"domain": host})
        assert r["excluded"], host
        assert r["exclude_reason"] == "B2B 目录站/平台"


def test_real_buyer_not_excluded():
    r = screening.screen({"domain": "arasystem.kr", "phone": "+827048950794"})
    assert r["country"] == "South Korea" and not r["excluded"]


def test_custom_exclude_country():
    cand = {"domain": "ledindia.in", "phone": "+919876543210"}
    assert screening.screen(cand)["excluded"] is False  # not excluded by default
    r = screening.screen(cand, exclude_countries=["India", "Pakistan"])
    assert r["excluded"] and r["exclude_reason"] == "排除国家（India）"


def test_peer_filter_can_be_turned_off():
    r = screening.screen({"domain": "gldled.com", "phone": "+8613809866355"}, exclude_peers=False)
    assert r["country"] == "China" and not r["excluded"]


def test_unknown_country_never_excluded():
    r = screening.screen({"domain": "mystery.io"}, exclude_countries=["India"])
    assert r["country"] is None and not r["excluded"]


def test_local_format_us_numbers_are_not_china():
    """Regression: '(866) 738-3580' (US toll-free) and '865-...' (Tennessee) must not
    read as +86 China — that would screen out real US customers."""
    for local in ("(866) 738-3580", "866-335-4723", "865-210-8501", "1-800-555-0100"):
        assert screening.detect_country({"phone": local}) is None, local
        assert not screening.screen({"domain": "atd-av.com", "phone": local})["excluded"], local


def test_phone_code_not_confused_with_longer_codes():
    assert screening.detect_country({"phone": "+971529357710"}) == "UAE"
    assert screening.detect_country({"phone": "+8613427921400"}) == "China"


EIDIM_FOOTER = """
EIDIM GROUP
877.773.4346
1015 S Placentia Ave, Fullerton, CA 92831
hello@eidim.com
"""


def test_us_address_is_read_from_the_page():
    """Regression: eidim.com is a Fullerton, CA integrator that the book filed under
    South Korea, because nothing ever looked at the address on its own contact page."""
    assert screening.country_from_text(EIDIM_FOOTER) == "USA"
    assert screening.detect_country(
        {"domain": "eidim.com", "text": EIDIM_FOOTER}) == "USA"


def test_canadian_postcode_is_not_usa():
    text = "Suite 400, 200 Front St W, Toronto, ON M5V 3L9"
    assert screening.country_from_text(text) == "Canada"


def test_plus_one_alone_decides_nothing():
    """'1' covers two countries. Writing either one is a guess, and 'USA/Canada' is
    not a country the target-market check or the dashboard can use."""
    assert screening.detect_country({"phone": "+16162021473"}) is None
    assert screening.detect_country({"phone": "+16162021473",
                                     "domain": "example.ca"}) == "Canada"


def test_chinese_phone_still_beats_a_us_office_address():
    """A Shenzhen factory listing a US branch address must stay screened out."""
    cand = {"domain": "szledfactory.com", "phone": "+8613809866355",
            "text": "US office: 100 Main St, Irvine, CA 92618"}
    assert screening.detect_country(cand) == "China"
    assert screening.screen(cand)["excluded"]


def test_country_named_on_the_page():
    assert screening.country_from_text("Seoul, Republic of Korea") == "South Korea"
    assert screening.country_from_text("Av. Paulista, São Paulo, Brasil") == "Brazil"
    assert screening.country_from_text("no address anywhere") is None


def test_us_place_names_are_not_countries():
    """Regression: 'Indiana' read as India, 'New Mexico' as Mexico, 'Chilean' as Chile —
    19 leads in the book carried a country picked up from a word inside another word."""
    assert screening.country_from_text("Serving Indianapolis, Indiana since 1998") is None
    assert screening.country_from_text("Albuquerque, New Mexico") is None
    assert screening.country_from_text("our Chilean-born founder") is None
    assert screening.country_from_text("Bloomington, IN 47401") == "USA"


def test_dot_co_is_only_colombian_as_com_co():
    """Regression: pureav.co and visualizeproductions.co are US companies on a short
    domain; ledwave.com.co is the form a Colombian company actually registers."""
    assert screening.detect_country({"domain": "pureav.co"}) is None
    assert screening.detect_country({"domain": "ledwave.com.co"}) == "Colombia"


# --- a peer that arrived with no website at all -----------------------------------

def test_a_peer_is_recognised_by_its_name_when_it_has_no_site():
    """Long Run LED USA walked into the book because it had only an Instagram handle,
    and the brand check only ever looked at the domain — so there was nothing to look
    at. A company announces itself in its name too."""
    assert screening.is_peer_brand(None, "Long Run LED USA") == "longrun"


def test_a_peer_is_recognised_by_its_social_handle():
    assert screening.is_peer_brand(None, None, ("longrunled_usa",)) == "longrun"


def test_the_screen_stops_that_company_at_the_door():
    verdict = screening.screen({"company_en": "Long Run LED USA",
                                "instagram": "longrunled_usa", "country": "USA"})
    assert verdict["excluded"] is True
    assert "longrun" in verdict["exclude_reason"]


def test_a_real_customer_with_a_handle_is_not_mistaken_for_one():
    verdict = screening.screen({"company_en": "Verum AV", "domain": "verumav.com",
                                "instagram": "verumav", "country": "USA"})
    assert verdict["excluded"] is False
