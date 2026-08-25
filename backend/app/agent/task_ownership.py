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


def _locked(exc: sqlite3.OperationalError) -> bool:
    text = str(exc).lower()
    return "locked" in text or "busy" in text


def _owner_column_present(conn) -> bool:
    """Migration already done — a read-only check, so a busy DB costs nothing."""
    from app.db import tables_exist

    if not tables_exist(conn, "activities"):
        return False
    return "work_owner" in {row["name"] for row in conn.execute("PRAGMA table_info(activities)")}


def ensure_schema(conn) -> None:
    """Own the additive owner migration and tolerate a concurrently busy live DB.

    PR #9 can be deployed onto a database that already has the activities table. The
    first API request must not become responsible for a one-shot ALTER TABLE that fails
    just because the embedded Worker happens to be writing at the same instant. Retry a
    bounded number of times, including the base activities schema setup, and tolerate
    another connection winning the migration race between PRAGMA and ALTER.
    """
    if _owner_column_present(conn):
        return
    last_error: sqlite3.OperationalError | None = None
    for attempt in range(_SCHEMA_RETRIES):
        try:
            # Base activity setup itself executes DDL/index statements, so keep it inside
            # the retry loop as well; otherwise a busy production DB can fail before the
            # work_owner migration even starts.
            activities.ensure_schema(conn)
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(activities)")}
            if "work_owner" not in columns:
                try:
                    conn.execute(
                        "ALTER TABLE activities ADD COLUMN work_owner TEXT NOT NULL DEFAULT 'human'"
                    )
                except sqlite3.OperationalError as exc:
                    # A second process may have completed the same additive migration
                    # after our PRAGMA read. Verify the actual table before failing.
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
    """Repair only rows whose exact activity id was recorded by the Agent executor.

    Very old production databases may predate `execution_result`. CREATE TABLE IF NOT
    EXISTS does not add missing columns, so absence of that optional historical evidence
    must mean "cannot backfill", not a 500 for the entire Sales Tasks page.
    """
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(agent_proposals)")}
    if "execution_result" not in columns:
        return 0
    rows = conn.execute(
        "SELECT id,lead_no,execution_result FROM agent_proposals"
        " WHERE kind='create_task' AND status='executed'"
        " AND execution_result LIKE '已建销售任务 #%'"
        # Only rows still unattributed can change anything. Without this the repair
        # opens a write transaction on every single task-list request forever, and
        # loses the race against the Worker's lock.
        " AND EXISTS (SELECT 1 FROM activities a WHERE a.lead_no=agent_proposals.lead_no"
        "             AND a.source='manual' AND COALESCE(a.source_ref,'')='')").fetchall()
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


def backfill(conn) -> dict:
    """Classify exact Agent-created activities as human or machine work.

    Best effort on purpose: this repair runs on the task-list read path, where the
    embedded Sales Worker may hold the write lock at any moment. A skipped pass is
    retried on the next request and costs nothing; raising here took the whole task
    list and every customer's task panel down with a 500.
    """
    try:
        return _backfill(conn)
    except sqlite3.OperationalError as exc:
        if not _locked(exc):
            raise
        try:
            conn.rollback()
        except sqlite3.Error:
            pass
        return {"provenance_backfilled": 0, "owners_changed": 0, "skipped": "locked"}


def _backfill(conn) -> dict:
    ensure_schema(conn)
    proposals.ensure_schema(conn)
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
