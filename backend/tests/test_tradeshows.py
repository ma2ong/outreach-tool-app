"""Sourcing leads from a trade-show exhibitor directory (docs/57).

The value of this source is one sentence — "看到你们在 InfoComm 2026 的展位" — and the
sentence is only worth anything while it is true. These tests guard the three ways it
goes false: the wrong year, an invented booth number, and a company that was never on
the list.
"""
import datetime as dt

import pytest

from app import tradeshows


def test_the_year_comes_from_the_page_not_from_today():
    assert tradeshows.year_from("https://infocomm.org/2023/exhibitors") == 2023


def test_the_newest_year_on_the_page_wins():
    # Directory pages link their own archives; the page is about its latest edition.
    assert tradeshows.year_from("https://x.com/2026/list", "2026 show · 2025 archive") == 2026


def test_a_page_with_no_year_yields_none():
    assert tradeshows.year_from("https://iseurope.org/exhibitor-directory") is None


def test_a_phone_number_is_not_a_year():
    assert tradeshows.year_from("call 1-800-555-2099 ext 4021") is None


def test_the_hook_names_the_show_and_the_year():
    assert tradeshows.hook_for("InfoComm", 2026) == "看到你们在 InfoComm 2026 的展位。"


def test_a_booth_is_included_only_when_there_is_one():
    assert "C120" in tradeshows.hook_for("ISE", 2026, "C120")
    assert tradeshows.hook_for("ISE", 2026, None).endswith("展位。")


def test_without_a_year_no_exhibitor_hook_is_written():
    cands = [{"domain": "a.com"}]
    out = tradeshows.prepare(cands, show="ISE", year=None, url="https://x/list")
    assert out["hooked"] == 0
    assert cands[0].get("hook") is None
    assert "没有年份" in out["skipped_reason"]


def test_a_stale_directory_is_harvested_but_not_hooked():
    # "We saw your booth" about a 2019 show invites "that was years ago".
    cands = [{"domain": "a.com"}]
    out = tradeshows.prepare(cands, show="ISE", year=2019, url="https://x/2019",
                             today=dt.date(2026, 8, 26))
    assert (out["hooked"], cands[0].get("hook")) == (0, None)
    assert "太旧" in out["skipped_reason"]


def test_a_recent_directory_hooks_every_candidate():
    cands = [{"domain": "a.com"}, {"domain": "b.com"}]
    out = tradeshows.prepare(cands, show="InfoComm", year=2026,
                             url="https://infocomm.org/2026/list",
                             today=dt.date(2026, 8, 26))
    assert out["hooked"] == 2
    assert all("InfoComm 2026" in c["hook"] for c in cands)


def test_the_directory_page_is_recorded_as_the_source():
    cands = [{"domain": "a.com"}]
    url = "https://infocomm.org/2026/list"
    tradeshows.prepare(cands, show="InfoComm", year=2026, url=url,
                       today=dt.date(2026, 8, 26))
    assert url in cands[0]["source_urls"]


def test_a_booth_is_never_invented():
    cands = [{"domain": "a.com"}, {"domain": "b.com", "booth": "Hall 5 C120"}]
    tradeshows.prepare(cands, show="ISE", year=2026, url="https://x/2026",
                       today=dt.date(2026, 8, 26))
    assert cands[0]["hook"] == "看到你们在 ISE 2026 的展位。"
    assert "Hall 5 C120" in cands[1]["hook"]


@pytest.fixture
def harvested(monkeypatch):
    """A directory page carrying two real prospects and one Chinese LED factory."""
    rows = [
        {"domain": "verumav.com", "excluded": False, "fit_score": 70},
        {"domain": "brightlinkav.com", "excluded": False, "fit_score": 65},
        {"domain": "szledfactory.cn", "excluded": True, "exclude_reason": "同行"},
    ]
    monkeypatch.setattr(tradeshows, "run_page_discovery", lambda *a, **k: rows)
    return rows


def test_peer_factories_never_reach_the_import(harvested):
    out = tradeshows.run(None, "https://infocomm.org/2026/list", show="InfoComm")
    assert out["excluded"] == 1
    assert {c["domain"] for c in out["candidates"]} == {"verumav.com", "brightlinkav.com"}


def test_the_year_is_read_off_the_url_when_not_given(harvested):
    out = tradeshows.run(None, "https://infocomm.org/2026/list", show="InfoComm")
    assert out["year"] == 2026
    assert out["hooked"] == 2


def test_preview_does_not_import(harvested, monkeypatch):
    called = []
    monkeypatch.setattr(tradeshows, "import_candidates",
                        lambda *a, **k: called.append(a) or {})
    out = tradeshows.run(None, "https://infocomm.org/2026/list", show="InfoComm")
    assert called == []
    assert "imported" not in out
