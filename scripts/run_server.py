"""Windowless entry point for the scheduled task.

pythonw.exe has no stdout, so uvicorn's logging kills it on the first write.
Point both streams at a rotating-by-day log file before importing uvicorn.
Run this instead of `-m uvicorn` when starting without a console.
"""
import datetime
import os
import sys

BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
os.chdir(BACKEND)
sys.path.insert(0, BACKEND)

log_dir = os.path.join(BACKEND, "logs")
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, f"server-{datetime.date.today():%Y-%m-%d}.log")
stream = open(log_path, "a", encoding="utf-8", buffering=1)
sys.stdout = sys.stderr = stream

import uvicorn  # noqa: E402  (must come after the streams exist)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, log_level="info")
