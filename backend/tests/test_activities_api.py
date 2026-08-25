import app.main as main
from app.agent import task_ownership
from app.db import connect, init_schema
from fastapi.testclient import TestClient


def _client(tmp_path):
    db = str(tmp_path / "t.db")
    conn = connect(db)
    init_schema(conn)
    conn.execute("INSERT INTO leads(no, company_en, country) VALUES (1,'Alpha AV','USA')")
    conn.commit()
    conn.close()
    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    return TestClient(main.app)


def test_activity_crud_filters_and_stats(tmp_path):
    client = _client(tmp_path)
    created = client.post("/api/activities", json={
        "lead_no": 1,
        "title": "Send P2.5 quote",
        "type": "quote",
        "due_at": "2026-08-04",
        "priority": "high",
    })
    assert created.status_code == 200
    activity_id = created.json()["id"]
    assert client.get("/api/activities?lead_no=1").json()[0]["id"] == activity_id
    assert client.get("/api/activities/stats").json()["open_count"] == 1

    changed = client.patch(
        f"/api/activities/{activity_id}", json={"title": "Send revised quote"})
    assert changed.status_code == 200 and changed.json()["title"] == "Send revised quote"
    done = client.post(f"/api/activities/{activity_id}/complete")
    assert done.status_code == 200 and done.json()["status"] == "done"
    assert client.get("/api/activities?lead_no=1").json() == []


def test_activity_get_does_not_run_ownership_backfill(tmp_path, monkeypatch):
    client = _client(tmp_path)
    created = client.post("/api/activities", json={"lead_no": 1, "title": "Human task"})
    assert created.status_code == 200

    def forbidden_write(_conn):
        raise AssertionError("GET /api/activities must not run ownership backfill")

    monkeypatch.setattr(task_ownership, "backfill", forbidden_write)
    listing = client.get("/api/activities?work_owner=human")
    stats = client.get("/api/activities/stats?work_owner=human")
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert stats.status_code == 200
    assert stats.json()["open_count"] == 1


def test_activity_api_validation_and_not_found(tmp_path):
    client = _client(tmp_path)
    bad = client.post("/api/activities", json={"lead_no": 1, "title": "", "type": "magic"})
    assert bad.status_code == 400
    assert client.patch("/api/activities/999", json={"title": "x"}).status_code == 404
    assert client.post("/api/activities/999/complete").status_code == 404
