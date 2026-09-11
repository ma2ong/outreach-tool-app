"""Spec 107: a skipped poll must not claim recovery from a real failure."""
import pytest
import datetime as dt
import sqlite3
import threading

from app import runtime
from app.db import connect, init_schema


def snapshot(path):
    conn = connect(path)
    try:
        return runtime.capability_status(conn)[0]
    finally:
        conn.close()


def test_parallel_first_requests_can_upgrade_old_capability_table(tmp_path):
    path = str(tmp_path / "old-health.db")
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE capability_health (name TEXT PRIMARY KEY, updated_at TEXT NOT NULL)"
    )
    conn.commit()
    conn.close()
    barrier = threading.Barrier(6)
    errors = []

    def upgrade():
        local = connect(path)
        try:
            barrier.wait()
            runtime.ensure_schema(local)
        except Exception as exc:  # assertion below reports every concurrent failure
            errors.append(exc)
        finally:
            local.close()

    workers = [threading.Thread(target=upgrade) for _ in range(6)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()

    assert errors == []
    conn = connect(path)
    try:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(capability_health)")]
        assert columns.count("status") == 1
        assert columns.count("running_since") == 1
    finally:
        conn.close()


@pytest.mark.parametrize("status", ["disabled", "not_configured", "idle"])
def test_skipped_work_does_not_clear_failure_or_claim_success(tmp_path, status):
    path = str(tmp_path / "health.db")
    conn = connect(path)
    init_schema(conn)
    conn.close()
    runtime.run_capability(path, "email_poll", lambda: False)
    before = snapshot(path)
    result = runtime.run_capability(path, "email_poll", lambda: {"status": status})
    after = snapshot(path)
    assert result["status"] == status
    assert after["last_error"] == before["last_error"]
    assert after["consecutive_failures"] == 1
    assert after["last_success_at"] is None
    assert after["last_attempt_at"] == before["last_attempt_at"]
    assert after["status"] == status


def test_partial_work_records_failure_and_successful_output(tmp_path):
    path = str(tmp_path / "health.db")
    result = runtime.run_capability(path, "website_recheck", lambda: {
        "processed": 17, "failed": 3, "errors": ["three sites timed out"],
    })
    assert result["ok"] is False
    assert result["status"] == "partial"
    after = snapshot(path)
    assert after["processed_count"] == 17
    assert after["last_output_at"] is not None
    assert after["last_success_at"] is None
    assert after["consecutive_failures"] == 1
    assert "timed out" in after["last_error"]


def test_actual_success_clears_failure(tmp_path):
    path = str(tmp_path / "health.db")
    runtime.run_capability(path, "email_poll", lambda: False)
    runtime.run_capability(path, "email_poll", lambda: {"processed": 2})
    after = snapshot(path)
    assert after["status"] == "succeeded"
    assert after["last_error"] is None
    assert after["consecutive_failures"] == 0


def test_running_is_visible_without_claiming_completion(tmp_path):
    path = str(tmp_path / "health.db")
    def work():
        during = snapshot(path)
        assert during["status"] == "running"
        assert during["running_since"] is not None
        assert during["last_success_at"] is None
        return {"status": "idle"}
    assert runtime.run_capability(path, "email_poll", work)["ok"]
    assert snapshot(path)["running_since"] is None


def test_overdue_running_job_is_observed_not_retried(tmp_path):
    path = str(tmp_path / "health.db")
    started = dt.datetime(2026, 9, 8, tzinfo=dt.UTC)
    runtime._capability_write(path, "email_send", success=None, now=started)
    conn = connect(path)
    try:
        row = runtime.capability_status(conn, now=started + dt.timedelta(minutes=21))[0]
        assert row["status"] == "stalled"
        assert row["consecutive_failures"] == 0
        assert conn.execute("SELECT status FROM capability_health").fetchone()[0] == "running"
    finally:
        conn.close()
