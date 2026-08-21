import datetime as dt

import pytest

from app import runtime
from app.db import connect, init_schema


BASE = dt.datetime(2026, 8, 21, 6, 0, tzinfo=dt.UTC)


def _db(tmp_path):
    path = str(tmp_path / "runtime.db")
    conn = connect(path)
    init_schema(conn)
    runtime.ensure_schema(conn)
    return path, conn


def test_only_one_live_owner_can_hold_sales_operator_lease(tmp_path):
    _, conn = _db(tmp_path)
    assert runtime.acquire(conn, owner="worker-a", mode="worker", now=BASE, ttl_seconds=120)
    assert not runtime.acquire(
        conn, owner="worker-b", mode="embedded",
        now=BASE + dt.timedelta(seconds=30), ttl_seconds=120,
    )
    row = conn.execute("SELECT owner, mode FROM runtime_leases WHERE name=?",
                       (runtime.LEASE_NAME,)).fetchone()
    assert row["owner"] == "worker-a" and row["mode"] == "worker"


def test_expired_lease_can_be_taken_over(tmp_path):
    _, conn = _db(tmp_path)
    assert runtime.acquire(conn, owner="old", mode="embedded", now=BASE, ttl_seconds=60)
    assert runtime.acquire(
        conn, owner="new", mode="worker",
        now=BASE + dt.timedelta(seconds=61), ttl_seconds=60,
    )
    assert runtime.status(conn, now=BASE + dt.timedelta(seconds=61))["lease"]["owner"] == "new"


def test_same_owner_renews_without_resetting_acquired_at(tmp_path):
    _, conn = _db(tmp_path)
    runtime.acquire(conn, owner="same", mode="worker", now=BASE, ttl_seconds=120)
    before = runtime.status(conn, now=BASE)["lease"]
    runtime.acquire(
        conn, owner="same", mode="worker",
        now=BASE + dt.timedelta(seconds=45), ttl_seconds=120,
    )
    after = runtime.status(conn, now=BASE + dt.timedelta(seconds=45))["lease"]
    assert after["acquired_at"] == before["acquired_at"]
    assert after["heartbeat_at"] != before["heartbeat_at"]


def test_release_allows_immediate_handoff(tmp_path):
    _, conn = _db(tmp_path)
    runtime.acquire(conn, owner="a", mode="embedded", now=BASE)
    assert runtime.release(conn, owner="a") is True
    assert runtime.acquire(conn, owner="b", mode="worker", now=BASE + dt.timedelta(seconds=1))


def test_runtime_status_reports_active_and_expired_heartbeat(tmp_path):
    _, conn = _db(tmp_path)
    runtime.acquire(conn, owner="a", mode="worker", now=BASE, ttl_seconds=120)
    live = runtime.status(conn, now=BASE + dt.timedelta(seconds=20))
    assert live["active"] is True
    assert live["heartbeat_age_seconds"] == 20
    expired = runtime.status(conn, now=BASE + dt.timedelta(seconds=121))
    assert expired["active"] is False


def test_leased_cycle_records_success_and_keeps_lease(tmp_path):
    path, conn = _db(tmp_path)
    result = runtime.run_leased_cycle(
        path, lambda: True, owner="worker-a", mode="worker", ttl_seconds=120)
    assert result["acquired"] is True
    assert result["cycle_ok"] is True and result["email_poll_ok"] is True
    state = runtime.status(conn)["state"]
    assert state["cycle_count"] == 1
    assert state["last_cycle_ok"] == 1
    assert state["last_email_poll_ok"] == 1
    assert runtime.status(conn)["lease"]["owner"] == "worker-a"


def test_mail_poll_failure_is_degraded_health_not_dead_worker(tmp_path):
    path, conn = _db(tmp_path)
    result = runtime.run_leased_cycle(
        path, lambda: False, owner="worker-a", mode="worker", ttl_seconds=120)
    assert result["cycle_ok"] is True
    assert result["email_poll_ok"] is False
    state = runtime.status(conn)["state"]
    assert state["last_cycle_ok"] == 1
    assert state["last_email_poll_ok"] == 0
    assert runtime.status(conn)["active"] is True


def test_leased_cycle_records_crash_instead_of_losing_it(tmp_path):
    path, conn = _db(tmp_path)

    def boom():
        raise RuntimeError("broken cycle")

    result = runtime.run_leased_cycle(
        path, boom, owner="worker-a", mode="worker", ttl_seconds=120,
        release_after=True,
    )
    assert result["cycle_ok"] is False
    assert "broken cycle" in result["error"]
    state = runtime.status(conn)["state"]
    assert state["last_cycle_ok"] == 0
    assert state["last_email_poll_ok"] is None
    assert "broken cycle" in state["last_error"]
    assert runtime.status(conn)["lease"] is None


def test_second_leased_cycle_does_not_execute_while_first_owner_is_live(tmp_path):
    path, conn = _db(tmp_path)
    runtime.acquire(conn, owner="leader", mode="worker", ttl_seconds=120)
    calls = []
    result = runtime.run_leased_cycle(
        path, lambda: calls.append("ran") or True,
        owner="standby", mode="embedded", ttl_seconds=120,
    )
    assert result["acquired"] is False
    assert calls == []


def test_standalone_once_releases_lease_and_records_cycle(monkeypatch, tmp_path):
    from app import main, worker

    path = str(tmp_path / "worker.db")
    conn = connect(path); init_schema(conn); conn.close()
    monkeypatch.setattr(main, "DB_PATH", path)
    monkeypatch.setattr(main, "background_cycle", lambda: True)
    result = worker.run_once(
        db_path=path, owner="once-worker", mode="worker", release_after=True)
    assert result["cycle_ok"] is True
    check = connect(path)
    try:
        status = runtime.status(check)
        assert status["active"] is False
        assert status["lease"] is None
        assert status["state"]["cycle_count"] == 1
    finally:
        check.close()


def test_worker_refuses_to_lease_one_db_and_execute_against_another(monkeypatch, tmp_path):
    from app import main, worker

    path = str(tmp_path / "leased.db")
    monkeypatch.setattr(main, "DB_PATH", str(tmp_path / "different.db"))
    with pytest.raises(RuntimeError, match="DB_PATH"):
        worker.run_once(db_path=path, owner="bad")


def test_sequence_autosend_is_owned_by_background_cycle(monkeypatch, tmp_path):
    from app import autosend, main

    path = str(tmp_path / "autosend.db")
    conn = connect(path); init_schema(conn); conn.close()
    monkeypatch.setattr(main, "DB_PATH", path)
    monkeypatch.setenv("OUTREACH_AUTOSEND_SCHEDULER", "1")
    calls = []
    monkeypatch.setattr(autosend, "should_run", lambda conn: True)
    monkeypatch.setattr(autosend, "run_once",
                        lambda conn, sender, image: calls.append((sender, image)) or {"sent": 0})
    monkeypatch.setattr(main.send_api, "pick_sender", lambda conn: "sender")
    monkeypatch.setattr(main.send_api, "DEFAULT_ATTACHMENT", None)
    main.auto_send_sequences()
    assert calls == [("sender", None)]
