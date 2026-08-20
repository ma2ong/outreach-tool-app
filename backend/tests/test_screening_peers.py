import pytest

from app.screening import is_peer_brand, reads_as_chinese_maker, screen


@pytest.mark.parametrize("domain,brand", [
    ("linsnled.com", "linsn"),            # 灵星雨, control systems
    ("doitvision.com", "doitvision"),
    ("unit-led.com", "unit-led"),
    ("chipshowledusa.com", "chipshow"),   # a US front for a Shenzhen maker
    ("absen.com.br", "absen"),            # 艾比森, Brazil branch
    ("www.unilumin.com", "unilumin"),
])
def test_a_chinese_maker_behind_a_western_domain_is_named(domain, brand):
    """None of the older signals see these: the TLD is Western and the phone is local."""
    assert is_peer_brand(domain) == brand
    result = screen({"domain": domain})
    assert result["excluded"] and brand in result["exclude_reason"]


@pytest.mark.parametrize("domain", [
    "neoti.com", "keycodemedia.com", "brightlinkav.com", "mvix.com",
    "elitemultimedia.com", "snap-install.com",
])
def test_a_real_buyer_is_not_swept_up(domain):
    assert is_peer_brand(domain) is None
    assert screen({"domain": domain})["excluded"] is False


def test_both_signals_are_required_before_calling_someone_a_factory():
    """A US integrator says 'manufacturer' about the brands it carries, and a customer
    may mention Shenzhen. Either alone is innocent."""
    assert not reads_as_chinese_maker({"business": "AV integrator and manufacturer rep"})
    assert not reads_as_chinese_maker({"business": "we buy panels from Shenzhen"})
    assert reads_as_chinese_maker({"business": "LED display manufacturer (Shenzhen-backed)"})


def test_a_shenzhen_backed_front_is_excluded_by_what_it_says(conn=None):
    result = screen({"domain": "innoleader.ca",
                     "business": "LED display manufacturer/distributor (Shenzhen-backed)"})
    assert result["excluded"] and "自称中国厂家" in result["exclude_reason"]


def test_a_us_area_code_is_not_read_as_china():
    """AVL Solutions of Greenville SC was flagged as a peer because its number was
    stored as +8642507942 — 864 is the Greenville area code, and the missing +1 made it
    read as +86. Screening must not exclude it on the strength of the rest."""
    cand = {"domain": "avlsusa.com", "phone": "+1 864-250-7942",
            "business": "Greenville SC AV company, outdoor mobile LED screen rental"}
    assert screen(cand)["excluded"] is False


def test_peer_screening_can_still_be_switched_off():
    assert screen({"domain": "absen.com.br"}, exclude_peers=False)["excluded"] is False
