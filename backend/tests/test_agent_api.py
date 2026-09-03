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
    # docs/93 起多了 hook 这一档：写开场白的模型和分类走同一条便宜后端
    assert set(body["llm"]["tasks"]) == {"classify", "draft", "hook"}
    assert body["llm"]["tasks"]["hook"]["backend"] == "deepseek"
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
    assert approved.json()["proposal"]["status"] == "approved"   # execution is queued
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


def test_the_sales_mission_is_readable_and_safely_updateable(tmp_path):
    client, _ = _client(tmp_path)
    current = client.get("/api/agent/mission").json()
    assert current["target_markets"] == ["USA", "South Korea"]
    assert current["minimum_fit_score"] == 75

    changed = client.put("/api/agent/mission", json={
        "target_markets": ["Brazil", "Brazil", "UK"],
        "daily_qualified_leads": 6,
        "minimum_fit_score": 10,
        "auto_enroll": False,
    }).json()
    assert changed == {
        "target_markets": ["Brazil", "UK"],
        "daily_qualified_leads": 6,
        "minimum_fit_score": 75,
        "auto_enroll": False,
    }
    status = client.get("/api/agent/status").json()
    assert status["mission"] == changed
    assert status["mission_progress"]["daily_target"] == 6


def test_conversation_takeover_and_resume_are_explicit_api_actions(tmp_path):
    client, _ = _client(tmp_path)
    taken = client.post("/api/agent/conversations/1/email/takeover",
                        json={"reason": "strategic negotiation"})
    assert taken.status_code == 200 and taken.json()["owner"] == "allen"
    status = client.get("/api/agent/status").json()
    assert status["takeovers"][0]["company_en"] == "Alpha AV"

    resumed = client.post("/api/agent/conversations/1/email/resume")
    assert resumed.status_code == 200 and resumed.json()["owner"] == "agent"
    assert client.get("/api/agent/status").json()["takeovers"] == []
    assert client.post("/api/agent/conversations/1/sms/takeover", json={}).status_code == 400


def test_the_backend_for_a_task_is_switchable(tmp_path):
    client, _ = _client(tmp_path)
    body = client.post("/api/agent/backend",
                       json={"task": "classify", "backend": "cli"}).json()
    assert body["tasks"]["classify"]["backend"] == "cli"
    assert client.post("/api/agent/backend",
                       json={"task": "classify", "backend": "gpt"}).status_code == 400

# ------------------------------------------------- Spec 31: execution leaves the request

def test_approving_returns_a_job_instead_of_waiting_for_the_work(tmp_path):
    """discover_run ran inside the request for 3m08s and the tunnel cut it off."""
    client, db = _client(tmp_path)
    conn = connect(db)
    from app.agent import proposals
    p = proposals.create(conn, "create_task", lead_no=1, title="打个电话",
                         payload={"title": "打个电话", "due_at": "2026-09-01"})
    conn.close()
    body = client.post(f"/api/agent/proposals/{p['id']}/approve", json={}).json()
    assert body["job_id"]
    assert body["proposal"]["status"] == "approved"
    job = client.get(f"/api/agent/proposals/job/{body['job_id']}")
    assert job.status_code == 200 and job.json()["status"] in ("running", "done")


def test_a_second_click_cannot_execute_the_same_proposal(tmp_path):
    client, db = _client(tmp_path)
    conn = connect(db)
    from app.agent import proposals
    p = proposals.create(conn, "create_task", lead_no=1, title="只做一次",
                         payload={"title": "只做一次"})
    conn.close()
    assert client.post(f"/api/agent/proposals/{p['id']}/approve", json={}).status_code == 200
    again = client.post(f"/api/agent/proposals/{p['id']}/approve", json={})
    assert again.status_code == 400      # no longer pending: the race cannot double-run


def test_an_in_flight_proposal_still_shows_in_the_pending_list(tmp_path):
    client, db = _client(tmp_path)
    conn = connect(db)
    from app.agent import proposals
    p = proposals.create(conn, "create_task", lead_no=1, title="执行中的", payload={})
    proposals.mark_approved(conn, p["id"])
    conn.close()
    listed = client.get("/api/agent/proposals?status=pending").json()
    assert [x["id"] for x in listed] == [p["id"]]   # three minutes is not a blank screen
    assert listed[0]["status"] == "approved"


def test_a_restart_does_not_leave_a_proposal_executing_forever(tmp_path):
    """The background task dies with the process; the row would say 执行中 for good."""
    client, db = _client(tmp_path)
    conn = connect(db)
    from app.agent import proposals
    p = proposals.create(conn, "create_task", lead_no=1, title="重启前批准的", payload={})
    proposals.mark_approved(conn, p["id"])
    assert proposals.fail_interrupted(conn) == 1
    after = proposals.get(conn, p["id"])
    conn.close()
    assert after["status"] == "failed" and "重启" in after["execution_result"]


def test_allen_can_write_and_retire_a_customer_memory(tmp_path):
    """The rule that the agent may never edit Allen's memory needs a way for him to
    write one in the first place."""
    client, _ = _client(tmp_path)
    written = client.post("/api/agent/memory/1",
                          json={"content": "老板不喜欢被追，等他主动。", "kind": "profile"})
    assert written.status_code == 200
    item = written.json()
    assert item["origin"] == "explicit"

    stored = client.get("/api/agent/memory/1").json()
    assert [i["content"] for i in stored["items"]] == ["老板不喜欢被追，等他主动。"]
    assert "老板不喜欢被追" in stored["summary"]

    assert client.delete(f"/api/agent/memory/1/{item['id']}").status_code == 200
    assert client.get("/api/agent/memory/1").json()["items"] == []
    assert client.delete(f"/api/agent/memory/1/{item['id']}").status_code == 404


def test_empty_memory_is_refused(tmp_path):
    client, _ = _client(tmp_path)
    assert client.post("/api/agent/memory/1", json={"content": "   "}).status_code == 400
