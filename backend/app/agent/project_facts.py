"""Sourced LED requirement capture from customer messages.

This is deliberately deterministic. A model may summarize the prose elsewhere, but a
number enters the project record only when this module can point to the exact characters
the customer wrote. Conflicting values remain evidence; they are never auto-resolved.
"""
from __future__ import annotations

import datetime as dt
import re
import sqlite3


SCHEMA = """
CREATE TABLE IF NOT EXISTS project_fact_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_no INTEGER NOT NULL,
    opportunity_id INTEGER,
    source_message_id INTEGER NOT NULL,
    field TEXT NOT NULL,
    value TEXT NOT NULL,
    normalized_value TEXT NOT NULL,
    source_quote TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(source_message_id, field, normalized_value)
);
CREATE INDEX IF NOT EXISTS idx_project_fact_lead
    ON project_fact_evidence(lead_no, opportunity_id, field, id);
CREATE INDEX IF NOT EXISTS idx_project_fact_message
    ON project_fact_evidence(source_message_id);
"""

_DIMENSIONS = re.compile(
    r"\b(?P<w>\d+(?:\.\d+)?)\s*(?P<u1>m|meters?|metres?|ft|feet|foot)?\s*"
    r"(?:x|×|by)\s*(?P<h>\d+(?:\.\d+)?)\s*"
    r"(?P<u2>m|meters?|metres?|ft|feet|foot)?\b",
    re.I,
)
_PITCH = re.compile(r"\bP\s*(?P<value>\d+(?:\.\d+)?)\b", re.I)
_AREA = re.compile(r"\b(?P<value>\d+(?:\.\d+)?)\s*(?:m2|m²|sq\.?\s*m|sqm)\b", re.I)
_QUANTITY = re.compile(
    r"\b(?P<value>\d+)\s+(?:(?:indoor|outdoor)\s+)?"
    r"(?:screens?|displays?|sets?|units?|pcs?)\b",
    re.I,
)
_BRIGHTNESS = re.compile(r"\b(?P<value>\d{3,5})\s*(?:nits?|cd\s*/\s*m(?:2|²))\b", re.I)
_REFRESH = re.compile(r"\b(?P<value>\d{3,5})\s*hz\b", re.I)
_VIEWING = re.compile(
    r"\b(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>m|meters?|metres?|ft|feet|foot)"
    r"\s+(?:viewing\s+)?distance\b",
    re.I,
)
_TIMING = re.compile(r"\bQ(?P<quarter>[1-4])(?:\s*[-/]?\s*(?P<year>20\d{2}))?\b", re.I)
_ENVIRONMENT = re.compile(r"\b(indoor|outdoor)\b", re.I)


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def _number(value: str) -> str:
    number = float(value)
    return str(int(number)) if number.is_integer() else str(number)


def _metres(value: str, unit: str | None) -> float:
    number = float(value)
    if (unit or "").lower() in ("ft", "feet", "foot"):
        number *= 0.3048
    return round(number, 4)


def extract(body: str) -> list[dict]:
    """Return only literal, mechanically verifiable facts from one message."""
    text = body or ""
    facts: list[dict] = []

    def add(field: str, value, quote: str, typed=None) -> None:
        normalized = str(value).strip().lower()
        key = (field, normalized)
        if not normalized or any((row["field"], row["normalized_value"]) == key for row in facts):
            return
        facts.append({
            "field": field, "value": str(value), "normalized_value": normalized,
            "source_quote": quote.strip(), "typed_value": value if typed is None else typed,
        })

    for match in _ENVIRONMENT.finditer(text):
        value = match.group(1).lower()
        add("indoor_outdoor", value, match.group(0), value)
    for match in _PITCH.finditer(text):
        value = f"P{_number(match.group('value'))}"
        add("pixel_pitch", value, match.group(0), value)
    for match in _DIMENSIONS.finditer(text):
        if not (match.group("u1") or match.group("u2")):
            continue
        unit = match.group("u1") or match.group("u2")
        width = _metres(match.group("w"), match.group("u1") or unit)
        height = _metres(match.group("h"), match.group("u2") or unit)
        add("width_m", _number(str(width)), match.group(0), width)
        add("height_m", _number(str(height)), match.group(0), height)
    for pattern, field, caster in (
        (_AREA, "area_sqm", float),
        (_QUANTITY, "quantity", int),
        (_BRIGHTNESS, "brightness_nits", int),
        (_REFRESH, "refresh_rate_hz", int),
    ):
        for match in pattern.finditer(text):
            typed = caster(match.group("value"))
            add(field, _number(str(typed)), match.group(0), typed)
    for match in _VIEWING.finditer(text):
        value = _metres(match.group("value"), match.group("unit"))
        add("viewing_distance_m", _number(str(value)), match.group(0), value)
    for match in _TIMING.finditer(text):
        value = f"Q{match.group('quarter')}" + (f" {match.group('year')}" if match.group("year") else "")
        add("project_timing", value, match.group(0), value)
    return facts


def _single_open_opportunity(conn: sqlite3.Connection, lead_no: int) -> dict | None:
    from app import opportunities

    opportunities.ensure_schema(conn)
    rows = opportunities.list_all(conn, lead_no=lead_no)
    open_rows = [row for row in rows if row["stage"] in opportunities.OPEN_STAGES]
    return open_rows[0] if len(open_rows) == 1 else None


def _fill_empty_fields(conn: sqlite3.Connection, opportunity: dict | None,
                       facts: list[dict]) -> None:
    if not opportunity:
        return
    from app import opportunities

    allowed = {
        "pixel_pitch", "indoor_outdoor", "width_m", "height_m",
        "brightness_nits", "refresh_rate_hz", "viewing_distance_m", "project_timing",
        "quantity",
    }
    updates = {}
    by_field: dict[str, list[dict]] = {}
    for fact in facts:
        by_field.setdefault(fact["field"], []).append(fact)
    for field, rows in by_field.items():
        if field not in allowed or opportunity.get(field) not in (None, ""):
            continue
        values = {row["normalized_value"] for row in rows}
        if len(values) == 1:
            updates[field] = rows[0]["typed_value"]
    if updates:
        opportunities.update(conn, opportunity["id"], updates)


def capture(conn: sqlite3.Connection, message: dict) -> dict:
    ensure_schema(conn)
    lead_no = int(message["lead_no"])
    message_id = int(message["id"])
    opportunity = _single_open_opportunity(conn, lead_no)
    facts = extract(str(message.get("body") or ""))
    now = _now()
    for fact in facts:
        conn.execute(
            "INSERT INTO project_fact_evidence(lead_no,opportunity_id,source_message_id,"
            " field,value,normalized_value,source_quote,created_at) VALUES (?,?,?,?,?,?,?,?)"
            " ON CONFLICT(source_message_id,field,normalized_value) DO NOTHING",
            (lead_no, opportunity["id"] if opportunity else None, message_id,
             fact["field"], fact["value"], fact["normalized_value"],
             fact["source_quote"], now),
        )
    conn.commit()
    _fill_empty_fields(conn, opportunity, facts)
    return for_message(conn, message_id)


def _public(row: sqlite3.Row | dict) -> dict:
    item = dict(row)
    item["source_message_id"] = item.pop("source_message_id")
    return item


def for_message(conn: sqlite3.Connection, message_id: int) -> dict:
    ensure_schema(conn)
    rows = conn.execute(
        "SELECT id,lead_no,opportunity_id,source_message_id,field,value,"
        " normalized_value,source_quote,created_at FROM project_fact_evidence"
        " WHERE source_message_id=? ORDER BY id", (message_id,),
    ).fetchall()
    facts = [_public(row) for row in rows]
    return {"facts": facts, "conflicts": []}


def for_lead(conn: sqlite3.Connection, lead_no: int) -> dict:
    ensure_schema(conn)
    rows = conn.execute(
        "SELECT id,lead_no,opportunity_id,source_message_id,field,value,"
        " normalized_value,source_quote,created_at FROM project_fact_evidence"
        " WHERE lead_no=? ORDER BY id DESC", (lead_no,),
    ).fetchall()
    facts = [_public(row) for row in rows]
    grouped: dict[tuple[int | None, str], dict[str, dict]] = {}
    for fact in facts:
        grouped.setdefault((fact["opportunity_id"], fact["field"]), {})[
            fact["normalized_value"]
        ] = fact
    conflicts = []
    for (opportunity_id, field), variants in grouped.items():
        if len(variants) > 1:
            conflicts.append({
                "opportunity_id": opportunity_id, "field": field,
                "values": [row["value"] for row in variants.values()],
                "evidence": list(variants.values()),
            })
    return {"facts": facts, "conflicts": conflicts}
