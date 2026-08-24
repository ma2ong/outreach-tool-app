import datetime as dt
import os

from app import backup, production_health, runtime
from app.db import connect, init_schema


def _db(path):
    conn = connect(str(path))
    init_schema(conn)
    conn.execute("INSERT INTO leads(no, company_en, country) VALUES (1, 'Backup Buyer', 'USA')")
    conn.commit()
    conn.close()


def test_daily_backup_is_verified_and_idempotent(tmp_path):
    db = tmp_path / "outreach.db"
    _db(db)
    today = dt.date(2026, 8, 24)

    first = backup.ensure_daily_backup(str(db), today=today)
    second = backup.ensure_daily_backup(str(db), today=today)

    assert first["created"] is True
    assert first["verified"] is True
    assert os.path.isfile(first["path"])
    assert backup.quick_check(first["path"]) == (True, "ok")
    assert second["created"] is False
    assert second["path"] == first["path"]
    assert second["verified"] is True


def test_corrupt_daily_backup_is_quarantined_and_rebuilt(tmp_path):
    db = tmp_path / "outreach.db"
    _db(db)
    today = dt.date(2026, 8, 24)
    first = backup.ensure_daily_backup(str(db), today=today)

    with open(first["path"], "wb") as fh:
        fh.write(b"definitely not sqlite")
    backup._quick_check_cached.cache_clear()

    rebuilt = backup.ensure_daily_backup(str(db), today=today)

    assert rebuilt["created"] is True
    assert rebuilt["verified"] is True
    assert rebuilt["quarantined"] is not None
    assert os.path.isfile(rebuilt["quarantined"])
    assert backup.quick_check(rebuilt["path"]) == (True, "ok")


def test_runtime_refuses_unattended_cycle_when_backup_fails(tmp_path, monkeypatch):
    db = tmp_path / "outreach.db"
    _db(db)
    called = []

    def fail_backup(*_args, **_kwargs):
        raise backup.BackupError("disk full")

    monkeypatch.setattr(backup, "ensure_daily_backup", fail_backup)

    result = runtime.run_leased_cycle(
        str(db), lambda: called.append(True) or True,
        owner="worker:test", mode="worker", release_after=True,
    )

    assert called == []
    assert result["acquired"] is True
    assert result["cycle_ok"] is False
    assert "BackupError" in (result["error"] or "")

    conn = connect(str(db))
    try:
        state = runtime.status(conn)["state"]
        assert state["last_cycle_ok"] == 0
        assert "BackupError" in (state["last_error"] or "")
    finally:
        conn.close()


def test_runtime_creates_backup_before_running_cycle(tmp_path):
    db = tmp_path / "outreach.db"
    _db(db)
    seen = []

    result = runtime.run_leased_cycle(
        str(db), lambda: seen.append(backup.status(str(db))["verified"]) or True,
        owner="worker:test-ok", mode="worker", release_after=True,
    )

    assert result["cycle_ok"] is True
    assert seen == [True]
    assert result["backup"]["verified"] is True


def test_db_health_quick_check_is_throttled_for_file_db(tmp_path, monkeypatch):
    db = tmp_path / "outreach.db"
    _db(db)
    conn = connect(str(db))
    production_health._DB_CHECK_CACHE.clear()
    calls = []
    original = production_health._run_db_quick_check

    def counted(current):
        calls.append(True)
        return original(current)

    monkeypatch.setattr(production_health, "_run_db_quick_check", counted)
    monkeypatch.setattr(production_health.time, "monotonic", lambda: 100.0)
    try:
        first = production_health._db_status(conn)
        second = production_health._db_status(conn)
        monkeypatch.setattr(production_health.time, "monotonic", lambda: 161.0)
        third = production_health._db_status(conn)
    finally:
        conn.close()
        production_health._DB_CHECK_CACHE.clear()

    assert first["status"] == second["status"] == third["status"] == "ok"
    assert len(calls) == 2  # first request + one refresh after the 60-second TTL


def test_production_health_marks_missing_backup_critical(tmp_path, monkeypatch):
    db = tmp_path / "outreach.db"
    _db(db)
    conn = connect(str(db))
    production_health._DB_CHECK_CACHE.clear()
    monkeypatch.setattr(
        production_health, "_frontend_status",
        lambda: {"status": "ok", "built": True, "size_bytes": 1},
    )
    monkeypatch.setattr(
        production_health, "_server_log_status",
        lambda: {"status": "ok", "last_crash_unrecovered": False,
                 "last_crash_mtime": None, "last_start_mtime": None},
    )
    monkeypatch.setattr(
        production_health, "_disk_status",
        lambda _path: {"status": "ok", "free_bytes": 2_000_000_000,
                       "total_bytes": 4_000_000_000},
    )
    try:
        health = production_health.status(conn, str(db))
    finally:
        conn.close()
        production_health._DB_CHECK_CACHE.clear()

    assert health["database"]["status"] == "ok"
    assert health["backup"]["status"] == "missing"
    assert health["status"] == "critical"
    assert any("备份" in item for item in health["critical"])


def test_production_health_is_ok_with_verified_today_backup(tmp_path, monkeypatch):
    db = tmp_path / "outreach.db"
    _db(db)
    backup.ensure_daily_backup(str(db))
    conn = connect(str(db))
    production_health._DB_CHECK_CACHE.clear()
    monkeypatch.setattr(
        production_health, "_frontend_status",
        lambda: {"status": "ok", "built": True, "size_bytes": 1},
    )
    monkeypatch.setattr(
        production_health, "_server_log_status",
        lambda: {"status": "ok", "last_crash_unrecovered": False,
                 "last_crash_mtime": None, "last_start_mtime": None},
    )
    monkeypatch.setattr(
        production_health, "_disk_status",
        lambda _path: {"status": "ok", "free_bytes": 2_000_000_000,
                       "total_bytes": 4_000_000_000},
    )
    try:
        health = production_health.status(conn, str(db))
    finally:
        conn.close()
        production_health._DB_CHECK_CACHE.clear()

    assert health["status"] == "ok"
    assert health["backup"]["verified"] is True
    assert health["critical"] == []
