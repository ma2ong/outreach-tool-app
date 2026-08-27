"""Prospecting channels as declarations (docs/70).

There was exactly one route — a DuckDuckGo query written as a function — so adding a
second meant new code, tests and a deploy, and three months later there was still one.

Two rules carry the weight here: an unconfigured channel is not a broken one, and one
channel failing must not take the day's prospecting with it. Naver redesigns, Google
rate-limits and Instagram wants a fresh login, and those never happen on the same day.
"""
import pytest

from app import discovery_sources as ds


@pytest.mark.parametrize("url,expected", [
    ("https://www.verumav.com/about", True),
    ("http://ledkorea.co.kr", True),
    ("https://blog.naver.com/somebody", False),
    ("https://www.instagram.com/someone", False),
    ("https://www.linkedin.com/company/x", False),
    ("https://www.alibaba.com/showroom/led", False),
    ("", False),
])
def test_only_a_company_of_its_own_counts_as_a_lead(url, expected):
    # A hit on a platform is somebody's page on somebody else's site.
    assert ds.is_company_site(url) is expected


def test_a_channel_with_no_key_is_unavailable_not_failed(monkeypatch):
    monkeypatch.delenv("NAVER_API_KEY_ID", raising=False)
    monkeypatch.delenv("NAVER_API_KEY", raising=False)
    naver = ds.SOURCES["naver"]
    assert naver.available() is False
    assert "NAVER_API_KEY_ID" in naver.unavailable()


def test_korea_is_reachable_without_any_account(monkeypatch):
    """NAVER Cloud Platform wants Korean real-name verification, which Allen cannot do
    from Shenzhen. A channel that works today beats a better one that never opens."""
    assert ds.SOURCES["naver-web"].available() is True
    assert ds.SOURCES["naver-web"].kind == "page"


def test_the_api_route_is_optional_not_a_daily_complaint(monkeypatch):
    monkeypatch.delenv("NAVER_API_KEY_ID", raising=False)
    naver = ds.SOURCES["naver"]
    assert naver.available() is False
    assert naver.optional is True


def test_naver_page_results_drop_the_cdn_and_the_forums(monkeypatch):
    page = " ".join(f"]({u})" for u in [
        "https://ssl.pstatic.net/img.png",
        "https://www.navercorp.com/about",
        "https://cafe.daum.net/thread",
        "https://gadgetrental.kr/",
        "https://media-rental.co.kr/led",
        "https://gadgetrental.kr/again",
    ])
    monkeypatch.setattr("app.jina.fetch", lambda url, timeout=45: page)
    rows = ds.naver_page_search("LED 렌탈")
    assert [r["domain"] for r in rows] == ["gadgetrental.kr", "media-rental.co.kr"]
    assert rows[0]["country"] == "South Korea"


def test_the_local_channel_shares_the_same_keys(monkeypatch):
    # One credential pair for both Naver channels: configuring one and not the other
    # would be a state nobody can reason about.
    monkeypatch.delenv("NAVER_API_KEY_ID", raising=False)
    assert ds.SOURCES["naver-local"].available() is False


def test_a_local_listing_without_a_website_is_still_a_lead(monkeypatch):
    monkeypatch.setenv("NAVER_API_KEY_ID", "id")
    monkeypatch.setenv("NAVER_API_KEY", "key")
    monkeypatch.setattr(ds, "_naver_call", lambda path, params: {"items": [
        {"title": "<b>제일</b>미디어", "link": "https://blog.naver.com/x",
         "address": "서울특별시 강남구", "telephone": "02-555-1234"}]})
    rows = ds.naver_local("AV 렌탈 강남")
    assert rows[0]["company_en"] == "제일미디어"
    assert rows[0]["phone"] == "02-555-1234"
    assert rows[0]["city"] == "서울특별시"
    # A listing on a blog domain has no site of its own; the phone is the way in.
    assert "website" not in rows[0]


def test_a_configured_channel_becomes_available(monkeypatch):
    monkeypatch.setenv("NAVER_API_KEY_ID", "id")
    monkeypatch.setenv("NAVER_API_KEY", "secret")
    assert ds.SOURCES["naver"].available() is True


def test_an_unavailable_channel_is_reported_as_such_not_run(monkeypatch):
    monkeypatch.delenv("NAVER_API_KEY_ID", raising=False)
    out = ds.gather(["LED rental"], only=["naver"])
    assert out["candidates"] == []
    assert out["sources"][0]["status"] == "未启用"


def test_one_channel_failing_does_not_stop_the_others(monkeypatch):
    def explode(_query, _limit):
        raise RuntimeError("rate limited")

    monkeypatch.setitem(ds.SOURCES, "boom", ds.Source(
        name="boom", label="炸的", kind="page", fetch=explode))
    monkeypatch.setitem(ds.SOURCES, "fine", ds.Source(
        name="fine", label="好的", kind="page",
        fetch=lambda q, n: [{"domain": "verumav.com", "source": "fine"}]))

    out = ds.gather(["LED rental"], only=["boom", "fine"])
    assert [c["domain"] for c in out["candidates"]] == ["verumav.com"]
    states = {s["name"]: s["status"] for s in out["sources"]}
    assert states == {"boom": "失败", "fine": "ok"}


def test_the_same_company_found_twice_is_one_candidate(monkeypatch):
    monkeypatch.setitem(ds.SOURCES, "a", ds.Source(
        name="a", label="A", kind="page",
        fetch=lambda q, n: [{"domain": "verumav.com", "source": "a"}]))
    monkeypatch.setitem(ds.SOURCES, "b", ds.Source(
        name="b", label="B", kind="page",
        fetch=lambda q, n: [{"domain": "verumav.com", "source": "b"}]))
    out = ds.gather(["x"], only=["a", "b"])
    assert len(out["candidates"]) == 1


def test_every_channel_reports_what_it_found(monkeypatch):
    monkeypatch.setitem(ds.SOURCES, "a", ds.Source(
        name="a", label="A", kind="page",
        fetch=lambda q, n: [{"domain": f"{q}.com", "source": "a"}]))
    out = ds.gather(["one", "two"], only=["a"])
    assert out["sources"][0]["found"] == 2


def test_naver_returns_nothing_rather_than_calling_without_a_key(monkeypatch):
    monkeypatch.delenv("NAVER_API_KEY_ID", raising=False)
    monkeypatch.delenv("NAVER_API_KEY", raising=False)
    assert ds.naver_search("LED 전광판") == []
