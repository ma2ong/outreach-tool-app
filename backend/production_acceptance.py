"""Production acceptance checks used by the Windows updater.

Keep this logic in Python instead of embedding a long `python -c` expression inside
Windows PowerShell 5.1. That avoids quoting/parser differences on older Windows hosts.
"""
from __future__ import annotations

from app import backup, production_health, runtime
from app.db import connect
from app.main_deps import DB_PATH


def run_checks(db_path: str = DB_PATH) -> tuple[bool, dict]:
    backup_status = backup.ensure_daily_backup(db_path)
    conn = connect(db_path)
    try:
        health = production_health.status(conn, db_path)
        worker = runtime.status(conn)
    finally:
        conn.close()

    worker_active = bool(worker.get("lease"))
    ok = bool(backup_status.get("verified")) and health.get("status") in ("ok", "degraded") and worker_active
    result = {
        "backup": backup_status,
        "health": health,
        "worker_active": worker_active,
    }
    return ok, result


def main() -> int:
    ok, result = run_checks()
    backup_status = result["backup"]
    health = result["health"]
    print(
        "BACKUP=",
        backup_status.get("status"),
        " verified=",
        bool(backup_status.get("verified")),
        " date=",
        backup_status.get("date"),
    )
    print(
        "HEALTH=",
        health.get("status"),
        " critical=",
        health.get("critical"),
        " warnings=",
        health.get("warnings"),
    )
    print("WORKER_ACTIVE=", result["worker_active"])
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
