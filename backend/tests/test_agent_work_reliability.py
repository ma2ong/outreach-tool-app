import datetime as dt

from app.agent import task_ownership, work_reliability
from app.db import (
    DB_BUSY_TIMEOUT_MS,
    WAL_AUTOCHECKPOINT_PAGES,
    connect,
    init_schema,
)


def _agent_task(conn, *, due_at: str) -> int:
    now = dt.datetime.now(dt.UTC).isoformat()
    conn.execute("INSERT INTO leads(no,company_en,country) VALUES (1,'Queue AV','USA')")
    task_ownership.ensure_schema(conn)
    cur = conn.execute(
        "INSERT INTO activities("
        "lead_no,type,title,due_at,priority,status,source,source_ref,created_at,updated_at,work_owner"
        ") VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (1, "task", "Agent research", due_at, "normal", "open", "agent",
         "proposal:1", now, now, "agent"),
    )
    conn.commit()
    return int(cur.lastrowid)


def test_every_file_connection_uses_wal_concurrency_profile(tmp_path):
    db = str(tmp_path / "wal.db")
    first = connect(db)
    init_schema(first)
    second = connect(db)
    try:
        assert first.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert second.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert second.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert second.execute("PRAGMA busy_timeout").fetchone()[0] == DB_BUSY_TIMEOUT_MS
        assert second.execute("PRAGMA synchronous").fetchone()[0] == 1  # NORMAL
        assert second.execute("PRAGMA wal_autocheckpoint").fetchone()[0] == WAL_AUTOCHECKPOINT_PAGES
    finally:
        second.close()
        first.close()


def test_agent_work_failure_backoff_and_queue_health(tmp_path):
    db = str(tmp_path / "queue.db")
    conn = connect(db)
    init_schema(conn)
    today = dt.date(2026, 8, 25)
    activity_id = _agent_task(conn, due_at="2026-08-10")

    failures, delay = work_reliability.next_failure_delay(conn, activity_id)
    assert (failures, delay) == (1, 3)
    work_reliability.record_attempt(conn, activity_id, "retry", error="website timeout")

    failures, delay = work_reliability.next_failure_delay(conn, activity_id)
    assert (failures, delay) == (2, 7)
    work_reliability.record_attempt(conn, activity_id, "retry", error="website timeout again")

    health = work_reliability.queue_health(conn, today=today)
    assert health["open"] == 1
    assert health["due"] == 1
    assert health["stale"] == 1
    assert health["repeated_failures"] == 1

    work_reliability.record_attempt(conn, activity_id, "rescheduled")
    assert work_reliability.state(conn, activity_id)["consecutive_failures"] == 0
    assert work_reliability.queue_health(conn, today=today)["repeated_failures"] == 0
    conn.close()


def test_last_sweep_is_visible_without_mutating_queue_read(tmp_path):
    db = str(tmp_path / "sweep.db")
    conn = connect(db)
    init_schema(conn)
    work_reliability.save_sweep(conn, {
        "processed": 6,
        "done": 4,
        "rescheduled": 1,
        "failed": 1,
        "materialized": {"executed": 2, "failed": 0},
    })

    health = work_reliability.queue_health(conn, today=dt.date(2026, 8, 25))
    assert health["last_sweep"]["processed"] == 6
    assert health["last_sweep"]["done"] == 4
    assert health["last_sweep"]["failed"] == 1
    conn.close()
