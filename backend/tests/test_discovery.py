import threading

from app import discovery


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
