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
    monkeypatch.delenv("NAVER_CLIENT_ID", raising=False)
    monkeypatch.delenv("NAVER_CLIENT_SECRET", raising=False)
    naver = ds.SOURCES["naver"]
    assert naver.available() is False
    assert "NAVER_CLIENT_ID" in naver.unavailable()


def test_a_configured_channel_becomes_available(monkeypatch):
    monkeypatch.setenv("NAVER_CLIENT_ID", "id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "secret")
    assert ds.SOURCES["naver"].available() is True


def test_an_unavailable_channel_is_reported_as_such_not_run(monkeypatch):
    monkeypatch.delenv("NAVER_CLIENT_ID", raising=False)
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
    monkeypatch.delenv("NAVER_CLIENT_ID", raising=False)
    monkeypatch.delenv("NAVER_CLIENT_SECRET", raising=False)
    assert ds.naver_search("LED 전광판") == []
