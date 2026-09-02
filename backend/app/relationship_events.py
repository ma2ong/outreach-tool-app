"""Everything that happened on one relationship, in one place (docs/68 part 1).

A relationship currently lives across six tables — `outreach`, `send_log`,
`sequence_enrollments`, `social_dm_queue`, `inbox_messages`, `activities` — so the
conversation view has to reassemble it on every read, and a fact that belongs to none of
them (a phone number found while prospecting) has nowhere to go at all.

This is a place for the whole story, added beside those tables rather than instead of
them. They stay authoritative: every existing writer keeps writing exactly what it wrote
before, and this is written afterwards. That order matters — **recording history must
never be able to break the thing it is recording**, so every call here swallows its own
errors. A missing event line is a gap in a report; a raised exception here would be a
letter that did not go out.
"""
from __future__ import annotations

import datetime as _dt
import json
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS relationship_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_no INTEGER NOT NULL,
    at TEXT NOT NULL,
    kind TEXT NOT NULL,
    channel TEXT,
    summary TEXT NOT NULL,
    detail_json TEXT,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rel_events_lead ON relationship_events(lead_no, at);
CREATE INDEX IF NOT EXISTS idx_rel_events_kind ON relationship_events(kind, at);
"""

# What can happen on a relationship. A closed list, because "kind" is what the timeline
# groups and filters by, and a free-text one drifts into six spellings of "sent".
KINDS = (
    "sent",         # we wrote to them
    "received",     # they wrote back
    "bounced",      # the address is dead
    "fact",         # we learned something about them
    "stage",        # where the deal stands changed
    "task",         # a piece of work was finished on this account
)

SOURCES = ("agent", "allen", "import", "discovery")


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def record(conn, lead_no: int, kind: str, summary: str, *, source: str = "agent",
           channel: str | None = None, detail: dict | None = None,
           at: str | None = None) -> int | None:
    """Add one event. Returns its id, or None when it could not be written.

    Never raises. This is a bystander to the work it describes: a send that succeeded
    and then failed to be written down is still a send, and turning that into an
    exception would lose the letter to save the note about it.
    """
    try:
        ensure_schema(conn)
        now = _dt.datetime.now(_dt.UTC).isoformat()
        cur = conn.execute(
            "INSERT INTO relationship_events(lead_no, at, kind, channel, summary,"
            " detail_json, source, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (lead_no, at or now, kind, channel, summary,
             json.dumps(detail, ensure_ascii=False) if detail else None, source, now))
        conn.commit()
        # docs/87. A durable fact about a company — a payment, a correction, a hard
        # constraint — is exactly what the next letter should already know. Recording it
        # here rather than waiting for a synthesis is why the memory was empty for months.
        if kind == "fact" and lead_no:
            try:
                from app.agent import memory_events
                memory_events.remember(conn, lead_no)
            except Exception:  # noqa: BLE001 — same rule: never lose the event
                pass
        return cur.lastrowid
    except Exception:  # noqa: BLE001 — see the docstring; this must not propagate
        return None


def timeline(conn, lead_no: int, limit: int = 200) -> list[dict]:
    """This relationship's events, oldest first."""
    try:
        ensure_schema(conn)
    except Exception:  # noqa: BLE001
        return []
    rows = conn.execute(
        "SELECT id, at, kind, channel, summary, detail_json, source"
        " FROM relationship_events WHERE lead_no=? ORDER BY at, id LIMIT ?",
        (lead_no, limit)).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        raw = item.pop("detail_json", None)
        try:
            item["detail"] = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            item["detail"] = None
        out.append(item)
    return out


def recent(conn, kind: str | None = None, days: int = 1, limit: int = 200) -> list[dict]:
    """What happened lately, for the daily report."""
    try:
        ensure_schema(conn)
    except Exception:  # noqa: BLE001
        return []
    sql = ("SELECT e.*, l.company_en FROM relationship_events e"
           " LEFT JOIN leads l ON l.no = e.lead_no"
           " WHERE e.at >= datetime('now', ?)")
    params: list = [f"-{days} days"]
    if kind:
        sql += " AND e.kind = ?"
        params.append(kind)
    sql += " ORDER BY e.at DESC LIMIT ?"
    params.append(limit)
    return [dict(r) for r in conn.execute(sql, params)]


def count_today(conn, kind: str) -> int:
    try:
        ensure_schema(conn)
        return conn.execute(
            "SELECT COUNT(*) FROM relationship_events"
            " WHERE kind=? AND date(at)=date('now')", (kind,)).fetchone()[0]
    except Exception:  # noqa: BLE001
        return 0
