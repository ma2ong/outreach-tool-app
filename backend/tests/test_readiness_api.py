import app.main as main
from app.db import connect, init_schema
from fastapi.testclient import TestClient


def _client(tmp_path, monkeypatch):
    db = str(tmp_path / "t.db")
    conn = connect(db)
    init_schema(conn)
    conn.executescript("""
        INSERT INTO leads(no, company_en, email, email_status) VALUES
            (1, 'Alpha', 'a@alpha.com', 'valid'),
            (2, 'Beta', 'b@beta.com', NULL);
        INSERT INTO sequences(name, channel, active) VALUES ('Email follow-up', 'email', 1);
        INSERT INTO sequence_steps(sequence_id, step_order, day_offset, body)
            VALUES (1, 0, 0, 'hello');
        INSERT INTO sequence_enrollments(lead_no, sequence_id, current_step, status, next_due_date)
            VALUES (1, 1, 0, 'active', '2026-07-01');
    """)
    conn.commit()
    conn.close()
    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    monkeypatch.setattr("app.readiness.get_password", lambda: "")
    monkeypatch.setattr("app.api.autosend.get_password", lambda: "")
    return TestClient(main.app)


def test_readiness_reports_blocker_without_exposing_secrets(tmp_path, monkeypatch):
    body = _client(tmp_path, monkeypatch).get("/api/readiness").json()
    assert body["status"] == "blocked"
    assert body["metrics"]["email_verified_coverage"] == 50
    assert body["metrics"]["autosend"]["enabled"] is False
    assert body["metrics"]["autosend"]["preview"]["due"] == 1
    assert body["metrics"]["pending_replies"] == 0
    assert body["metrics"]["activities"]["open_count"] == 0
    assert next(c for c in body["checks"] if c["id"] == "sales_activities")["action_page"] == "activities"
    assert "password" not in str(body).lower()


def test_autosend_enable_requires_mailbox_and_has_preview(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    r = client.patch("/api/autosend", json={"enabled": True})
    assert r.status_code == 400
    client.post("/api/mailboxes", json={
        "email": "sales@x.com", "smtp_host": "smtp.x.com",
        "imap_host": "imap.x.com", "username": "sales@x.com", "password": "secret",
    })
    enabled = client.patch("/api/autosend", json={"enabled": True}).json()
    assert enabled["enabled"] is True
    assert enabled["preview"]["will_send"] == 1


def test_resuming_after_a_safety_pause_requires_explicit_risk_acknowledgement(
        tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    client.post("/api/mailboxes", json={
        "email": "sales@x.com", "smtp_host": "smtp.x.com",
        "imap_host": "imap.x.com", "username": "sales@x.com", "password": "secret",
    })
    pause = {"code": "bounce_rate", "reason": "退信率 11.4% 超过安全线"}
    monkeypatch.setattr("app.api.autosend.autosend.safety_pause", lambda conn: pause)

    blocked = client.patch("/api/autosend", json={"enabled": True})
    assert blocked.status_code == 409 and "确认" in blocked.json()["detail"]
    resumed = client.patch("/api/autosend", json={
        "enabled": True, "acknowledge_safety_risk": True,
    })
    assert resumed.status_code == 200 and resumed.json()["enabled"] is True
