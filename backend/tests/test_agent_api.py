import app.main as main
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
    return TestClient(main.app), db


def test_status_reports_what_the_agent_can_and_cannot_do(tmp_path):
    client, _ = _client(tmp_path)
    body = client.get("/api/agent/status").json()
    assert body["pending"] == 0
    assert body["autonomy"]["reply_draft"] == "propose"
    assert set(body["llm"]["tasks"]) == {"classify", "draft"}
    assert body["llm"]["tasks"]["classify"]["backend"] == "deepseek"


def test_meta_gives_the_ui_its_vocabulary(tmp_path):
    client, _ = _client(tmp_path)
    meta = client.get("/api/agent/meta").json()
    assert "reply_draft" in meta["kinds"]
    assert meta["autonomy"] == ["off", "propose", "auto"]
    assert "wrong_intent" in meta["reject_reasons"]
    assert "negotiation" in meta["intents"]


def test_approving_a_task_proposal_creates_the_task(tmp_path):
    client, db = _client(tmp_path)
    conn = connect(db)
    from app.agent import proposals
    p = proposals.create(conn, "create_task", lead_no=1, title="Call them",
                         payload={"title": "Call them", "due_at": "2026-09-01"})
    conn.close()
    assert client.get("/api/agent/proposals").json()[0]["id"] == p["id"]
    approved = client.post(f"/api/agent/proposals/{p['id']}/approve", json={})
    assert approved.status_code == 200
    assert approved.json()["status"] == "executed"
    assert client.get("/api/activities?lead_no=1").json()[0]["title"] == "Call them"


def test_rejecting_needs_a_reason_the_api_recognises(tmp_path):
    client, db = _client(tmp_path)
    conn = connect(db)
    from app.agent import proposals
    p = proposals.create(conn, "create_task", lead_no=1, title="x", payload={})
    conn.close()
    assert client.post(f"/api/agent/proposals/{p['id']}/reject",
                       json={"reason": "made up"}).status_code == 400
    ok = client.post(f"/api/agent/proposals/{p['id']}/reject",
                     json={"reason": "not_worth_it", "note": "小客户"})
    assert ok.json()["status"] == "rejected"
    assert client.get("/api/agent/proposals").json() == []


def test_the_autonomy_dial_is_settable_per_kind(tmp_path):
    client, _ = _client(tmp_path)
    body = client.post("/api/agent/autonomy",
                       json={"kind": "create_task", "level": "auto"}).json()
    assert body["autonomy"]["create_task"] == "auto"
    assert body["autonomy"]["reply_draft"] == "propose"
    assert client.post("/api/agent/autonomy",
                       json={"kind": "create_task", "level": "sometimes"}).status_code == 400


def test_the_backend_for_a_task_is_switchable(tmp_path):
    client, _ = _client(tmp_path)
    body = client.post("/api/agent/backend",
                       json={"task": "classify", "backend": "cli"}).json()
    assert body["tasks"]["classify"]["backend"] == "cli"
    assert client.post("/api/agent/backend",
                       json={"task": "classify", "backend": "gpt"}).status_code == 400
