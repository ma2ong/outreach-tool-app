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
    # Kept as a compatibility hook; the normal planner now covers the whole workday.
    if not (12 <= now.hour < run.REPORT_HOUR):
        return False
    return run.plan_due(conn, now)


def run_if_due(conn, now: dt.datetime | None = None) -> dict:
    now = now or dt.datetime.now()
    if not due(conn, now):
        return {"ran": False, "proposed": 0}
    result = run.make_plan(conn, now)
    return {"ran": True, **result}
