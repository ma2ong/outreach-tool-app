import app.main as main
from app import jobs
from app.db import connect, init_schema
from fastapi.testclient import TestClient


def _client(tmp_path):
    import app.api.discover as disc
    db = str(tmp_path / "t.db")
    c = connect(db)
    init_schema(c)
    c.execute("INSERT INTO leads(no, company_en, website) VALUES (1,'Alpha','alpha.com')")
    c.commit()
    c.close()
    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    disc.DB_PATH = db
    disc.SEARCH_FN = lambda q, limit: [{"domain": "alpha.com", "title": "Alpha"},
                                       {"domain": "newco.com", "title": "New Co"}]
    disc.ENRICH_FN = lambda d: {"domain": d, "emails": [f"info@{d}"], "email": f"info@{d}"}
    return TestClient(main.app), db


def test_discover_job_and_import(tmp_path):
    jobs.clear()
    client, db = _client(tmp_path)
    r = client.post("/api/discover", json={"query": "led wall", "limit": 10})
    jid = r.json()["job_id"]
    job = client.get(f"/api/discover/jobs/{jid}").json()
    assert job["status"] == "done"
    cands = job["result"]["candidates"]
    assert {c["domain"] for c in cands} == {"alpha.com", "newco.com"}
    # import the new one with full contact fields
    r2 = client.post("/api/leads/import", json={"country": "USA", "candidates": [
        {"company_en": "New Co", "website": "newco.com", "email": "info@newco.com",
         "phone": "+5511956635316", "instagram": "newcoig", "facebook": "newcofb",
         "linkedin": "linkedin.com/company/newco"}]})
    assert r2.json()["imported"] == 1
    conn = connect(db)
    row = conn.execute("SELECT * FROM leads WHERE website='newco.com'").fetchone()
    assert row is not None
    assert row["phone"] == "+5511956635316"
    assert row["instagram"] == "newcoig"
    assert row["facebook"] == "newcofb"
    assert row["linkedin"] == "linkedin.com/company/newco"


def test_discovery_background_job_uses_request_database(tmp_path, monkeypatch):
    import app.api.discover as disc

    jobs.clear()
    client, _ = _client(tmp_path)
    wrong = str(tmp_path / "wrong.db")
    conn = connect(wrong)
    init_schema(conn)
    conn.execute("INSERT INTO leads(no, company_en, website) VALUES (99,'Wrong','newco.com')")
    conn.commit()
    conn.close()
    monkeypatch.setattr(disc, "DB_PATH", wrong, raising=False)

    response = client.post("/api/discover", json={"query": "led wall", "limit": 10})
    job = client.get(f"/api/discover/jobs/{response.json()['job_id']}").json()

    assert job["status"] == "done"
    candidates = {row["domain"]: row for row in job["result"]["candidates"]}
    assert candidates["alpha.com"]["duplicate_of"] == 1
    assert candidates["newco.com"]["duplicate_of"] is None


def test_import_not_blocked_by_generic_company_name(tmp_path):
    """Regression: lead named 'Contact' in DB must not swallow every candidate titled 'Contact'."""
    jobs.clear()
    client, db = _client(tmp_path)
    conn = connect(db)
    conn.execute("INSERT INTO leads(no, company_en, website) VALUES (2,'Contact','other.com')")
    conn.commit()
    conn.close()
    r = client.post("/api/leads/import", json={"country": "USA", "candidates": [
        {"company_en": "Contact", "website": "brandnew.com", "email": "a@brandnew.com"}]})
    body = r.json()
    assert body["imported"] == 1 and body["skipped"] == []


def test_import_reports_skipped_duplicates(tmp_path):
    jobs.clear()
    client, _ = _client(tmp_path)
    r = client.post("/api/leads/import", json={"country": "USA", "candidates": [
        {"company_en": "Alpha", "website": "alpha.com"}]})
    body = r.json()
    assert body["imported"] == 0
    assert body["skipped"] == [{"company_en": "Alpha", "website": "alpha.com",
                                "duplicate_of": 1, "enriched": []}]


def test_a_known_company_is_enriched_rather_than_discarded(tmp_path):
    """docs/68 R4.3. Prospecting keeps walking into companies already in the book, and
    what it learned on the way used to be dropped because the only question asked was
    "is this new?"."""
    jobs.clear()
    client, db = _client(tmp_path)
    r = client.post("/api/leads/import", json={"country": "USA", "candidates": [
        {"company_en": "Alpha", "website": "alpha.com",
         "email": "buyer@alpha.com", "phone": "+13468378628"}]})
    assert r.json()["enriched_fields"] == 2

    row = connect(db).execute("SELECT email, phone FROM leads WHERE no=1").fetchone()
    assert row["email"] == "buyer@alpha.com"
    assert row["phone"] == "+13468378628"


def test_discover_multiple_queries_dedup_by_domain(tmp_path):
    jobs.clear()
    client, _ = _client(tmp_path)
    r = client.post("/api/discover", json={"queries": ["led wall Texas", "led rental Texas"], "limit": 10})
    job = client.get(f"/api/discover/jobs/{r.json()['job_id']}").json()
    assert job["status"] == "done"
    # both queries return the same two domains; merged result must not duplicate them
    assert sorted(c["domain"] for c in job["result"]["candidates"]) == ["alpha.com", "newco.com"]


def test_discover_requires_query(tmp_path):
    client, _ = _client(tmp_path)
    assert client.post("/api/discover", json={"limit": 10}).status_code == 400
    assert client.post("/api/discover", json={"queries": ["  "], "limit": 10}).status_code == 400


def test_quick_add_website_enriches(tmp_path):
    import app.api.leads as leads_api
    client, db = _client(tmp_path)
    leads_api.ENRICH_FN = lambda d: {"email": f"info@{d}", "phone": "+1555", "instagram": "newig",
                                     "company": "New Co Inc", "icp_type": "rental", "fit_score": 88}
    try:
        r = client.post("/api/leads/quick_add", json={"url": "https://www.newco.com/about", "country": "USA"})
        body = r.json()
        assert body["duplicate_of"] is None
        lead = body["lead"]
        assert lead["company_en"] == "New Co Inc" and lead["email"] == "info@newco.com"
        assert lead["country"] == "USA" and lead["instagram"] == "newig"
        assert "租赁" in lead["target_fit"] or "rental" in lead["target_fit"]
        assert any("快速添加" in n["text"] for n in lead["notes"])
    finally:
        leads_api.ENRICH_FN = None


def test_quick_add_instagram_no_enrich_needed(tmp_path):
    client, _ = _client(tmp_path)
    r = client.post("/api/leads/quick_add", json={"url": "https://www.instagram.com/mccannsystems"})
    lead = r.json()["lead"]
    assert lead["instagram"] == "mccannsystems"
    assert lead["company_en"] == "Mccannsystems"


def test_quick_add_duplicate_returns_existing(tmp_path):
    client, _ = _client(tmp_path)
    r = client.post("/api/leads/quick_add", json={"url": "https://alpha.com"})
    body = r.json()
    assert body["duplicate_of"] == 1 and body["lead"]["no"] == 1


def test_quick_add_bad_url_400(tmp_path):
    client, _ = _client(tmp_path)
    assert client.post("/api/leads/quick_add", json={"url": "not a url"}).status_code == 400
    assert client.post("/api/leads/quick_add",
                       json={"url": "https://instagram.com/p/Cxyz/"}).status_code == 400


def test_import_uses_candidate_country_when_given(tmp_path):
    """Searching 'South Korea' also surfaces US firms — each lead keeps its own country."""
    jobs.clear()
    client, db = _client(tmp_path)
    client.post("/api/leads/import", json={"country": "South Korea", "candidates": [
        {"company_en": "Ara", "website": "arasystem.kr", "country": "South Korea"},
        {"company_en": "US Co", "website": "usco.com", "country": "Mexico"},
        {"company_en": "No Country", "website": "mystery.io"}]})
    conn = connect(db)
    got = {r["website"]: r["country"] for r in conn.execute("SELECT website, country FROM leads")}
    assert got["arasystem.kr"] == "South Korea"
    assert got["usco.com"] == "Mexico"
    assert got["mystery.io"] == "South Korea"  # falls back to the request country


def test_discover_flags_chinese_peers_and_directories(tmp_path):
    import app.api.discover as disc
    jobs.clear()
    client, _ = _client(tmp_path)
    disc.SEARCH_FN = lambda q, limit: [{"domain": "gldled.com", "title": "GLD LED"},
                                       {"domain": "alibaba.com", "title": "Alibaba"},
                                       {"domain": "arasystem.kr", "title": "Ara System"}]
    disc.ENRICH_FN = lambda d: {"phone": "+8613809866355" if d == "gldled.com" else "+827048950794"}
    try:
        r = client.post("/api/discover", json={"queries": ["led"], "limit": 10})
        cands = client.get(f"/api/discover/jobs/{r.json()['job_id']}").json()["result"]["candidates"]
        by = {c["domain"]: c for c in cands}
        assert by["gldled.com"]["excluded"] and "同行" in by["gldled.com"]["exclude_reason"]
        assert by["alibaba.com"]["exclude_reason"] == "B2B 目录站/平台"
        assert not by["arasystem.kr"]["excluded"]
        assert by["arasystem.kr"]["country"] == "South Korea"
    finally:
        disc.SEARCH_FN = lambda q, limit: [{"domain": "alpha.com", "title": "Alpha"},
                                           {"domain": "newco.com", "title": "New Co"}]
        disc.ENRICH_FN = lambda d: {"domain": d, "emails": [f"info@{d}"], "email": f"info@{d}"}


def test_discover_custom_exclude_countries(tmp_path):
    import app.api.discover as disc
    jobs.clear()
    client, _ = _client(tmp_path)
    disc.SEARCH_FN = lambda q, limit: [{"domain": "ledindia.in", "title": "LED India"}]
    disc.ENRICH_FN = lambda d: {"phone": "+919876543210"}
    try:
        r = client.post("/api/discover", json={"queries": ["led"], "limit": 10,
                                               "exclude_countries": ["India"]})
        c = client.get(f"/api/discover/jobs/{r.json()['job_id']}").json()["result"]["candidates"][0]
        assert c["excluded"] and c["exclude_reason"] == "排除国家（India）"
    finally:
        disc.SEARCH_FN = lambda q, limit: [{"domain": "alpha.com", "title": "Alpha"},
                                           {"domain": "newco.com", "title": "New Co"}]
        disc.ENRICH_FN = lambda d: {"domain": d, "emails": [f"info@{d}"], "email": f"info@{d}"}


def test_excluded_candidate_skips_enrich(tmp_path):
    """A peer/directory must not cost an enrich fetch — that is the slow part."""
    import app.api.discover as disc
    jobs.clear()
    client, _ = _client(tmp_path)
    calls: list[str] = []
    disc.SEARCH_FN = lambda q, limit: [{"domain": "alibaba.com", "title": "Alibaba"},
                                       {"domain": "newco.com", "title": "New Co"}]
    disc.ENRICH_FN = lambda d: (calls.append(d), {"email": f"info@{d}"})[1]
    try:
        r = client.post("/api/discover", json={"queries": ["led"], "limit": 10})
        client.get(f"/api/discover/jobs/{r.json()['job_id']}")
        assert calls == ["newco.com"]
    finally:
        disc.SEARCH_FN = lambda q, limit: [{"domain": "alpha.com", "title": "Alpha"},
                                           {"domain": "newco.com", "title": "New Co"}]
        disc.ENRICH_FN = lambda d: {"domain": d, "emails": [f"info@{d}"], "email": f"info@{d}"}


def test_discover_page_harvests_and_tags_source(tmp_path):
    import app.api.discover as disc
    jobs.clear()
    client, _ = _client(tmp_path)
    disc.HARVEST_FN = lambda url, limit: ["alpha.com", "distco.com"]
    r = client.post("/api/discover/page", json={"url": "https://absen.com/where-to-buy", "limit": 40})
    assert r.status_code == 200
    job = client.get(f"/api/discover/jobs/{r.json()['job_id']}").json()
    assert job["status"] == "done"
    cands = job["result"]["candidates"]
    assert {c["domain"] for c in cands} == {"alpha.com", "distco.com"}
    assert all(c["source"] == "名录/经销商页" for c in cands)


def test_discover_page_rejects_bad_url(tmp_path):
    client, _ = _client(tmp_path)
    assert client.post("/api/discover/page", json={"url": "absen.com"}).status_code == 400


def test_discover_jobs_404(tmp_path):
    client, _ = _client(tmp_path)
    assert client.get("/api/discover/jobs/nope").status_code == 404
