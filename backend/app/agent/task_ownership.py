"""Durable ownership for CRM activities.

`activities` remains the single task ledger, but not every row is work for the human.
Routine public-data research created by Account Brain is owned by the Agent. The owner is
recovered only from exact proposal provenance/completion rules; titles are never used to
guess who should do something.
"""
from __future__ import annotations

import datetime as dt
import re
import sqlite3
import time

from app import activities
from app.agent import proposals, task_policy

_SCHEMA_RETRIES = 6
_SCHEMA_RETRY_SECONDS = 0.25
_BACKFILL_RETRIES = 6
_BACKFILL_RETRY_SECONDS = 0.35


def _locked(exc: sqlite3.OperationalError) -> bool:
    text = str(exc).lower()
    return "locked" in text or "busy" in text


def ensure_schema(conn) -> None:
    """Own the additive owner migration and tolerate a concurrently busy live DB."""
    last_error: sqlite3.OperationalError | None = None
    for attempt in range(_SCHEMA_RETRIES):
        try:
            activities.ensure_schema(conn)
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(activities)")}
            if "work_owner" not in columns:
                try:
                    conn.execute(
                        "ALTER TABLE activities ADD COLUMN work_owner TEXT NOT NULL DEFAULT 'human'"
                    )
                except sqlite3.OperationalError as exc:
                    columns = {row["name"] for row in conn.execute("PRAGMA table_info(activities)")}
                    if "work_owner" not in columns:
                        raise exc
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_activities_owner_status_due "
                "ON activities(work_owner,status,due_at)"
            )
            conn.commit()
            return
        except sqlite3.OperationalError as exc:
            last_error = exc
            try:
                conn.rollback()
            except sqlite3.Error:
                pass
            if not _locked(exc) or attempt + 1 >= _SCHEMA_RETRIES:
                raise
            time.sleep(_SCHEMA_RETRY_SECONDS * (attempt + 1))
    if last_error is not None:
        raise last_error


def _legacy_provenance(conn) -> int:
    """Repair only rows whose exact activity id was recorded by the Agent executor."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(agent_proposals)")}
    if "execution_result" not in columns:
        return 0
    # Materialize the result set before issuing UPDATEs on the same connection.
    rows = conn.execute(
        "SELECT id,lead_no,execution_result FROM agent_proposals"
        " WHERE kind='create_task' AND status='executed'"
        " AND execution_result LIKE '已建销售任务 #%'").fetchall()
    fixed = 0
    for row in rows:
        match = re.search(r"已建销售任务 #(\d+)", row["execution_result"] or "")
        if not match:
            continue
        cur = conn.execute(
            "UPDATE activities SET source='agent',source_ref=?,updated_at=?"
            " WHERE id=? AND lead_no=? AND source='manual' AND COALESCE(source_ref,'')=''",
            (f"proposal:{row['id']}", dt.datetime.now(dt.UTC).isoformat(),
             int(match.group(1)), row["lead_no"]),
        )
        fixed += cur.rowcount
    return fixed


def _backfill_once(conn) -> dict:
    provenance = _legacy_provenance(conn)
    changed = 0
    rows = conn.execute(
        "SELECT id,source_ref,work_owner FROM activities"
        " WHERE source='agent' AND source_ref LIKE 'proposal:%'"
    ).fetchall()
    for row in rows:
        try:
            proposal_id = int(str(row["source_ref"]).split(":", 1)[1])
        except (TypeError, ValueError, IndexError):
            continue
        proposal = proposals.get(conn, proposal_id)
        if not proposal:
            continue
        owner = task_policy.owner_for_proposal(proposal)
        if row["work_owner"] == owner:
            continue
        cur = conn.execute(
            "UPDATE activities SET work_owner=?,updated_at=? WHERE id=?",
            (owner, dt.datetime.now(dt.UTC).isoformat(), row["id"]),
        )
        changed += cur.rowcount
    if provenance or changed:
        conn.commit()
    return {"provenance_backfilled": provenance, "owners_changed": changed}


def backfill(conn) -> dict:
    """Classify exact Agent-created activities as human or machine work.

    This is a maintenance/write operation. It runs at startup and in the Worker, never
    as part of a Sales Tasks GET request. A live SQLite writer may still overlap a Worker
    pass, so retry the whole transaction on transient lock/busy errors.
    """
    ensure_schema(conn)
    proposals.ensure_schema(conn)
    last_error: sqlite3.OperationalError | None = None
    for attempt in range(_BACKFILL_RETRIES):
        try:
            return _backfill_once(conn)
        except sqlite3.OperationalError as exc:
            last_error = exc
            try:
                conn.rollback()
            except sqlite3.Error:
                pass
            if not _locked(exc) or attempt + 1 >= _BACKFILL_RETRIES:
                raise
            time.sleep(_BACKFILL_RETRY_SECONDS * (attempt + 1))
    if last_error is not None:
        raise last_error
    return {"provenance_backfilled": 0, "owners_changed": 0}


def set_owner(conn, activity_id: int, owner: str) -> None:
    ensure_schema(conn)
    if owner not in task_policy.WORK_OWNERS:
        raise ValueError("unknown work owner")
    conn.execute(
        "UPDATE activities SET work_owner=?,updated_at=? WHERE id=?",
        (owner, dt.datetime.now(dt.UTC).isoformat(), activity_id),
    )
    conn.commit()


def filter_rows(rows: list[dict], owner: str | None) -> list[dict]:
    if owner in (None, "", "all"):
        return rows
    if owner not in task_policy.WORK_OWNERS:
        raise activities.ActivityValidation("未知任务负责人")
    return [row for row in rows if (row.get("work_owner") or "human") == owner]


def stats(conn, owner: str | None = None) -> dict:
    ensure_schema(conn)
    if owner not in (None, "", "all", *task_policy.WORK_OWNERS):
        raise activities.ActivityValidation("未知任务负责人")
    today = dt.date.today().isoformat()
    where = ""
    params: list[object] = [today, today, today]
    if owner not in (None, "", "all"):
        where = " WHERE work_owner=?"
        params.append(owner)
    row = conn.execute(
        "SELECT"
        " SUM(CASE WHEN status='open' AND due_at < ? THEN 1 ELSE 0 END) overdue,"
        " SUM(CASE WHEN status='open' AND due_at = ? THEN 1 ELSE 0 END) today,"
        " SUM(CASE WHEN status='open' AND due_at > ? THEN 1 ELSE 0 END) upcoming,"
        " SUM(CASE WHEN status='open' AND (due_at IS NULL OR due_at='') THEN 1 ELSE 0 END) no_due,"
        " SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) open_count"
        f" FROM activities{where}",
        params,
    ).fetchone()
    return {key: int(row[key] or 0) for key in row.keys()}
