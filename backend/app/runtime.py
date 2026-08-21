"""Durable single-leader runtime state for the autonomous sales cycle.

FastAPI may run with multiple processes, and a hosted deployment may run a separate
worker beside the web process. Without a lease every process can start the same account
scan, plan or send cycle. This module uses SQLite's short BEGIN IMMEDIATE transaction to
select exactly one active owner while preserving local single-file deployment.
"""
from __future__ import annotations

import datetime as dt
import os
import socket
import sqlite3
import uuid


LEASE_NAME = "sales-operator"
DEFAULT_TTL_SECONDS = 20 * 60

SCHEMA = """
CREATE TABLE IF NOT EXISTS runtime_leases (
    name TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    mode TEXT NOT NULL,
    acquired_at TEXT NOT NULL,
    heartbeat_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runtime_state (
    name TEXT PRIMARY KEY,
    owner TEXT,
    mode TEXT,
    last_cycle_started_at TEXT,
    last_cycle_finished_at TEXT,
    last_cycle_ok INTEGER,
    last_error TEXT,
    cycle_count INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);
"""


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _iso(value: dt.datetime) -> str:
    return value.astimezone(dt.UTC).isoformat()


def _parse(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.UTC)
    return parsed.astimezone(dt.UTC)


def owner_id(mode: str = "embedded") -> str:
    """One stable identity per worker process lifetime."""
    return f"{mode}:{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:10]}"


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def acquire(conn: sqlite3.Connection, *, name: str = LEASE_NAME, owner: str,
            mode: str, ttl_seconds: int = DEFAULT_TTL_SECONDS,
            now: dt.datetime | None = None) -> bool:
    """Atomically acquire an absent/expired lease or renew the current owner's lease."""
    ensure_schema(conn)
    now = now or utcnow()
    expires = now + dt.timedelta(seconds=max(60, int(ttl_seconds)))
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT owner, expires_at FROM runtime_leases WHERE name=?", (name,)
        ).fetchone()
        if row is not None:
            existing_expiry = _parse(row["expires_at"])
            if row["owner"] != owner and existing_expiry and existing_expiry > now:
                conn.rollback()
                return False
        acquired_at = _iso(now)
        if row is not None and row["owner"] == owner:
            previous = conn.execute(
                "SELECT acquired_at FROM runtime_leases WHERE name=?", (name,)
            ).fetchone()
            acquired_at = previous["acquired_at"] if previous else acquired_at
        conn.execute(
            "INSERT INTO runtime_leases(name,owner,mode,acquired_at,heartbeat_at,expires_at)"
            " VALUES (?,?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET"
            " owner=excluded.owner, mode=excluded.mode, acquired_at=excluded.acquired_at,"
            " heartbeat_at=excluded.heartbeat_at, expires_at=excluded.expires_at",
            (name, owner, mode, acquired_at, _iso(now), _iso(expires)),
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise


def renew(conn: sqlite3.Connection, *, name: str = LEASE_NAME, owner: str,
          ttl_seconds: int = DEFAULT_TTL_SECONDS,
          now: dt.datetime | None = None) -> bool:
    ensure_schema(conn)
    now = now or utcnow()
    expires = now + dt.timedelta(seconds=max(60, int(ttl_seconds)))
    cur = conn.execute(
        "UPDATE runtime_leases SET heartbeat_at=?, expires_at=? WHERE name=? AND owner=?",
        (_iso(now), _iso(expires), name, owner),
    )
    conn.commit()
    return cur.rowcount == 1


def release(conn: sqlite3.Connection, *, name: str = LEASE_NAME, owner: str) -> bool:
    ensure_schema(conn)
    cur = conn.execute("DELETE FROM runtime_leases WHERE name=? AND owner=?", (name, owner))
    conn.commit()
    return cur.rowcount == 1


def record_start(conn: sqlite3.Connection, *, name: str = LEASE_NAME,
                 owner: str, mode: str, now: dt.datetime | None = None) -> None:
    ensure_schema(conn)
    now = now or utcnow()
    conn.execute(
        "INSERT INTO runtime_state(name,owner,mode,last_cycle_started_at,updated_at)"
        " VALUES (?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET"
        " owner=excluded.owner, mode=excluded.mode,"
        " last_cycle_started_at=excluded.last_cycle_started_at, updated_at=excluded.updated_at",
        (name, owner, mode, _iso(now), _iso(now)),
    )
    conn.commit()


def record_finish(conn: sqlite3.Connection, *, ok: bool, error: str | None,
                  name: str = LEASE_NAME, owner: str, mode: str,
                  now: dt.datetime | None = None) -> None:
    ensure_schema(conn)
    now = now or utcnow()
    conn.execute(
        "INSERT INTO runtime_state(name,owner,mode,last_cycle_finished_at,last_cycle_ok,last_error,"
        " cycle_count,updated_at) VALUES (?,?,?,?,?,?,1,?)"
        " ON CONFLICT(name) DO UPDATE SET owner=excluded.owner, mode=excluded.mode,"
        " last_cycle_finished_at=excluded.last_cycle_finished_at,"
        " last_cycle_ok=excluded.last_cycle_ok, last_error=excluded.last_error,"
        " cycle_count=runtime_state.cycle_count+1, updated_at=excluded.updated_at",
        (name, owner, mode, _iso(now), int(bool(ok)), (error or "")[:2000] or None, _iso(now)),
    )
    conn.commit()


def status(conn: sqlite3.Connection, *, name: str = LEASE_NAME,
           now: dt.datetime | None = None) -> dict:
    ensure_schema(conn)
    now = now or utcnow()
    lease = conn.execute("SELECT * FROM runtime_leases WHERE name=?", (name,)).fetchone()
    state = conn.execute("SELECT * FROM runtime_state WHERE name=?", (name,)).fetchone()
    lease_data = dict(lease) if lease else None
    state_data = dict(state) if state else None
    active = False
    heartbeat_age_seconds = None
    if lease_data:
        expiry = _parse(lease_data.get("expires_at"))
        heartbeat = _parse(lease_data.get("heartbeat_at"))
        active = bool(expiry and expiry > now)
        if heartbeat:
            heartbeat_age_seconds = max(0, int((now - heartbeat).total_seconds()))
    return {
        "name": name,
        "active": active,
        "lease": lease_data,
        "state": state_data,
        "heartbeat_age_seconds": heartbeat_age_seconds,
    }
