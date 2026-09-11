"""Verified, low-risk backups for the local SQLite sales database.

The app can stay running for days or weeks, so startup-only backups are not enough.
The single-leader sales runtime calls :func:`ensure_daily_backup` each cycle; the
function is idempotent and creates at most one verified snapshot per local calendar day.
"""
from __future__ import annotations

import datetime as dt
import functools
import glob
import os
import sqlite3
from pathlib import Path


BACKUP_KEEP = 14


class BackupError(RuntimeError):
    pass


def _backup_dir(db_path: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(db_path)), "backups")


def _backup_path(db_path: str, today: dt.date | None = None) -> str:
    today = today or dt.date.today()
    return os.path.join(_backup_dir(db_path), f"outreach-{today.isoformat()}.db")


def _quick_check_uncached(path: str) -> tuple[bool, str]:
    if not os.path.isfile(path):
        return False, "file missing"
    try:
        conn = sqlite3.connect(path, timeout=30)
        try:
            rows = [str(row[0]) for row in conn.execute("PRAGMA quick_check").fetchall()]
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001 — status must report corruption/open errors
        return False, f"{type(exc).__name__}: {exc}"
    if rows == ["ok"]:
        return True, "ok"
    return False, "; ".join(rows[:5]) or "quick_check failed"


@functools.lru_cache(maxsize=64)
def _quick_check_cached(path: str, mtime_ns: int, size: int) -> tuple[bool, str]:
    # mtime/size are intentionally part of the cache key: a replaced backup is checked
    # again, while the dashboard may poll the same verified file every 15 seconds.
    return _quick_check_uncached(path)


def quick_check(path: str) -> tuple[bool, str]:
    try:
        stat = os.stat(path)
    except OSError as exc:
        return False, f"{type(exc).__name__}: {exc}"
    return _quick_check_cached(os.path.abspath(path), stat.st_mtime_ns, stat.st_size)


def _prune(bdir: str, keep: int) -> None:
    snapshots = sorted(glob.glob(os.path.join(bdir, "outreach-????-??-??.db")))
    for old in snapshots[:-max(1, int(keep))]:
        try:
            os.remove(old)
        except OSError:
            # A pruning failure must not invalidate the snapshot that was just made.
            pass


def _quarantine(path: str) -> str:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    quarantined = f"{path}.corrupt-{stamp}"
    os.replace(path, quarantined)
    return quarantined


def ensure_daily_backup(db_path: str, *, keep: int = BACKUP_KEEP,
                        today: dt.date | None = None) -> dict:
    """Create or verify today's transactionally consistent SQLite snapshot.

    If today's file exists but fails ``PRAGMA quick_check``, it is quarantined and
    replaced from the live database. A newly-created snapshot is verified *before* the
    atomic rename; an unverified backup is never presented as the day's good copy.
    """
    if not os.path.isfile(db_path):
        raise BackupError(f"database not found: {db_path}")
    today = today or dt.date.today()
    bdir = _backup_dir(db_path)
    os.makedirs(bdir, exist_ok=True)
    dest = _backup_path(db_path, today)
    quarantined = None

    if os.path.exists(dest):
        valid, detail = quick_check(dest)
        if valid:
            _prune(bdir, keep)
            return {
                "status": "ok", "path": dest, "created": False, "verified": True,
                "quick_check": detail, "size_bytes": os.path.getsize(dest),
                "date": today.isoformat(), "quarantined": None,
            }
        quarantined = _quarantine(dest)

    tmp = dest + ".tmp"
    try:
        if os.path.exists(tmp):
            os.remove(tmp)
        source = sqlite3.connect(db_path, timeout=30)
        target = sqlite3.connect(tmp, timeout=30)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        valid, detail = _quick_check_uncached(tmp)
        if not valid:
            raise BackupError(f"new snapshot failed SQLite quick_check: {detail}")
        os.replace(tmp, dest)
        # Ensure cached verification keys cannot retain an old file with the same path.
        _quick_check_cached.cache_clear()
        _prune(bdir, keep)
        return {
            "status": "ok", "path": dest, "created": True, "verified": True,
            "quick_check": detail, "size_bytes": os.path.getsize(dest),
            "date": today.isoformat(), "quarantined": quarantined,
        }
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        raise


def startup_backup(db_path: str) -> str | None:
    """Compatibility shape for bootstrap/tests while using the verified backup path."""
    if not os.path.isfile(db_path):
        return None
    return str(ensure_daily_backup(db_path)["path"])


def status(db_path: str, *, today: dt.date | None = None) -> dict:
    """Cheap dashboard-friendly backup state, with cached integrity verification."""
    today = today or dt.date.today()
    bdir = _backup_dir(db_path)
    paths = sorted(glob.glob(os.path.join(bdir, "outreach-????-??-??.db")))
    if not paths:
        return {
            "status": "missing", "verified": False, "path": None,
            "date": None, "age_days": None, "count": 0, "size_bytes": 0,
            "quick_check": "no backup snapshots found",
        }
    latest = paths[-1]
    name = Path(latest).stem
    raw_date = name.removeprefix("outreach-")
    try:
        backup_date = dt.date.fromisoformat(raw_date)
        age_days = max(0, (today - backup_date).days)
    except ValueError:
        backup_date = None
        age_days = None
    valid, detail = quick_check(latest)
    state = "ok" if valid and age_days == 0 else "stale" if valid else "corrupt"
    return {
        "status": state,
        "verified": valid,
        "path": latest,
        "date": backup_date.isoformat() if backup_date else raw_date,
        "age_days": age_days,
        "count": len(paths),
        "size_bytes": os.path.getsize(latest),
        "quick_check": detail,
    }
