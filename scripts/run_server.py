"""Windowless entry point for the scheduled task.

pythonw.exe has no stdout, so uvicorn's logging kills it on the first write.
Point both streams at a rotating-by-day log file before importing uvicorn.
Run this instead of `-m uvicorn` when starting without a console.
"""
import datetime
import faulthandler
import glob
import os
import sys
import traceback

BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
os.chdir(BACKEND)
sys.path.insert(0, BACKEND)

LOG_KEEP_DAYS = 30
log_dir = os.path.join(BACKEND, "logs")
os.makedirs(log_dir, exist_ok=True)

# Keep normal daily logs bounded so a machine that stays online for months does not
# grow this directory forever. Crash/start markers are tiny and are kept separately.
cutoff = datetime.date.today() - datetime.timedelta(days=LOG_KEEP_DAYS)
for old in glob.glob(os.path.join(log_dir, "server-????-??-??.log")):
    try:
        stamp = os.path.basename(old)[7:17]
        if datetime.date.fromisoformat(stamp) < cutoff:
            os.remove(old)
    except (OSError, ValueError):
        pass

log_path = os.path.join(log_dir, f"server-{datetime.date.today():%Y-%m-%d}.log")
stream = open(log_path, "a", encoding="utf-8", buffering=1)
sys.stdout = sys.stderr = stream
faulthandler.enable(file=stream, all_threads=True)

import uvicorn  # noqa: E402  (must come after the streams exist)
from app import startup  # noqa: E402


def _record_crash(exc: BaseException) -> None:
    marker = os.path.join(log_dir, "last-crash.txt")
    with open(marker, "w", encoding="utf-8") as fh:
        fh.write(datetime.datetime.now(datetime.UTC).isoformat() + "\n")
        traceback.print_exception(type(exc), exc, exc.__traceback__, file=fh)


if __name__ == "__main__":
    try:
        owner = startup.port_owner()
        if owner == "outreach":
            print("[startup] outreach-tool 已在 8000 端口运行，复用现有服务。", flush=True)
            raise SystemExit(0)
        if owner == "other":
            raise RuntimeError(
                "端口 8000 已被其他程序占用；outreach-tool 未启动。请关闭占用程序或修改端口。"
            )
        start_marker = os.path.join(log_dir, "last-start.txt")
        with open(start_marker, "w", encoding="utf-8") as fh:
            fh.write(datetime.datetime.now(datetime.UTC).isoformat())
        uvicorn.run("app.main:app", host="127.0.0.1", port=8000, log_level="info")
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 — Scheduled Task will restart after recording it
        _record_crash(exc)
        traceback.print_exception(type(exc), exc, exc.__traceback__, file=stream)
        raise
