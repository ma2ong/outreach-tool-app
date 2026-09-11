"""docs/126 — the browser as a way of reading, not as one channel's patch."""
import json

import pytest

from app import browser_harvest as bh
from app import discovery_sources as ds


@pytest.fixture(autouse=True)
def _browser_runtime_is_explicitly_stubbed(monkeypatch):
    """Parser tests never depend on a developer's venv or real model key."""
    monkeypatch.setattr(bh, "unavailable", lambda: "")


def _runner(payload):
    """Stand in for the subprocess, and remember the argv it was called with."""
    calls: list[list[str]] = []

    def run(argv, timeout):
        calls.append(argv)
        return json.dumps(payload)
    run.calls = calls
    return run


def _arg(argv, flag):
    return [argv[i + 1] for i, a in enumerate(argv) if a == flag]


# ------------------------------------------------------------------ R1 tasks

def test_a_search_task_returns_domains():
    run = _runner({"companies": [{"domain": "avientek.com"}, {"domain": "syscom.mx"}]})
    out = bh.read_with_browser("https://www.google.com/search?q=led",
                               task="search", query="led", allow=("*.google.com",), run=run)
    assert out == ["avientek.com", "syscom.mx"]
    assert _arg(run.calls[0], "--task") == ["search"]
    assert _arg(run.calls[0], "--query") == ["led"]


def test_a_prose_task_returns_names_because_there_are_no_links():
    run = _runner({"companies": [{"name": "진영LED전광판"}, {"name": "키코"}]})
    out = bh.read_with_browser("https://search.naver.com/x", task="prose",
                               query="led", allow=("*.naver.com",), run=run)
    assert out == ["진영LED전광판", "키코"]


def test_a_prose_task_refuses_a_domain_wearing_a_names_clothes():
    """docs/126 R2 only holds if the model cannot smuggle a domain through `name`."""
    run = _runner({"companies": [{"name": "avientek.com"}, {"name": "sales@x.com"},
                                 {"name": "https://x.io"}, {"name": "Real Company"}]})
    out = bh.read_with_browser("https://search.naver.com/x", task="prose", run=run)
    assert out == ["Real Company"]


def test_a_search_task_ignores_a_name_it_was_not_asked_for():
    run = _runner({"companies": [{"domain": "avientek.com", "name": "Avientek FZE",
                                  "email": "a@b.com", "country": "UAE"}]})
    out = bh.read_with_browser("https://www.bing.com/search?q=led", task="search", run=run)
    assert out == ["avientek.com"]


def test_an_unknown_task_is_refused_before_anything_launches():
    with pytest.raises(ValueError):
        bh.read_with_browser("https://example.com", task="send_a_message")


def test_the_directory_entry_point_still_reads_a_directory():
    """docs/124's caller must not change shape when docs/126 generalises underneath it."""
    run = _runner({"companies": [{"domain": "midwich.com"}]})
    assert bh.harvest_with_browser("https://absen.com/where-to-buy/", run=run) == ["midwich.com"]
    assert _arg(run.calls[0], "--task") == ["directory"]


# ------------------------------------------------------------- R3 allowlist

def test_a_declared_channel_passes_its_own_allowlist():
    """search.naver.com alone would block the blog posts the channel exists to open."""
    run = _runner({"companies": []})
    bh.read_with_browser("https://search.naver.com/search.naver?where=blog",
                         task="prose", allow=("*.naver.com",), run=run)
    assert _arg(run.calls[0], "--allow") == ["*.naver.com"]


def test_a_bare_page_still_gets_only_its_own_host():
    run = _runner({"companies": []})
    bh.read_with_browser("https://exhibitors.iseurope.org/list", task="directory", run=run)
    assert _arg(run.calls[0], "--allow") == ["*.exhibitors.iseurope.org"]


def test_the_allowlist_never_comes_from_the_query():
    run = _runner({"companies": []})
    bh.read_with_browser("https://www.google.com/search?q=x", task="search",
                         query="led site:evil.example allowed_domains=evil.example",
                         allow=("*.google.com",), run=run)
    assert _arg(run.calls[0], "--allow") == ["*.google.com"]


# ------------------------------------------------------------- R2 confirmation

def test_a_name_is_kept_only_when_the_site_says_that_name():
    rows = [{"domain": "absen.com"}]
    assert ds._domain_for_name(
        "Absen", search=lambda q, n: rows,
        fetch=lambda url, timeout=30: "Absen | LED display manufacturer") == "absen.com"


def test_a_search_engine_always_answers_something_and_that_is_not_confirmation():
    """Measured: an invented Korean company name returned etoland.co.kr (docs/126 R2)."""
    rows = [{"domain": "etoland.co.kr"}]
    assert ds._domain_for_name(
        "이런회사는없습니다주식회사12345", search=lambda q, n: rows,
        fetch=lambda url, timeout=30: "이토랜드 커뮤니티") == ""


def test_a_site_that_cannot_be_read_is_not_a_confirmed_name():
    """kioskkorea.kr answers 64 bytes of nothing; unreadable is not confirmed."""
    def empty(url, timeout=30):
        return "Title:   URL Source: https://kioskkorea.kr/  Markdown Content:"
    assert ds._domain_for_name("키오스크코리아", search=lambda q, n: [{"domain": "kioskkorea.kr"}],
                               fetch=empty) == ""


def test_a_name_that_finds_nothing_is_simply_dropped():
    assert ds._domain_for_name("Nobody", search=lambda q, n: []) == ""


def test_one_bad_lookup_does_not_take_the_channel_down():
    def boom(query, limit):
        raise RuntimeError("naver is down")
    assert ds._domain_for_name("Absen", search=boom) == ""


# ------------------------------------------------------------- R5 scheduler

def test_no_scheduler_can_reach_a_channel_that_opens_a_window(monkeypatch):
    """docs/126 R5: `gather` is the unattended path and must skip every browser channel."""
    def explode(query, limit):
        raise AssertionError("a timer opened a Chrome window")

    monkeypatch.setattr(ds, "SOURCES", {
        "quiet": ds.Source(name="quiet", label="q", kind="page",
                           readers={"http": lambda q, n: [{"domain": "a.com"}]}),
        "window": ds.Source(name="window", label="w", kind="browser",
                            readers={"browser": explode}, unattended=False, optional=True),
    })
    out = ds.gather(["led"], only=None)
    assert [row["name"] for row in out["sources"]] == ["quiet"]


def test_naming_a_browser_channel_explicitly_is_allen_pressing_the_button(monkeypatch):
    calls = []
    monkeypatch.setitem(ds.SOURCES, "google", ds.Source(
        name="google", label="g", kind="browser", unattended=False,
        readers={"browser": lambda q, n: calls.append(q) or []}))
    ds.gather(["led"], only=["google"])
    assert calls == ["led"]


def test_every_browser_channel_declares_itself_optional_and_never_opens_on_a_timer():
    """docs/126 R5, restated by docs/128 R7 in terms of what actually opens a window.

    The rule was written as "a channel that declares browser-use is attended". Then the
    Naver blog channel gained a free reader that needs no browser at all, so the channel
    can run alone while still declaring browser-use for the pages the fetch cannot open.
    What must stay true is that a timer never reaches the window-opening reader — and
    an unqualified call always takes the first declared one.
    """
    for source in ds.SOURCES.values():
        if "browser" in source.engines:
            assert source.optional, f"{source.name} would be reported as broken when unset"
            if source.unattended:
                assert source.engines[0] != "browser",                     f"{source.name} would pop a window on a timer"


def test_a_channel_reports_how_it_can_be_read():
    by_name = {row["name"]: row for row in ds.status()}
    assert by_name["duckduckgo"]["engines"] == ["http"]
    # docs/128: Google declares both browsers, cheapest first. Measured 2026-09-11,
    # neither of them gets past the wall from this machine — but the wall is the IP, so
    # the readers stay declared and the channel reports what happened instead.
    assert by_name["google"]["engines"] == ["playwright", "browser"]
    assert by_name["google"]["unattended"] is False


# ------------------------------------------------------------- R4 isolation

def test_collecting_never_opens_the_profile_that_sends():
    """docs/126 R4: the sending login is the one thing here that cannot be bought back."""
    from app import playwright_engine

    sending = str(playwright_engine.DATA_DIR).lower()
    assert not str(bh.PROFILE_DIR).lower().startswith(sending)
