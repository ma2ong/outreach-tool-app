import app.main as main
from app.db import connect, init_schema
from fastapi.testclient import TestClient


def _client(tmp_path):
    db = str(tmp_path / "t.db")
    c = connect(db)
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, email) VALUES
            (1, 'Alpha AV', 'USA', 'a@alpha.com'),
            (2, 'Beta Screens', 'USA', 'b@beta.com');
    """)
    c.commit()
    c.close()
    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    return TestClient(main.app)


_SEQ = {"name": "Cold 3-touch", "channel": "email", "steps": [
    {"day_offset": 0, "subject": "Hi {name}", "body": "First"},
    {"day_offset": 3, "body": "Second"},
]}


def test_create_list_enroll_due_advance(tmp_path):
    client = _client(tmp_path)
    r = client.post("/api/sequences", json=_SEQ)
    assert r.status_code == 200
    sid = r.json()["id"]
    assert len(r.json()["steps"]) == 2

    assert client.get("/api/sequences").json()[0]["id"] == sid

    r = client.post(f"/api/sequences/{sid}/enroll", json={"lead_nos": [1, 2]})
    assert r.json()["enrolled"] == 2

    due = client.get("/api/sequences/due").json()
    assert {d["lead_no"] for d in due} == {1, 2}
    assert all(d["step_order"] == 0 for d in due)

    eid = due[0]["enrollment_id"]
    assert client.post("/api/sequences/advance", json={"enrollment_ids": [eid]}).json()["advanced"] == 1
    # step 1 is +3 days, so that lead drops out of today's due queue
    assert {d["lead_no"] for d in client.get("/api/sequences/due").json()} == {2}


def test_due_channel_filter(tmp_path):
    client = _client(tmp_path)
    sid = client.post("/api/sequences", json=_SEQ).json()["id"]
    client.post(f"/api/sequences/{sid}/enroll", json={"lead_nos": [1]})
    assert client.get("/api/sequences/due?channel=email").json()
    assert client.get("/api/sequences/due?channel=whatsapp").json() == []


def test_send_due_runs_job_and_advances(tmp_path):
    import app.api.send as send_api
    import app.api.sequences as sequences_api
    from app import jobs
    jobs.clear()
    sent = []
    send_api.SENDER = lambda to, s, b, a: sent.append(to)
    db = str(tmp_path / "t.db")
    c = connect(db)
    init_schema(c)
    c.execute("INSERT INTO leads(no, company_en, email) VALUES (1,'Alpha','a@alpha.com')")
    c.commit()
    c.close()
    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    sequences_api.DB_PATH = db  # background job opens its own connection via this global
    client = TestClient(main.app)

    sid = client.post("/api/sequences", json=_SEQ).json()["id"]
    client.post(f"/api/sequences/{sid}/enroll", json={"lead_nos": [1]})
    eid = client.get("/api/sequences/due").json()[0]["enrollment_id"]
    r = client.post("/api/sequences/send", json={"enrollment_ids": [eid], "image": None})
    assert r.json()["will_send"] == 1
    job = client.get(f"/api/send/jobs/{r.json()['job_id']}").json()
    assert job["status"] == "done" and job["result"]["sent"] == 1
    assert sent == ["a@alpha.com"]
    # advanced to step 1 -> no longer due today
    assert client.get("/api/sequences/due").json() == []


def test_validation(tmp_path):
    client = _client(tmp_path)
    assert client.post("/api/sequences", json={"name": " ", "channel": "email",
                                               "steps": [{"body": "x"}]}).status_code == 400
    assert client.post("/api/sequences", json={"name": "x", "channel": "email",
                                               "steps": []}).status_code == 400
    assert client.post("/api/sequences", json={"name": "x", "channel": "fax",
                                               "steps": [{"body": "x"}]}).status_code == 400
    assert client.post("/api/sequences/999/enroll", json={"lead_nos": [1]}).status_code == 404
