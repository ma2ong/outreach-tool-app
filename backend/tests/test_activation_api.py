import app.main as main
from app import mailboxes, settings
from app.agent import mission, proposals
from app.db import connect, init_schema
from fastapi.testclient import TestClient


def _client(tmp_path):
    db = str(tmp_path / "activation.db")
    conn = connect(db)
    init_schema(conn)
    conn.close()
    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    return TestClient(main.app), db


def test_activation_progress_comes_from_real_configuration(tmp_path):
    client, db = _client(tmp_path)
    initial = client.get("/api/activation").json()
    assert initial["prepared"] is False
    assert initial["completed"] == 0
    assert initial["worker"]["active"] is False
    assert initial["worker"]["last_cycle_ok"] is None
    assert [step["id"] for step in initial["steps"]] == [
        "mission", "mailbox", "knowledge", "plan", "autonomy"]

    conn = connect(db)
    mission.set_mission(conn, {
        "target_markets": ["USA"], "daily_qualified_leads": 5,
        "minimum_fit_score": 80, "auto_enroll": True,
    })
    mailbox_id = mailboxes.add_mailbox(
        conn, "sales@example.com", "smtp.example.com", 465,
        "sales@example.com", "secret", 20, "imap.example.com", 993, True)
    settings.set_value(conn, f"mailbox_test_success:{mailbox_id}", "2026-09-10T09:00:00+08:00")
    conn.execute(
        "INSERT INTO products(model,pixel_pitch,agent_approved) VALUES ('MX-P2.5','P2.5',1)")
    conn.commit()
    conn.close()

    client.post("/api/activation/acknowledge", json={"step": "plan"})
    client.post("/api/activation/acknowledge", json={"step": "autonomy"})
    done = client.get("/api/activation").json()
    assert done["prepared"] is True
    assert done["completed"] == done["total"] == 5


def test_activation_preview_and_review_never_raise_autonomy(tmp_path):
    client, db = _client(tmp_path)
    conn = connect(db)
    before = proposals.autonomy_map(conn)
    conn.close()

    preview = client.get("/api/activation/preview").json()
    assert "pricing" in preview["allen_owns"]
    response = client.post("/api/activation/acknowledge", json={"step": "autonomy"})
    assert response.status_code == 200

    conn = connect(db)
    assert proposals.autonomy_map(conn) == before
    conn.close()


def test_only_review_steps_can_be_acknowledged(tmp_path):
    client, _ = _client(tmp_path)
    response = client.post("/api/activation/acknowledge", json={"step": "mailbox"})
    assert response.status_code == 400


def test_successful_mailbox_test_is_recorded_and_password_change_invalidates_it(tmp_path,
                                                                                 monkeypatch):
    client, db = _client(tmp_path)
    conn = connect(db)
    mailbox_id = mailboxes.add_mailbox(
        conn, "sales@example.com", "smtp.example.com", 465,
        "sales@example.com", "secret", 20, "imap.example.com", 993, True)
    conn.close()
    monkeypatch.setattr("app.channels.email_adapter.test_mailbox", lambda _box: None)
    monkeypatch.setattr("app.replies.test_mailbox", lambda _box: None)

    assert client.post(f"/api/mailboxes/{mailbox_id}/test").status_code == 200
    assert client.get("/api/activation").json()["steps"][1]["complete"] is True
    assert client.put(
        f"/api/mailboxes/{mailbox_id}/password", json={"password": "new-secret"}
    ).status_code == 200
    assert client.get("/api/activation").json()["steps"][1]["complete"] is False
