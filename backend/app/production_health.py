"""Read-only production health diagnostics with no customer/business data leakage."""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import threading
import time
from pathlib import Path

from app import auth, backup


MIN_FREE_CRITICAL_BYTES = 256 * 1024 * 1024
MIN_FREE_WARN_BYTES = 1024 * 1024 * 1024
DB_CHECK_TTL_SECONDS = 60
_DB_CHECK_CACHE: dict[str, tuple[float, dict]] = {}
_DB_CHECK_LOCK = threading.Lock()


def _db_cache_key(conn: sqlite3.Connection) -> str | None:
    """Return the durable SQLite file path; in-memory/test DBs stay uncached."""
    try:
        rows = conn.execute("PRAGMA database_list").fetchall()
    except Exception:  # noqa: BLE001 — the real health check will report the DB failure
        return None
    for row in rows:
        # sqlite3.Row supports both mapping and index access; database_list is
        # seq/name/file and the main DB is the only one relevant to this app.
        try:
            name = row["name"]
            path = row["file"]
        except (IndexError, KeyError, TypeError):
            name, path = row[1], row[2]
        if name == "main" and path:
            return os.path.abspath(str(path))
    return None


def _run_db_quick_check(conn: sqlite3.Connection) -> dict:
    try:
        rows = [str(row[0]) for row in conn.execute("PRAGMA quick_check(1)").fetchall()]
        ok = rows == ["ok"]
        return {"status": "ok" if ok else "corrupt", "quick_check": "; ".join(rows[:3])}
    except Exception as exc:  # noqa: BLE001 — health endpoint reports rather than hides
        return {"status": "error", "quick_check": f"{type(exc).__name__}: {exc}"}


def _db_status(conn: sqlite3.Connection) -> dict:
    """Run the live DB check at most once per minute for the same database file.

    The Worker badge polls runtime status every 15 seconds. Re-running SQLite integrity
    work on every browser poll would make observability itself increasingly expensive as
    the CRM grows, so file-backed databases share a short process-local cache. In-memory
    test databases are never cached.
    """
    key = _db_cache_key(conn)
    if key is None:
        return _run_db_quick_check(conn)

    now = time.monotonic()
    with _DB_CHECK_LOCK:
        cached = _DB_CHECK_CACHE.get(key)
        if cached and now - cached[0] < DB_CHECK_TTL_SECONDS:
            return dict(cached[1])

    result = _run_db_quick_check(conn)
    with _DB_CHECK_LOCK:
        _DB_CHECK_CACHE[key] = (now, dict(result))
        # Production has one DB, while tests create many temporary paths. Keep this
        # cache bounded without introducing a second cache dependency.
        if len(_DB_CHECK_CACHE) > 64:
            oldest = min(_DB_CHECK_CACHE, key=lambda item: _DB_CHECK_CACHE[item][0])
            if oldest != key:
                _DB_CHECK_CACHE.pop(oldest, None)
    return result


def _disk_status(db_path: str) -> dict:
    target = os.path.dirname(os.path.abspath(db_path)) or "."
    try:
        usage = shutil.disk_usage(target)
    except OSError as exc:
        return {"status": "error", "free_bytes": None, "total_bytes": None,
                "detail": f"{type(exc).__name__}: {exc}"}
    if usage.free < MIN_FREE_CRITICAL_BYTES:
        state = "critical"
    elif usage.free < MIN_FREE_WARN_BYTES:
        state = "warning"
    else:
        state = "ok"
    return {"status": state, "free_bytes": usage.free, "total_bytes": usage.total}


def _frontend_status() -> dict:
    root = Path(__file__).resolve().parents[2]
    index = root / "frontend" / "dist" / "index.html"
    return {
        "status": "ok" if index.is_file() and index.stat().st_size > 0 else "missing",
        "built": index.is_file(),
        "size_bytes": index.stat().st_size if index.is_file() else 0,
    }


def _server_log_status() -> dict:
    backend = Path(__file__).resolve().parents[1]
    log_dir = backend / "logs"
    crash = log_dir / "last-crash.txt"
    started = log_dir / "last-start.txt"
    crash_mtime = crash.stat().st_mtime if crash.exists() else None
    start_mtime = started.stat().st_mtime if started.exists() else None
    unrecovered = bool(crash_mtime and (start_mtime is None or crash_mtime > start_mtime))
    return {
        "status": "warning" if unrecovered else "ok",
        "last_crash_unrecovered": unrecovered,
        "last_crash_mtime": crash_mtime,
        "last_start_mtime": start_mtime,
    }


def status(conn: sqlite3.Connection, db_path: str) -> dict:
    database = _db_status(conn)
    backups = backup.status(db_path)
    disk = _disk_status(db_path)
    frontend = _frontend_status()
    server_log = _server_log_status()

    critical: list[str] = []
    warnings: list[str] = []
    if database["status"] != "ok":
        critical.append("SQLite 主数据库完整性检查未通过")
    if backups["status"] in ("missing", "corrupt"):
        critical.append("没有可验证的数据库备份" if backups["status"] == "missing" else "最近数据库备份损坏")
    elif backups["status"] == "stale":
        warnings.append("最近数据库备份不是今天生成的")
    if disk["status"] == "critical":
        critical.append("数据库磁盘剩余空间低于 256MB")
    elif disk["status"] == "warning":
        warnings.append("数据库磁盘剩余空间低于 1GB")
    if frontend["status"] != "ok":
        critical.append("frontend/dist/index.html 缺失或为空")
    if server_log["status"] != "ok":
        warnings.append("检测到最近一次服务崩溃且尚未看到更新的启动标记")

    overall = "critical" if critical else "degraded" if warnings else "ok"
    return {
        "status": overall,
        "critical": critical,
        "warnings": warnings,
        "database": database,
        "backup": backups,
        "disk": disk,
        "frontend": frontend,
        "server": server_log,
        "auth_enabled": auth.enabled(),
        "python": {
            "version": ".".join(map(str, sys.version_info[:3])),
            "ci_baseline": "3.14",
            "matches_ci_minor": sys.version_info[:2] == (3, 13),
        },
    }
