"""Standalone durable sales worker.

Local desktop installs keep the embedded FastAPI worker by default. Hosted installs can
set OUTREACH_EMBEDDED_WORKER=0 on the web service and run this module as a separate,
restartable process. Both modes share the same SQLite lease, so accidentally running
both does not duplicate a sales cycle.
"""
from __future__ import annotations

import argparse
import os
import signal
import time

from app import runtime
from app.main_deps import DB_PATH


DEFAULT_INTERVAL_SECONDS = 15 * 60
DEFAULT_RETRY_SECONDS = 60
DEFAULT_STANDBY_SECONDS = 60


def _seconds(name: str, default: int, minimum: int = 5) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        return default
    return max(minimum, value)


def run_once(*, db_path: str = DB_PATH, owner: str | None = None,
             mode: str = "worker", release_after: bool = True) -> dict:
    """Run one leased operating cycle; useful for health checks, tests and cron."""
    from app import main

    owner = owner or runtime.owner_id(mode)
    # In normal deployment main.DB_PATH and db_path both come from OUTREACH_DB. Keeping
    # the explicit check prevents a test or caller from leasing one DB while the cycle
    # silently mutates another.
    if os.path.abspath(main.DB_PATH) != os.path.abspath(db_path):
        raise RuntimeError(
            "worker db_path 与 app.main.DB_PATH 不一致；请在进程启动前设置 OUTREACH_DB"
        )
    return runtime.run_leased_cycle(
        db_path, main.background_cycle, owner=owner, mode=mode,
        release_after=release_after,
    )


def run_forever(*, db_path: str = DB_PATH) -> None:
    """Own the sales-operator lease for as long as this process is healthy."""
    owner = runtime.owner_id("worker")
    stop = False

    def request_stop(*_args):
        nonlocal stop
        stop = True

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, request_stop)
        except (ValueError, OSError):
            pass

    interval = _seconds("OUTREACH_WORKER_INTERVAL_SECONDS", DEFAULT_INTERVAL_SECONDS)
    retry = _seconds("OUTREACH_WORKER_RETRY_SECONDS", DEFAULT_RETRY_SECONDS)
    standby = _seconds("OUTREACH_WORKER_STANDBY_SECONDS", DEFAULT_STANDBY_SECONDS)

    while not stop:
        try:
            result = run_once(
                db_path=db_path, owner=owner, mode="worker", release_after=False)
        except Exception as exc:  # noqa: BLE001 — process supervisor should not be needed for a transient DB error
            print(f"[sales-worker] cycle error: {type(exc).__name__}: {exc}", flush=True)
            delay = retry
        else:
            if not result["acquired"]:
                delay = standby
            elif not result["cycle_ok"] or not result["email_poll_ok"]:
                delay = retry
            else:
                delay = interval
        slept = 0
        while not stop and slept < delay:
            step = min(5, delay - slept)
            time.sleep(step)
            slept += step

    # Graceful shutdown releases immediately; a hard crash falls back to TTL expiry.
    from app.db import connect
    conn = connect(db_path)
    try:
        runtime.release(conn, owner=owner)
    finally:
        conn.close()


def main_cli() -> None:
    parser = argparse.ArgumentParser(description="Outreach autonomous sales worker")
    parser.add_argument("--once", action="store_true",
                        help="run one leased cycle and release the lease")
    args = parser.parse_args()
    if args.once:
        result = run_once(release_after=True)
        print(result, flush=True)
        return
    run_forever()


if __name__ == "__main__":
    main_cli()
