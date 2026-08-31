import threading

import pytest

from app import discovery, screening


def test_run_discovery_flags_duplicates_and_progress(conn):
    # conn fixture: lead 1 has website 'alpha.com'
    search_fn = lambda q, limit: [{"domain": "alpha.com", "title": ""},
                                  {"domain": "newco.com", "title": ""}]
    enrich_fn = lambda d: {"domain": d, "emails": [f"info@{d}"], "email": f"info@{d}",
                           "phone": "+5511956635316", "instagram": "acmeled",
                           "facebook": "acmefb", "linkedin": "linkedin.com/company/acme"}
    seen = []
    cands = discovery.run_discovery(conn, "led", 10, search_fn=search_fn, enrich_fn=enrich_fn,
                                    on_progress=lambda done, total: seen.append((done, total)))
    by = {c["domain"]: c for c in cands}
    assert by["alpha.com"]["duplicate_of"] == 1
    assert by["newco.com"]["duplicate_of"] is None
    assert by["newco.com"]["email"] == "info@newco.com"
    assert by["newco.com"]["phone"] == "+5511956635316"
    assert by["newco.com"]["instagram"] == "acmeled"
    assert by["newco.com"]["facebook"] == "acmefb"
    assert by["newco.com"]["linkedin"] == "linkedin.com/company/acme"
    assert seen[-1] == (2, 2)


def test_run_page_discovery_harvests_then_enriches(conn):
    # conn fixture: lead 1 has website 'alpha.com'
    harvest_fn = lambda u, limit: ["alpha.com", "distco.com"]
    enrich_fn = lambda d: {"domain": d, "emails": [f"sales@{d}"], "email": f"sales@{d}",
                           "phone": None, "instagram": None, "facebook": None, "linkedin": None,
                           "company": "Dist Co"}
    cands = discovery.run_page_discovery(conn, "https://absen.com/where-to-buy",
                                         harvest_fn=harvest_fn, enrich_fn=enrich_fn)
    by = {c["domain"]: c for c in cands}
    assert by["alpha.com"]["duplicate_of"] == 1      # already in DB
    assert by["distco.com"]["duplicate_of"] is None
    assert by["distco.com"]["email"] == "sales@distco.com"
    assert all(c["source"] == "名录/经销商页" for c in cands)


def test_run_discovery_tags_search_source(conn):
    cands = discovery.run_discovery(conn, "led", 10,
                                    search_fn=lambda q, l: [{"domain": "x.com", "title": ""}],
                                    enrich_fn=lambda d: {"domain": d, "emails": [], "email": None})
    assert cands[0]["source"] == "搜索"


def test_run_discovery_missing_contact_fields_default_none(conn):
    search_fn = lambda q, limit: [{"domain": "bare.com", "title": ""}]
    enrich_fn = lambda d: {"domain": d, "emails": [], "email": None}
    cands = discovery.run_discovery(conn, "led", 10, search_fn=search_fn, enrich_fn=enrich_fn)
    c = cands[0]
    assert c["phone"] is None and c["instagram"] is None
    assert c["facebook"] is None and c["linkedin"] is None


def test_domain_enrichment_runs_as_a_bounded_parallel_batch(conn):
    domains = [{"domain": f"site-{i}.com", "title": ""} for i in range(4)]
    lock = threading.Lock()
    all_started = threading.Event()
    active = 0
    released = []

    def enrich(domain):
        nonlocal active
        with lock:
            active += 1
            if active == 4:
                all_started.set()
        released.append(all_started.wait(1))
        with lock:
            active -= 1
        return {"domain": domain, "emails": [], "email": None}

    discovery.run_discovery(conn, "led", search_fn=lambda q, n: domains,
                            enrich_fn=enrich)
    assert released == [True, True, True, True]


def test_live_discovery_uses_a_shorter_per_page_timeout(monkeypatch):
    seen = {}
    monkeypatch.setattr(discovery, "jina_fetch",
                        lambda url, timeout: seen.update(url=url, timeout=timeout) or "ok")
    assert discovery._bounded_fetch("https://example.com") == "ok"
    assert seen["timeout"] == discovery.DISCOVERY_FETCH_TIMEOUT


def test_detected_country_beats_the_searched_market(conn):
    """Regression: searching the Korean market imported a Fullerton, CA integrator as
    a South Korean lead. The company's own address decides; the search does not."""
    def fake_enrich(domain):
        return {"email": "hello@eidim.com", "country": "USA", "icp_type": "integrator",
                "fit_score": 90, "brief": "AV integrator", "hook": "school AV"}

    found = discovery.run_discovery(
        conn, "LED display Korea", search_fn=lambda q, lim: [{"domain": "eidim.com",
                                                              "title": "EIDIM"}],
        enrich_fn=fake_enrich)
    assert found[0]["country"] == "USA"
    accepted, rejected = discovery.qualify_for_auto_import(
        found, minimum_fit=50, target_country="South Korea")
    assert accepted == []
    assert "目标市场不符" in rejected[0]["reason"]


def test_import_keeps_the_detected_country(conn):
    result = discovery.import_candidates(
        conn, [{"domain": "eidim.com", "website": "eidim.com", "company_en": "Eidim",
                "country": "USA", "email": "hello@eidim.com"}],
        default_country="South Korea")
    row = conn.execute("SELECT country FROM leads WHERE no=?",
                       (result["imported_lead_nos"][0],)).fetchone()
    assert row["country"] == "USA"


# --- docs/78: a blog post is not a customer ----------------------------------------

@pytest.mark.parametrize("name", [
    "Robot Challenge Screen",
    "Checking your browser",
    "Just a moment...",
    "URL Source: https://m.blog.naver.com/x",
    "contact-us님의블로그 : 네이버 블로그",
    "Attention Required! | Cloudflare",
    "Page not found",
])
def test_a_bot_wall_is_not_a_company(name):
    assert not discovery.looks_like_a_company(name)


@pytest.mark.parametrize("name", [
    "Avidex", "LED Factory Chile", "AVDG", "옥외나우", "Big Screen Solutions",
])
def test_a_real_company_still_reads_as_one(name):
    assert discovery.looks_like_a_company(name)


def test_a_candidate_read_off_a_bot_wall_never_becomes_a_lead(conn):
    """docs/78 R1. thesupersignguy.com was filed as an AV integrator on a Cloudflare
    screen — the brief, the hook and the 85 all came off a page that was not theirs."""
    result = discovery.import_candidates(conn, [{
        "company_en": "Robot Challenge Screen", "domain": "thesupersignguy.com",
        "email": "info@thesupersignguy.com", "icp_type": "integrator", "fit_score": 85,
    }])
    assert result["imported"] == 0
    assert result["skipped"][0]["not_a_company"]
    assert conn.execute("SELECT COUNT(*) FROM leads WHERE website LIKE '%supersign%'"
                        ).fetchone()[0] == 0


@pytest.mark.parametrize("domain", [
    "blog.naver.com", "m.blog.naver.com", "ledplus.tistory.com", "brunch.co.kr",
    "ensun.io", "trademo.com", "f6s.com",
])
def test_a_content_or_data_platform_is_screened_out(domain):
    """docs/78 R2. These score high precisely because they are pages about the trade."""
    out = screening.screen({"domain": domain})
    assert out["excluded"]
    assert out["exclude_reason"]


def test_an_integrator_the_classifier_could_not_type_still_gets_in(conn):
    """docs/78 R1's last row: avidex is a real AV integrator whose homepage says none
    of the words. Rejecting unknown ICP would throw it away with the blogs."""
    result = discovery.import_candidates(conn, [{
        "company_en": "Avidex", "domain": "avidex.com", "email": "info@avidex.com",
        "icp_type": "unknown", "fit_score": 0,
        "brief": 'The site mentions "audio visual".',
    }])
    assert result["imported"] == 1
