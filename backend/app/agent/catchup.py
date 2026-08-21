"""Late-start recovery for the daily sales plan.

The normal planner deliberately prefers the morning. This helper exists for the local
runtime reality: if the PC first becomes available after noon, missing the whole day is
worse than planning a few hours late. It reuses the exact attempt/cooldown state owned by
`run.py`; it never creates a second retry policy.
"""
from __future__ import annotations

import datetime as dt

from app.agent import run


def due(conn, now: dt.datetime | None = None) -> bool:
    now = now or dt.datetime.now()
    # Morning is handled by run.plan_due(). After the report hour the day is no longer a
    # useful planning horizon, so recovery is bounded to the working afternoon.
    if not (run.PLAN_WINDOW[1] <= now.hour < run.REPORT_HOUR):
        return False
    status = run.status(conn)["plan"]
    if not status["enabled"] or status["last_date"] == now.date().isoformat():
        return False
    if int(status.get("attempts") or 0) >= int(status.get("max_attempts") or run.PLAN_MAX_ATTEMPTS):
        return False
    last_attempt = run._last_plan_attempt(conn)
    if last_attempt and now - last_attempt < dt.timedelta(minutes=run.PLAN_RETRY_MINUTES):
        return False
    return True


def run_if_due(conn, now: dt.datetime | None = None) -> dict:
    now = now or dt.datetime.now()
    if not due(conn, now):
        return {"ran": False, "proposed": 0}
    result = run.make_plan(conn, now)
    return {"ran": True, **result}
