import app.main as main
from app import jobs
from app.db import connect, init_schema
from fastapi.testclient import TestClient


def _client(tmp_path):
    import app.api.send as send_api
    db = str(tmp_path / "t.db")
    c = connect(db)
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, email) VALUES (1,'Alpha','a@a.com'),(2,'Beta','b@b.com');
    """)
    c.commit()
    c.close()
    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    send_api.DB_PATH = db  # background job opens its own connection via this module global
    return TestClient(main.app)


def test_send_email_runs_job(tmp_path):
    import app.api.send as send_api
    jobs.clear()
    sent = []
    send_api.SENDER = lambda to, s, b, a: sent.append(to)
    send_api.DELAY_RANGE = (0, 0)
    client = _client(tmp_path)
    r = client.post("/api/send/email", json={"lead_nos": [1, 2], "subject": "Hi {name}", "body": "Hello {name}"})
    assert r.status_code == 200
    jid = r.json()["job_id"]
    job = client.get(f"/api/send/jobs/{jid}").json()
    assert job["status"] == "done"
    assert job["result"]["sent"] == 2
    assert set(sent) == {"a@a.com", "b@b.com"}


def test_background_send_reopens_the_request_database_not_a_module_default(tmp_path, monkeypatch):
    import app.api.send as send_api

    jobs.clear()
    client = _client(tmp_path)
    wrong = str(tmp_path / "wrong.db")
    wrong_conn = connect(wrong)
    init_schema(wrong_conn)
    wrong_conn.close()
    monkeypatch.setattr(send_api, "DB_PATH", wrong, raising=False)
    sent: list[str] = []
    monkeypatch.setattr(send_api, "SENDER", lambda to, *_: sent.append(to))
    monkeypatch.setattr(send_api, "DELAY_RANGE", (0, 0))

    response = client.post(
        "/api/send/email",
        json={"lead_nos": [1], "subject": "Hi {name}", "body": "Hello {name}"},
    )
    job = client.get(f"/api/send/jobs/{response.json()['job_id']}").json()

    assert job["status"] == "done"
    assert sent == ["a@a.com"]
    assert connect(wrong).execute("SELECT COUNT(*) c FROM send_log").fetchone()["c"] == 0


def test_send_jobs_404(tmp_path):
    assert _client(tmp_path).get("/api/send/jobs/nope").status_code == 404
