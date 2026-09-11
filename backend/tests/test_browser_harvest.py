"""名录页里抓不动的那一类 (docs/124).

Four real directory pages returned zero companies through jina on 2026-09-10: two
answered with an anti-bot wall, and the other two handed over CDN and social domains
while the exhibitor and distributor lists stayed inside JavaScript. A browser reads
them; the price is that a browser also invents things, so the interface deliberately
carries one field.
"""
import subprocess

import pytest

from app import browser_harvest as bh


@pytest.fixture(autouse=True)
def installed(monkeypatch, tmp_path):
    """Every test but the unavailability ones assumes the venv and the key are there.

    The suite must never reach the real one: a test that finds a working bu-venv would
    launch Chrome and call deepseek.
    """
    python = tmp_path / "python.exe"
    python.write_text("")
    monkeypatch.setattr(bh, "VENV_PYTHON", python)
    monkeypatch.setattr(bh, "_key", lambda: "test-key")


def _run_returning(payload: str):
    def run(argv, timeout):
        return payload
    return run


# --------------------------------------------------------------- R1 只交域名

def test_only_the_domain_survives_the_crossing():
    """docs/124 R1. The run that produced this spec read a company name off the image
    filename `syscom-cloned-21865-Avientek-Logo--768x134.png`. Names come from enrich,
    which reads the company's own site; nothing the browser says about a name gets in."""
    out = bh.harvest_with_browser(
        "https://www.absen.com/partners/",
        run=_run_returning('{"companies":[{"name":"syscom-cloned-21865-Avientek-Logo",'
                           '"country":"Mars","domain":"avientek.com"}]}'))
    assert out == ["avientek.com"]


def test_a_company_with_no_domain_is_not_a_lead():
    out = bh.harvest_with_browser("https://www.absen.com/partners/", run=_run_returning(
        '{"companies":[{"name":"Some Firm"},{"name":"Real","domain":"realco.com"}]}'))
    assert out == ["realco.com"]


def test_the_same_junk_filter_as_the_crawler_applies():
    """docs/70 R5 in miniature: one filter, not a second slightly different one."""
    out = bh.harvest_with_browser("https://www.absen.com/partners/", run=_run_returning(
        '{"companies":[{"domain":"facebook.com"},{"domain":"cdn.googleapis.com"},'
        '{"domain":"absen.com"},{"domain":"localhost:8000"},{"domain":"192.168.1.5"},'
        '{"domain":"psco.co.uk"}]}'))
    assert out == ["psco.co.uk"]


def test_a_full_url_is_reduced_to_its_host():
    out = bh.harvest_with_browser("https://www.absen.com/partners/", run=_run_returning(
        '{"companies":[{"domain":"https://www.midwich.com/en/contact"}]}'))
    assert out == ["midwich.com"]


def test_the_same_partner_listed_twice_is_one_domain():
    out = bh.harvest_with_browser("https://www.absen.com/partners/", run=_run_returning(
        '{"companies":[{"domain":"psco.co.uk"},{"domain":"www.psco.co.uk"}]}'))
    assert out == ["psco.co.uk"]


def test_the_limit_is_honoured():
    payload = '{"companies":[' + ",".join(
        f'{{"domain":"co{i}.com"}}' for i in range(50)) + ']}'
    assert len(bh.harvest_with_browser("https://x.com/list", limit=10,
                                       run=_run_returning(payload))) == 10


# --------------------------------------------------------------- R3 域名白名单

def test_the_allowlist_comes_from_the_url():
    assert bh.allowed_domains_for("https://www.absen.com/partners/") == ["*.absen.com"]


def test_a_subdomain_listing_does_not_open_its_parent():
    """`exhibitors.iseurope.org` is one listing, not permission to walk iseurope.org."""
    assert bh.allowed_domains_for("https://exhibitors.iseurope.org/2026/Exhibitor") == [
        "*.exhibitors.iseurope.org"]


def test_the_browser_is_told_only_that_one_domain():
    """The probe run tried DuckDuckGo, Bing and Google when the page stalled; all three
    were refused by this list. It is the mechanical half of "only reads the target"."""
    seen = {}

    def run(argv, timeout):
        seen["argv"] = argv
        return '{"companies":[]}'

    bh.harvest_with_browser("https://www.absen.com/partners/", run=run)
    joined = " ".join(seen["argv"])
    assert "*.absen.com" in joined
    for engine in ("duckduckgo.com", "bing.com", "google.com"):
        assert engine not in joined


# --------------------------------------------------------------- R2/R5 未启用 ≠ 失败

def test_a_missing_venv_is_unavailable_not_broken(monkeypatch, tmp_path):
    monkeypatch.setattr(bh, "VENV_PYTHON", tmp_path / "nope" / "python.exe")
    assert "bu-venv" in bh.unavailable()


def test_a_missing_key_names_the_file_it_wants(monkeypatch, tmp_path):
    python = tmp_path / "python.exe"
    python.write_text("")
    monkeypatch.setattr(bh, "VENV_PYTHON", python)
    monkeypatch.setattr(bh, "_key", lambda: "")
    assert "deepseek_key.txt" in bh.unavailable()


def test_an_unavailable_engine_refuses_before_launching_anything(monkeypatch, tmp_path):
    monkeypatch.setattr(bh, "VENV_PYTHON", tmp_path / "nope" / "python.exe")

    def run(argv, timeout):
        raise AssertionError("must not launch a browser when unavailable")

    with pytest.raises(bh.Unavailable):
        bh.harvest_with_browser("https://www.absen.com/partners/", run=run)


# --------------------------------------------------------------- R6 上限

def test_a_run_that_hangs_gives_back_nothing_rather_than_hanging():
    def run(argv, timeout):
        raise subprocess.TimeoutExpired(cmd="bu", timeout=timeout)

    assert bh.harvest_with_browser("https://x.com/list", run=run) == []


def test_a_crashed_run_is_not_a_500():
    def run(argv, timeout):
        raise subprocess.CalledProcessError(1, "bu", stderr="chrome died")

    assert bh.harvest_with_browser("https://x.com/list", run=run) == []


def test_unreadable_output_is_no_companies_not_an_exception():
    assert bh.harvest_with_browser("https://x.com/list",
                                   run=_run_returning("Traceback...")) == []


def test_the_step_budget_is_passed_down():
    seen = {}

    def run(argv, timeout):
        seen["argv"], seen["timeout"] = argv, timeout
        return '{"companies":[]}'

    bh.harvest_with_browser("https://x.com/list", run=run)
    assert str(bh.MAX_STEPS) in " ".join(seen["argv"])
    assert seen["timeout"] == bh.RUN_TIMEOUT


# --------------------------------------------------------------- R4 不进调度器

def test_no_scheduler_can_reach_the_browser(tmp_path):
    """docs/124 R4. It opens a real Chrome window, so a timer must never decide when.

    The rule is not enforceable by a guard — nothing stops an import — so it is checked
    here, where adding the import to autosend or the Agent turns red immediately.
    """
    import pathlib

    root = pathlib.Path(bh.__file__).resolve().parent
    scheduled = [root / "autosend.py", root / "worker.py", root / "social_queue.py",
                 root / "runtime.py", *sorted((root / "agent").glob("*.py"))]
    guilty = [p.name for p in scheduled
              if p.exists() and "browser_harvest" in p.read_text(encoding="utf-8")]
    assert guilty == []
