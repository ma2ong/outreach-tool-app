"""Durable reliability state for Agent-owned background work.

This module never turns failed automation into human homework. It only records bounded
attempt metadata, computes retry backoff, and exposes a read-only queue-health snapshot.
"""
from __future__ import annotations

import datetime as dt
import json

from app import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_work_state (
    activity_id INTEGER PRIMARY KEY,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TEXT,
    last_outcome TEXT,
    last_error TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(activity_id) REFERENCES activities(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_agent_work_failures
    ON agent_work_state(consecutive_failures, updated_at);
"""

LAST_SWEEP_KEY = "agent_work_last_sweep"
FAILURE_BACKOFF_DAYS = (3, 7, 14, 30)
STALE_DAYS = 7
REPEATED_FAILURE_THRESHOLD = 2


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def ensure_schema(conn) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def _table_exists(conn, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def _column_exists(conn, table: str, column: str) -> bool:
    if not _table_exists(conn, table):
        return False
    return column in {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def state(conn, activity_id: int) -> dict:
    if not _table_exists(conn, "agent_work_state"):
        return {"attempt_count": 0, "consecutive_failures": 0}
    row = conn.execute(
        "SELECT * FROM agent_work_state WHERE activity_id=?", (activity_id,)
    ).fetchone()
    return dict(row) if row else {"attempt_count": 0, "consecutive_failures": 0}


def next_failure_delay(conn, activity_id: int) -> tuple[int, int]:
    failures = int(state(conn, activity_id).get("consecutive_failures") or 0) + 1
    delay = FAILURE_BACKOFF_DAYS[min(failures - 1, len(FAILURE_BACKOFF_DAYS) - 1)]
    return failures, delay


def record_attempt(conn, activity_id: int, outcome: str, *, error: str | None = None) -> dict:
    """Record one completed attempt. A non-error attempt resets failure streak."""
    ensure_schema(conn)
    previous = state(conn, activity_id)
    attempts = int(previous.get("attempt_count") or 0) + 1
    failures = int(previous.get("consecutive_failures") or 0) + 1 if error else 0
    now = _now()
    conn.execute(
        "INSERT INTO agent_work_state("
        " activity_id,attempt_count,consecutive_failures,last_attempt_at,last_outcome,last_error,updated_at"
        ") VALUES (?,?,?,?,?,?,?)"
        " ON CONFLICT(activity_id) DO UPDATE SET"
        " attempt_count=excluded.attempt_count,"
        " consecutive_failures=excluded.consecutive_failures,"
        " last_attempt_at=excluded.last_attempt_at,"
        " last_outcome=excluded.last_outcome,"
        " last_error=excluded.last_error,"
        " updated_at=excluded.updated_at",
        (activity_id, attempts, failures, now, outcome, (error or "")[:500] or None, now),
    )
    conn.commit()
    return {"attempt_count": attempts, "consecutive_failures": failures}


def save_sweep(conn, summary: dict) -> None:
    safe = {
        "at": _now(),
        "processed": int(summary.get("processed") or 0),
        "done": int(summary.get("done") or 0),
        "rescheduled": int(summary.get("rescheduled") or 0),
        "failed": int(summary.get("failed") or 0),
        "materialized": dict(summary.get("materialized") or {}),
    }
    settings.set_value(conn, LAST_SWEEP_KEY, json.dumps(safe, ensure_ascii=False))


def _last_sweep(conn) -> dict | None:
    if not _table_exists(conn, "settings"):
        return None
    raw = settings.get(conn, LAST_SWEEP_KEY, "")
    if not raw:
        return None
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def queue_health(conn, *, today: dt.date | None = None) -> dict:
    """Read queue health without creating tables or mutating ownership."""
    today = today or dt.date.today()
    if not _table_exists(conn, "activities") or not _column_exists(conn, "activities", "work_owner"):
        return {
            "open": 0, "due": 0, "stale": 0, "repeated_failures": 0,
            "last_sweep": _last_sweep(conn),
        }
    stale_before = (today - dt.timedelta(days=STALE_DAYS)).isoformat()
    today_s = today.isoformat()
    row = conn.execute(
        "SELECT"
        " SUM(CASE WHEN status='open' AND source='agent' AND work_owner='agent' THEN 1 ELSE 0 END) open_count,"
        " SUM(CASE WHEN status='open' AND source='agent' AND work_owner='agent'"
        "   AND (due_at IS NULL OR due_at='' OR due_at<=?) THEN 1 ELSE 0 END) due_count,"
        " SUM(CASE WHEN status='open' AND source='agent' AND work_owner='agent'"
        "   AND due_at IS NOT NULL AND due_at!='' AND due_at<? THEN 1 ELSE 0 END) stale_count"
        " FROM activities",
        (today_s, stale_before),
    ).fetchone()
    repeated = 0
    if _table_exists(conn, "agent_work_state"):
        repeated_row = conn.execute(
            "SELECT COUNT(*) count FROM agent_work_state s"
            " JOIN activities a ON a.id=s.activity_id"
            " WHERE a.status='open' AND a.source='agent' AND a.work_owner='agent'"
            " AND s.consecutive_failures>=?",
            (REPEATED_FAILURE_THRESHOLD,),
        ).fetchone()
        repeated = int(repeated_row["count"] or 0)
    return {
        "open": int(row["open_count"] or 0),
        "due": int(row["due_count"] or 0),
        "stale": int(row["stale_count"] or 0),
        "repeated_failures": repeated,
        "last_sweep": _last_sweep(conn),
    }
