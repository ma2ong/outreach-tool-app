import datetime as dt
import threading

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
    standby = runtime.status(conn)["state"]
    assert standby["standby_count"] == 1
    assert standby["last_standby_owner"] == "standby"


def test_background_stage_failure_is_visible_in_the_runtime_record(monkeypatch, tmp_path):
    from app import background_jobs

    path, conn = _db(tmp_path)
    monkeypatch.setattr(background_jobs, "email_poll", lambda _p: True)
    monkeypatch.setattr(background_jobs, "social_scan", lambda _p: False)
    monkeypatch.setattr(background_jobs, "website_recheck", lambda _p: True)
    monkeypatch.setattr(background_jobs, "sequence_maintenance", lambda _p: True)
    monkeypatch.setattr(background_jobs, "email_send", lambda _p: True)
    monkeypatch.setattr(background_jobs, "social_send", lambda _p: True)
    monkeypatch.setattr(background_jobs, "agent", lambda _p: True)
    monkeypatch.setattr(background_jobs, "contact_names", lambda _p: True)

    result = runtime.run_leased_cycle(path, lambda: background_jobs.run_cycle(path),
                                      owner="worker-a", mode="worker")
    assert result["cycle_ok"] is False
    assert "social_scan" in result["error"]
    assert runtime.status(conn)["state"]["last_cycle_ok"] == 0
    capability = {row["name"]: row for row in runtime.capability_status(conn)}["social_scan"]
    assert capability["consecutive_failures"] == 1
    assert "reported failure" in capability["last_error"]


def test_capability_failure_does_not_stop_the_following_stage(monkeypatch, tmp_path):
    from app import background_jobs

    path, _conn = _db(tmp_path)
    called = []
    monkeypatch.setattr(background_jobs, "email_poll", lambda _p: (_ for _ in ()).throw(RuntimeError("imap down")))
    monkeypatch.setattr(background_jobs, "social_scan", lambda _p: called.append("social") or True)
    monkeypatch.setattr(background_jobs, "website_recheck", lambda _p: True)
    monkeypatch.setattr(background_jobs, "sequence_maintenance", lambda _p: True)
    monkeypatch.setattr(background_jobs, "email_send", lambda _p: True)
    monkeypatch.setattr(background_jobs, "social_send", lambda _p: True)
    monkeypatch.setattr(background_jobs, "agent", lambda _p: True)
    monkeypatch.setattr(background_jobs, "contact_names", lambda _p: True)

    with pytest.raises(RuntimeError, match="imap down"):
        background_jobs.run_cycle(path)
    assert called == ["social"]


def test_agent_job_propagates_decision_maker_search_failures(monkeypatch, tmp_path):
    from app import background_jobs, decision_maker_radar
    from app.agent import account_brain, catchup, opportunity_coach, run

    path, _conn = _db(tmp_path)
    monkeypatch.setenv("OUTREACH_AGENT", "1")
    monkeypatch.setenv("OUTREACH_AUTO_RESEARCH", "1")
    monkeypatch.setattr(run, "run_once", lambda _conn: {"processed": 1, "errors": []})
    monkeypatch.setattr(catchup, "run_if_due", lambda _conn: None)
    monkeypatch.setattr(account_brain, "safety_net", lambda _conn: None)
    monkeypatch.setattr(opportunity_coach, "safety_net", lambda _conn: None)
    monkeypatch.setattr(decision_maker_radar, "sweep", lambda _conn: {
        "checked": 1, "promoted": 0, "proposed": 0,
        "errors": ["lead #1: search offline"],
    })

    result = background_jobs.agent(path)
    assert result["errors"] == ["lead #1: search offline"]
    observed = runtime.run_capability(path, "agent", lambda: result)
    assert observed["status"] == "partial"
    assert observed["processed_count"] == 1


def test_stalled_stage_does_not_block_or_duplicate_and_final_result_is_collected(tmp_path):
    from app import scheduler

    path, conn = _db(tmp_path)
    release = threading.Event()
    started = threading.Event()
    finished = threading.Event()
    calls = []

    def stuck():
        calls.append("stuck")
        started.set()
        release.wait(2)
        finished.set()
        return {"processed": 3}

    later = []
    with pytest.raises(RuntimeError, match="stalled"):
        scheduler.run_cycle(
            path, (("stuck", stuck), ("later", lambda: later.append(1) or True)),
            deadlines={"stuck": 0.02, "later": 1},
        )
    assert started.is_set() and later == [1]
    health = {row["name"]: row for row in runtime.capability_status(conn)}
    assert health["stuck"]["status"] == "stalled"

    with pytest.raises(RuntimeError, match="stalled"):
        scheduler.run_cycle(
            path, (("stuck", stuck),), deadlines={"stuck": 0.02})
    assert calls == ["stuck"]

    release.set()
    assert finished.wait(1)
    assert scheduler.run_cycle(
        path, (("stuck", stuck),), deadlines={"stuck": 1}) is True
    health = {row["name"]: row for row in runtime.capability_status(conn)}["stuck"]
    assert health["status"] == "succeeded" and health["processed_count"] == 3
    assert calls == ["stuck"]


def test_standalone_once_releases_lease_and_records_cycle(monkeypatch, tmp_path):
    from app import background_jobs, worker

    path = str(tmp_path / "worker.db")
    conn = connect(path); init_schema(conn); conn.close()
    monkeypatch.setattr(background_jobs, "run_cycle", lambda actual: actual == path)
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


def test_worker_executes_cycle_against_the_leased_database(monkeypatch, tmp_path):
    from app import background_jobs, worker

    path = str(tmp_path / "leased.db")
    conn = connect(path); init_schema(conn); conn.close()
    seen = []
    monkeypatch.setattr(background_jobs, "run_cycle", lambda actual: seen.append(actual) or True)
    worker.run_once(db_path=path, owner="same-db")
    assert seen == [path]


def test_sequence_autosend_is_owned_by_background_cycle(monkeypatch, tmp_path):
    from app import autosend, background_jobs
    from app.api import send as send_api

    path = str(tmp_path / "autosend.db")
    conn = connect(path); init_schema(conn); conn.close()
    monkeypatch.setenv("OUTREACH_AUTOSEND_SCHEDULER", "1")
    calls = []
    monkeypatch.setattr(autosend, "should_run", lambda conn: True)
    monkeypatch.setattr(autosend, "run_once",
                        lambda conn, sender, image: calls.append((sender, image)) or {"sent": 0})
    monkeypatch.setattr(send_api, "pick_sender", lambda conn: "sender")
    monkeypatch.setattr(send_api, "DEFAULT_ATTACHMENT", None)
    background_jobs.email_send(path)
    assert calls == [("sender", None)]
