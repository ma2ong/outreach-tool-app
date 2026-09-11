import app.main as main
from app import jobs
from app.db import connect, init_schema
from fastapi.testclient import TestClient

_PAGES = {
    "https://rent.com": "LED screen rental for concerts and events",
    "https://bake.com": "artisanal sourdough",
}


def _client(tmp_path):
    import app.api.classify as classify_api
    db = str(tmp_path / "t.db")
    c = connect(db)
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, website) VALUES
            (1,'Rent Co','rent.com'), (2,'Bakery','bake.com'), (3,'NoSite',NULL);
    """)
    c.commit()
    c.close()
    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    classify_api.DB_PATH = db
    classify_api.FETCHER = lambda url: _PAGES[url]
    return TestClient(main.app), db


def test_classify_job_applies_types(tmp_path):
    jobs.clear()
    client, db = _client(tmp_path)
    r = client.post("/api/leads/classify", json={})
    job = client.get(f"/api/leads/classify/jobs/{r.json()['job_id']}").json()
    assert job["status"] == "done"
    assert job["result"]["checked"] == 2
    assert job["result"]["by_type"]["rental"] == 1
    conn = connect(db)
    assert conn.execute("SELECT target_fit FROM leads WHERE no=1").fetchone()["target_fit"].startswith("租赁公司")
    # docs/112 R1：判不出来的那家也留下结论，否则它和从没分过级的长得一样
    assert conn.execute("SELECT target_fit FROM leads WHERE no=2").fetchone()["target_fit"] == "未知 (0)"


def test_classify_background_job_uses_request_database(tmp_path, monkeypatch):
    import app.api.classify as classify_api

    jobs.clear()
    client, db = _client(tmp_path)
    wrong = str(tmp_path / "wrong.db")
    conn = connect(wrong)
    init_schema(conn)
    conn.close()
    monkeypatch.setattr(classify_api, "DB_PATH", wrong, raising=False)

    response = client.post("/api/leads/classify", json={"lead_nos": [1]})
    job = client.get(f"/api/leads/classify/jobs/{response.json()['job_id']}").json()

    assert job["status"] == "done"
    assert connect(db).execute("SELECT target_fit FROM leads WHERE no=1").fetchone()["target_fit"]
    assert connect(wrong).execute("SELECT COUNT(*) c FROM leads").fetchone()["c"] == 0


def test_classify_jobs_404(tmp_path):
    client, _ = _client(tmp_path)
    assert client.get("/api/leads/classify/jobs/nope").status_code == 404
