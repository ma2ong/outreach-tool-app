"""Durable ownership for CRM activities.

`activities` remains the single task ledger, but not every row is work for the human.
Routine public-data research created by Account Brain is owned by the Agent. The owner is
recovered only from exact proposal provenance/completion rules; titles are never used to
guess who should do something.
"""
from __future__ import annotations

import datetime as dt
import re

from app import activities
from app.agent import proposals, task_policy


def ensure_schema(conn) -> None:
    activities.ensure_schema(conn)
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(activities)")}
    if "work_owner" not in columns:
        conn.execute(
            "ALTER TABLE activities ADD COLUMN work_owner TEXT NOT NULL DEFAULT 'human'"
        )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_activities_owner_status_due "
        "ON activities(work_owner,status,due_at)"
    )
    conn.commit()


def _legacy_provenance(conn) -> int:
    """Repair only rows whose exact activity id was recorded by the Agent executor."""
    rows = conn.execute(
        "SELECT id,lead_no,execution_result FROM agent_proposals"
        " WHERE kind='create_task' AND status='executed'"
        " AND execution_result LIKE '已建销售任务 #%'")
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
    """Classify exact Agent-created activities as human or machine work."""
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
