"""Immutable copy history for editable customer-facing content (docs/107 G2)."""
from __future__ import annotations

import datetime as dt


SCHEMA = """
CREATE TABLE IF NOT EXISTS copy_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_kind TEXT NOT NULL,
    source_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    channel TEXT NOT NULL,
    market TEXT,
    customer_type TEXT,
    subject TEXT,
    body TEXT NOT NULL,
    day_offset INTEGER,
    change_kind TEXT NOT NULL,
    rollback_of_id INTEGER,
    created_by TEXT NOT NULL DEFAULT 'allen',
    created_at TEXT NOT NULL,
    UNIQUE(source_kind, source_id, version)
);
CREATE INDEX IF NOT EXISTS idx_copy_versions_source
    ON copy_versions(source_kind, source_id, version DESC);
"""


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def ensure_schema(conn) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def _source_id(sequence_id: int, step_order: int) -> str:
    return f"{sequence_id}:{step_order}"


def _sequence_context(conn, sequence_id: int) -> tuple[str, str | None, str | None]:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(sequences)")}
    optional = ",segment" if "segment" in columns else ""
    row = conn.execute(
        f"SELECT channel{optional} FROM sequences WHERE id=?", (sequence_id,)
    ).fetchone()
    if not row:
        raise LookupError("sequence not found")
    return row["channel"], None, row["segment"] if "segment" in row.keys() else None


def _insert_sequence_step(conn, sequence_id: int, step_order: int, row, *,
                          change_kind: str, rollback_of_id: int | None = None) -> dict:
    source_id = _source_id(sequence_id, step_order)
    channel, market, customer_type = _sequence_context(conn, sequence_id)
    version = conn.execute(
        "SELECT COALESCE(MAX(version),0)+1 FROM copy_versions"
        " WHERE source_kind='sequence_step' AND source_id=?", (source_id,)
    ).fetchone()[0]
    cur = conn.execute(
        "INSERT INTO copy_versions(source_kind,source_id,version,channel,market,"
        " customer_type,subject,body,day_offset,change_kind,rollback_of_id,created_at)"
        " VALUES ('sequence_step',?,?,?,?,?,?,?,?,?,?,?)",
        (source_id, version, channel, market, customer_type, row["subject"], row["body"],
         row["day_offset"], change_kind, rollback_of_id, _now()),
    )
    return dict(conn.execute("SELECT * FROM copy_versions WHERE id=?", (cur.lastrowid,)).fetchone())


def ensure_sequence_baseline(conn, sequence_id: int, step_order: int, row=None) -> dict:
    """Store the pre-edit copy once. Caller owns the surrounding transaction."""
    ensure_schema(conn)
    source_id = _source_id(sequence_id, step_order)
    existing = conn.execute(
        "SELECT * FROM copy_versions WHERE source_kind='sequence_step' AND source_id=?"
        " ORDER BY version LIMIT 1", (source_id,),
    ).fetchone()
    if existing:
        return dict(existing)
    row = row or conn.execute(
        "SELECT subject,body,day_offset FROM sequence_steps"
        " WHERE sequence_id=? AND step_order=?", (sequence_id, step_order),
    ).fetchone()
    if not row:
        raise LookupError("这一步不存在")
    return _insert_sequence_step(conn, sequence_id, step_order, row, change_kind="baseline")


def record_sequence_step(conn, sequence_id: int, step_order: int, *,
                         change_kind: str = "edit",
                         rollback_of_id: int | None = None) -> dict:
    row = conn.execute(
        "SELECT subject,body,day_offset FROM sequence_steps"
        " WHERE sequence_id=? AND step_order=?", (sequence_id, step_order),
    ).fetchone()
    if not row:
        raise LookupError("这一步不存在")
    return _insert_sequence_step(
        conn, sequence_id, step_order, row, change_kind=change_kind,
        rollback_of_id=rollback_of_id,
    )


def list_sequence_step(conn, sequence_id: int, step_order: int) -> list[dict]:
    ensure_schema(conn)
    return [dict(row) for row in conn.execute(
        "SELECT * FROM copy_versions WHERE source_kind='sequence_step' AND source_id=?"
        " ORDER BY version DESC", (_source_id(sequence_id, step_order),),
    )]


def rollback_sequence_step(conn, sequence_id: int, step_order: int,
                           version_id: int) -> dict:
    ensure_schema(conn)
    source_id = _source_id(sequence_id, step_order)
    version = conn.execute(
        "SELECT * FROM copy_versions WHERE id=? AND source_kind='sequence_step'"
        " AND source_id=?", (version_id, source_id),
    ).fetchone()
    if not version:
        raise LookupError("copy version not found")
    # Use the normal editor so a historical version cannot bypass today's safety guard.
    from app import sequence_edit
    sequence_edit.update_step(
        conn, sequence_id, step_order, subject=version["subject"], body=version["body"],
        day_offset=version["day_offset"], change_kind="rollback",
        rollback_of_id=version_id,
    )
    return list_sequence_step(conn, sequence_id, step_order)[0]
