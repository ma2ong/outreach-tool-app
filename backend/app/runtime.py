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
import threading
import uuid
from collections.abc import Callable


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
    last_email_poll_ok INTEGER,
    last_error TEXT,
    cycle_count INTEGER NOT NULL DEFAULT 0,
    last_standby_at TEXT,
    last_standby_owner TEXT,
    standby_count INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS capability_health (
    name TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'idle',
    running_since TEXT,
    last_attempt_at TEXT,
    last_success_at TEXT,
    last_output_at TEXT,
    last_error TEXT,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    processed_count INTEGER NOT NULL DEFAULT 0,
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


def _add_missing_columns(
    conn: sqlite3.Connection, table: str, definitions: tuple[tuple[str, str], ...]
) -> None:
    """Apply additive upgrades safely when two first requests arrive together."""
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    for column, definition in definitions:
        if column in columns:
            continue
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        except sqlite3.OperationalError as exc:
            # Another web request/process can finish the same additive migration
            # after our PRAGMA snapshot.  Only that exact, now-satisfied race is safe
            # to ignore; locks and malformed migrations still need to be visible.
            if "duplicate column name" not in str(exc).lower():
                raise
    conn.commit()


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    # Runtime tables may already exist from an earlier draft/deployment. Keep this
    # upgrade additive just like the CRM schemas instead of requiring a destructive
    # recreation for a new health field.
    _add_missing_columns(conn, "runtime_state", (
        ("last_email_poll_ok", "INTEGER"),
        ("last_standby_at", "TEXT"),
        ("last_standby_owner", "TEXT"),
        ("standby_count", "INTEGER NOT NULL DEFAULT 0"),
    ))
    _ensure_capability_status(conn)


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
            "SELECT owner, acquired_at, expires_at FROM runtime_leases WHERE name=?", (name,)
        ).fetchone()
        if row is not None:
            existing_expiry = _parse(row["expires_at"])
            if row["owner"] != owner and existing_expiry and existing_expiry > now:
                conn.rollback()
                return False
        acquired_at = row["acquired_at"] if row is not None and row["owner"] == owner else _iso(now)
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
                  email_poll_ok: bool | None = None,
                  name: str = LEASE_NAME, owner: str, mode: str,
                  now: dt.datetime | None = None) -> None:
    ensure_schema(conn)
    now = now or utcnow()
    email_value = None if email_poll_ok is None else int(bool(email_poll_ok))
    conn.execute(
        "INSERT INTO runtime_state(name,owner,mode,last_cycle_finished_at,last_cycle_ok,"
        " last_email_poll_ok,last_error,cycle_count,updated_at) VALUES (?,?,?,?,?,?,?,1,?)"
        " ON CONFLICT(name) DO UPDATE SET owner=excluded.owner, mode=excluded.mode,"
        " last_cycle_finished_at=excluded.last_cycle_finished_at,"
        " last_cycle_ok=excluded.last_cycle_ok, last_email_poll_ok=excluded.last_email_poll_ok,"
        " last_error=excluded.last_error, cycle_count=runtime_state.cycle_count+1,"
        " updated_at=excluded.updated_at",
        (name, owner, mode, _iso(now), int(bool(ok)), email_value,
         (error or "")[:2000] or None, _iso(now)),
    )
    conn.commit()


def _ensure_capability_status(conn: sqlite3.Connection) -> None:
    _add_missing_columns(conn, "capability_health", (
        ("status", "TEXT NOT NULL DEFAULT 'idle'"),
        ("running_since", "TEXT"),
    ))


def record_standby(conn: sqlite3.Connection, *, owner: str,
                   name: str = LEASE_NAME, now: dt.datetime | None = None) -> None:
    """Persist a declined startup without touching the active lease or cycle result."""
    ensure_schema(conn)
    now = now or utcnow()
    conn.execute(
        "INSERT INTO runtime_state(name,last_standby_at,last_standby_owner,standby_count,updated_at)"
        " VALUES (?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET"
        " last_standby_at=excluded.last_standby_at,"
        " last_standby_owner=excluded.last_standby_owner,"
        " standby_count=runtime_state.standby_count+1, updated_at=excluded.updated_at",
        (name, _iso(now), owner, 1, _iso(now)),
    )
    conn.commit()


def _capability_write(db_path: str, name: str, *, success: bool | None,
                      error: str | None = None, processed_count: int = 0,
                      now: dt.datetime | None = None, outcome: str | None = None) -> None:
    """Best-effort telemetry: observing a job may never become a new job failure."""
    from app.db import connect

    conn = None
    try:
        conn = connect(db_path)
        ensure_schema(conn)
        _ensure_capability_status(conn)
        stamp = _iso(now or utcnow())
        if outcome in ("disabled", "not_configured", "idle"):
            conn.execute(
                "INSERT INTO capability_health(name,status,updated_at) VALUES (?,?,?)"
                " ON CONFLICT(name) DO UPDATE SET status=excluded.status,"
                " running_since=NULL,updated_at=excluded.updated_at", (name, outcome, stamp))
            conn.commit()
            return
        if outcome == "stalled":
            conn.execute(
                "INSERT INTO capability_health(name,status,running_since,last_error,updated_at)"
                " VALUES (?,'stalled',?,?,?) ON CONFLICT(name) DO UPDATE SET"
                " status='stalled',running_since=COALESCE(capability_health.running_since,"
                " excluded.running_since),last_error=excluded.last_error,"
                " updated_at=excluded.updated_at",
                (name, stamp, (error or "capability exceeded its deadline")[:2000], stamp),
            )
            conn.commit()
            return
        if success is None:
            conn.execute(
                "INSERT INTO capability_health(name,running_since,updated_at) VALUES (?,?,?)"
                " ON CONFLICT(name) DO UPDATE SET running_since=excluded.running_since,"
                " updated_at=excluded.updated_at",
                (name, stamp, stamp),
            )
        elif success:
            output_at = stamp if processed_count > 0 else None
            conn.execute(
                "INSERT INTO capability_health(name,last_attempt_at,last_success_at,last_output_at,"
                " last_error,consecutive_failures,processed_count,updated_at)"
                " VALUES (?,?,?,?,NULL,0,?,?) ON CONFLICT(name) DO UPDATE SET"
                " last_attempt_at=excluded.last_attempt_at,last_success_at=excluded.last_success_at,"
                " last_output_at=COALESCE(excluded.last_output_at,capability_health.last_output_at),"
                " last_error=NULL,consecutive_failures=0,"
                " processed_count=excluded.processed_count,updated_at=excluded.updated_at",
                (name, stamp, stamp, output_at, max(0, int(processed_count)), stamp),
            )
        else:
            conn.execute(
                "INSERT INTO capability_health(name,last_attempt_at,last_error,"
                " consecutive_failures,processed_count,updated_at) VALUES (?,?,?,1,0,?)"
                " ON CONFLICT(name) DO UPDATE SET last_attempt_at=excluded.last_attempt_at,"
                " last_error=excluded.last_error,consecutive_failures="
                " capability_health.consecutive_failures+1,processed_count=0,"
                " updated_at=excluded.updated_at",
                (name, stamp, (error or "unknown failure")[:2000], stamp),
            )
            if processed_count > 0:
                conn.execute(
                    "UPDATE capability_health SET processed_count=?,last_output_at=? WHERE name=?",
                    (processed_count, stamp, name))
        conn.execute("UPDATE capability_health SET status=? WHERE name=?",
                     (outcome or ("running" if success is None else
                                  "succeeded" if success else "failed"), name))
        if success is not None:
            conn.execute("UPDATE capability_health SET running_since=NULL WHERE name=?", (name,))
        conn.commit()
    except Exception:  # noqa: BLE001 — telemetry must never affect the observed job
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass  # telemetry cleanup must not change the business result


def capability_status(conn: sqlite3.Connection, *, now: dt.datetime | None = None) -> list[dict]:
    ensure_schema(conn)
    _ensure_capability_status(conn)
    rows = conn.execute("SELECT * FROM capability_health ORDER BY name").fetchall()
    result = [dict(row) for row in rows]
    for row in result:
        started = _parse(row.get("running_since"))
        if started and (now or utcnow()) - started > dt.timedelta(seconds=DEFAULT_TTL_SECONDS):
            row["status"] = "stalled"
    return result


def _processed_count(result) -> int:
    if isinstance(result, bool) or result is None:
        return 0
    if isinstance(result, int):
        return max(0, result)
    if isinstance(result, dict):
        for key in ("processed", "sent", "scanned", "updated", "enrolled", "imported"):
            value = result.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                return max(0, value)
    return 0


def run_capability(db_path: str, name: str, fn: Callable[[], object]) -> dict:
    """Run one stage, preserve its real error, and never stop the following stages."""
    _capability_write(db_path, name, success=None)
    try:
        result = fn()
        if isinstance(result, dict):
            status = result.get("status")
            if status == "stalled":
                error = str(result.get("error") or "capability exceeded its deadline")
                _capability_write(
                    db_path, name, success=None, error=error, outcome="stalled")
                return {"ok": False, "status": "stalled", "error": error,
                        "processed_count": 0}
            if status in ("disabled", "not_configured", "idle"):
                _capability_write(db_path, name, success=None, outcome=status)
                return {"ok": True, "status": status, "error": None, "processed_count": 0}
            errors = result.get("errors") or result.get("error")
            if errors or result.get("failed") or result.get("unavailable") or result.get("ok") is False:
                processed = _processed_count(result)
                error = str(errors or result.get("note") or "job reported failures")
                status = "partial" if processed else "failed"
                _capability_write(db_path, name, success=False, error=error,
                                  processed_count=processed, outcome=status)
                return {"ok": False, "status": status, "error": error, "processed_count": processed}
        if result is False:
            raise RuntimeError(f"{name} reported failure")
    except Exception as exc:  # noqa: BLE001 — failure is returned to the orchestrator
        error = f"{type(exc).__name__}: {exc}"
        _capability_write(db_path, name, success=False, error=error)
        return {"ok": False, "status": "failed", "error": error, "processed_count": 0}
    processed = _processed_count(result)
    _capability_write(db_path, name, success=True, processed_count=processed)
    return {"ok": True, "status": "succeeded", "error": None, "processed_count": processed}


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


def _heartbeat_loop(db_path: str, owner: str, mode: str, stop: threading.Event,
                    ttl_seconds: int, interval_seconds: int) -> None:
    """Renew from a separate connection while a potentially slow sales cycle is running."""
    from app.db import connect

    while not stop.wait(interval_seconds):
        conn = None
        try:
            conn = connect(db_path)
            if not renew(conn, owner=owner, ttl_seconds=ttl_seconds):
                return  # ownership was lost; never fight the new leader
        except Exception:  # the current cycle still owns its normal error handling
            pass
        finally:
            if conn is not None:
                conn.close()


def run_leased_cycle(db_path: str, cycle_fn: Callable[[], bool], *, owner: str,
                     mode: str, ttl_seconds: int = DEFAULT_TTL_SECONDS,
                     release_after: bool = False) -> dict:
    """Run one full operating cycle only when this process owns the renewable lease.

    Before *any* unattended sales work, the leader makes sure today's SQLite snapshot
    exists and passes ``PRAGMA quick_check``. If backup creation or verification fails,
    the cycle is recorded as failed and no customer-facing/background sales action runs.

    ``cycle_fn`` returns the email-poll health used by the scheduler's retry cadence. A
    separate heartbeat connection renews the lease during slow website/mailbox work, so
    another process cannot take over mid-send merely because a cycle ran longer than the
    normal interval. One-shot/cron callers set ``release_after=True`` to hand off at once.
    """
    from app import backup
    from app.db import connect, init_schema

    conn = connect(db_path)
    heartbeat_stop: threading.Event | None = None
    heartbeat: threading.Thread | None = None
    backup_info: dict | None = None
    try:
        init_schema(conn)
        ensure_schema(conn)
        if not acquire(conn, owner=owner, mode=mode, ttl_seconds=ttl_seconds):
            record_standby(conn, owner=owner)
            return {
                "acquired": False, "cycle_ok": None, "email_poll_ok": None,
                "error": None, "owner": owner, "mode": mode, "backup": None,
            }
        record_start(conn, owner=owner, mode=mode)
        _capability_write(db_path, "backup", success=None)
        try:
            backup_info = backup.ensure_daily_backup(db_path)
        except Exception as exc:  # noqa: BLE001 — backup failure is a hard safety gate
            error = f"BackupError: {exc}"
            _capability_write(db_path, "backup", success=False, error=error)
            record_finish(conn, ok=False, error=error, email_poll_ok=None,
                          owner=owner, mode=mode)
            return {
                "acquired": True, "cycle_ok": False, "email_poll_ok": None,
                "error": error, "owner": owner, "mode": mode, "backup": None,
            }
        _capability_write(db_path, "backup", success=True, processed_count=1)

        heartbeat_stop = threading.Event()
        heartbeat_interval = max(10, min(300, int(ttl_seconds) // 3))
        heartbeat = threading.Thread(
            target=_heartbeat_loop,
            args=(db_path, owner, mode, heartbeat_stop, ttl_seconds, heartbeat_interval),
            daemon=True,
            name=f"outreach-heartbeat-{mode}",
        )
        heartbeat.start()
        try:
            email_poll_ok = bool(cycle_fn())
        except Exception as exc:  # noqa: BLE001 — runtime records rather than hides a crashed cycle
            error = f"{type(exc).__name__}: {exc}"
            record_finish(conn, ok=False, error=error, email_poll_ok=None,
                          owner=owner, mode=mode)
            return {
                "acquired": True, "cycle_ok": False, "email_poll_ok": None,
                "error": error, "owner": owner, "mode": mode, "backup": backup_info,
            }
        record_finish(conn, ok=True, error=None, email_poll_ok=email_poll_ok,
                      owner=owner, mode=mode)
        renew(conn, owner=owner, ttl_seconds=ttl_seconds)
        return {
            "acquired": True, "cycle_ok": True, "email_poll_ok": email_poll_ok,
            "error": None, "owner": owner, "mode": mode, "backup": backup_info,
        }
    finally:
        if heartbeat_stop is not None:
            heartbeat_stop.set()
        if heartbeat is not None:
            heartbeat.join(timeout=2)
        if release_after:
            try:
                release(conn, owner=owner)
            except Exception:
                pass
        conn.close()
