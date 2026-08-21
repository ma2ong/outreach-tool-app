import datetime as dt

from fastapi.testclient import TestClient

import app.main as main
from app import runtime
from app.db import connect, init_schema


NOW = dt.datetime(2026, 8, 21, 6, 30, tzinfo=dt.UTC)


def _client(tmp_path):
    db = str(tmp_path / "runtime-api.db")
    conn = connect(db)
    init_schema(conn)
    runtime.ensure_schema(conn)
    conn.close()
    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    return db, TestClient(main.app)


def test_runtime_status_exposes_active_worker_without_secrets(tmp_path, monkeypatch):
    db, client = _client(tmp_path)
    conn = connect(db)
    try:
        runtime.acquire(conn, owner="worker:test-host:123:abc", mode="worker",
                        ttl_seconds=120, now=NOW)
        runtime.record_start(conn, owner="worker:test-host:123:abc", mode="worker", now=NOW)
        runtime.record_finish(conn, ok=True, error=None,
                              owner="worker:test-host:123:abc", mode="worker", now=NOW)
    finally:
        conn.close()
    monkeypatch.setattr(runtime, "utcnow", lambda: NOW + dt.timedelta(seconds=20))
    monkeypatch.setenv("OUTREACH_EMBEDDED_WORKER", "0")

    try:
        response = client.get("/api/runtime/status")
        assert response.status_code == 200
        body = response.json()
        assert body["active"] is True
        assert body["lease"]["mode"] == "worker"
        assert body["heartbeat_age_seconds"] == 20
        assert body["state"]["cycle_count"] == 1
        assert body["state"]["last_cycle_ok"] == 1
        assert body["embedded_worker_enabled"] is False
        assert body["dedicated_worker_expected"] is True
        assert "password" not in str(body).lower()
    finally:
        main.app.dependency_overrides.pop(main.get_conn, None)


def test_runtime_status_makes_missing_dedicated_worker_visible(tmp_path, monkeypatch):
    _db, client = _client(tmp_path)
    monkeypatch.setenv("OUTREACH_EMBEDDED_WORKER", "0")
    try:
        body = client.get("/api/runtime/status").json()
        assert body["active"] is False
        assert body["lease"] is None
        assert body["state"] is None
        assert body["dedicated_worker_expected"] is True
    finally:
        main.app.dependency_overrides.pop(main.get_conn, None)
