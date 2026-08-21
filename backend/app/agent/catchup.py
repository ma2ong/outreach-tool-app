"""Late-start recovery for the daily sales plan.

The normal planner deliberately prefers the morning. This helper exists for the local
runtime reality: if the PC first becomes available after noon, missing the whole day is
worse than planning a few hours late. It reuses the exact attempt/cooldown state owned by
`run.py`; it never creates a second retry policy.
"""
from __future__ import annotations

import datetime as dt

from app import settings
from app.agent import run


def due(conn, now: dt.datetime | None = None) -> bool:
    now = now or dt.datetime.now()
    # Morning is handled by run.plan_due(). After the report hour the day is no longer a
    # useful planning horizon, so recovery is bounded to the working afternoon.
    if not (run.PLAN_WINDOW[1] <= now.hour < run.REPORT_HOUR):
        return False
    today = now.date().isoformat()
    if settings.get(conn, run._K_PLAN_ENABLED, "1") != "1":
        return False
    if settings.get(conn, run._K_PLAN_DATE) == today:
        return False
    if run._plan_attempts(conn, today) >= run.PLAN_MAX_ATTEMPTS:
        return False
    last_attempt = run._last_plan_attempt(conn)
    if last_attempt and settings.get(conn, run._K_PLAN_ATTEMPT_DATE) == today:
        if now - last_attempt < dt.timedelta(minutes=run.PLAN_RETRY_MINUTES):
            return False
    return True


def run_if_due(conn, now: dt.datetime | None = None) -> dict:
    now = now or dt.datetime.now()
    if not due(conn, now):
        return {"ran": False, "proposed": 0}
    result = run.make_plan(conn, now)
    return {"ran": True, **result}
