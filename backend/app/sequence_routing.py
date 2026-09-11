"""Database-configured automatic Sequence routing (docs/113)."""
from __future__ import annotations

import datetime as dt

from app import copy_segments

SCHEMA = """
CREATE TABLE IF NOT EXISTS sequence_routing_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    enabled INTEGER NOT NULL DEFAULT 1,
    priority INTEGER NOT NULL DEFAULT 0,
    country TEXT,
    language TEXT,
    customer_type TEXT,
    sequence_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(sequence_id) REFERENCES sequences(id)
);
CREATE INDEX IF NOT EXISTS idx_sequence_routing_match
    ON sequence_routing_rules(enabled,priority,language,country,customer_type);
"""

KOREA = {"south korea", "korea", "republic of korea", "대한민국"}


def ensure_schema(conn) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def language_of(lead: dict) -> str:
    return "ko" if str(lead.get("country") or "").strip().lower() in KOREA else "en"


def _country(value: str | None) -> str | None:
    from app.discovery import country_key

    value = country_key(value)
    return value or None


def _validate_rule(conn, sequence_id: int, language: str | None,
                   customer_type: str | None) -> None:
    if language not in (None, "en", "ko"):
        raise ValueError("language must be en, ko or empty")
    if customer_type not in (None, *copy_segments.SEGMENTS):
        raise ValueError("unknown customer type")
    row = conn.execute("SELECT 1 FROM sequences WHERE id=?", (sequence_id,)).fetchone()
    if row is None:
        raise LookupError("sequence not found")


def add_rule(conn, sequence_id: int, *, enabled: bool = True, priority: int = 0,
             country: str | None = None, language: str | None = None,
             customer_type: str | None = None) -> int:
    ensure_schema(conn)
    _validate_rule(conn, sequence_id, language, customer_type)
    rule_id = conn.execute(
        "INSERT INTO sequence_routing_rules"
        "(enabled,priority,country,language,customer_type,sequence_id,created_at)"
        " VALUES (?,?,?,?,?,?,?)",
        (int(enabled), int(priority), _country(country), language, customer_type,
         sequence_id, dt.datetime.now(dt.UTC).isoformat()),
    ).lastrowid
    conn.commit()
    return int(rule_id)


def update_rule(conn, rule_id: int, *, sequence_id: int, enabled: bool,
                priority: int, country: str | None, language: str | None,
                customer_type: str | None) -> dict:
    ensure_schema(conn)
    _validate_rule(conn, sequence_id, language, customer_type)
    cur = conn.execute(
        "UPDATE sequence_routing_rules SET sequence_id=?,enabled=?,priority=?,country=?,"
        " language=?,customer_type=? WHERE id=?",
        (sequence_id, int(enabled), int(priority), _country(country), language,
         customer_type, rule_id),
    )
    if not cur.rowcount:
        conn.rollback()
        raise LookupError("routing rule not found")
    conn.commit()
    return next(row for row in list_rules(conn) if row["id"] == rule_id)


def list_rules(conn) -> list[dict]:
    ensure_schema(conn)
    seed_declared_routes(conn)
    return [dict(row) for row in conn.execute(
        "SELECT r.*,s.name AS sequence_name,s.channel AS sequence_channel,"
        " s.active AS sequence_active FROM sequence_routing_rules r"
        " JOIN sequences s ON s.id=r.sequence_id"
        " ORDER BY r.enabled DESC,r.priority DESC,r.id"
    )]


def replace_declared_route(conn, sequence_id: int, *, customer_type: str,
                           language: str, country: str | None = None,
                           priority: int = 100_000) -> int:
    """A newly declared UI route replaces only the same declared destination."""
    ensure_schema(conn)
    seed_declared_routes(conn)
    conn.execute(
        "UPDATE sequence_routing_rules SET enabled=0"
        " WHERE language=? AND customer_type=?"
        " AND COALESCE(country,'')=COALESCE(?,'')",
        (language, customer_type, _country(country)),
    )
    return add_rule(conn, sequence_id, priority=priority, country=country,
                    language=language, customer_type=customer_type)


def seed_declared_routes(conn) -> int:
    """Translate existing segment/language declarations without changing their winner."""
    ensure_schema(conn)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(sequences)")}
    if not {"segment", "korean"}.issubset(columns):
        return 0
    existing = {row[0] for row in conn.execute(
        "SELECT DISTINCT sequence_id FROM sequence_routing_rules")}
    made = 0
    from app.seed_sequences import name_for
    legacy_names = {
        name_for(segment, korean): (segment, "ko" if korean else "en")
        for korean in (False, True) for segment in copy_segments.SEGMENTS
    }
    for rank, row in enumerate(conn.execute(
        "SELECT id,name,segment,korean FROM sequences"
        " WHERE active=1 AND channel='email'"
        " ORDER BY CASE WHEN segment IS NULL THEN 1 ELSE 0 END,id"
    ).fetchall()):
        if row["id"] in existing:
            continue
        if row["segment"] is not None:
            segment = row["segment"]
            language = "ko" if row["korean"] else "en"
        else:
            legacy = legacy_names.get(row["name"])
            if legacy is None:
                continue
            segment, language = legacy
        # Explicit segment declarations beat legacy names, then lowest id wins.
        add_rule(conn, row["id"], priority=-rank,
                 language=language, customer_type=segment)
        made += 1
    return made


def explain(conn, lead: dict) -> dict:
    ensure_schema(conn)
    seed_declared_routes(conn)
    language = str(lead.get("routing_language") or language_of(lead))
    country = _country(lead.get("country"))
    customer_type = str(lead.get("customer_type") or copy_segments.segment_of(lead))
    rows = conn.execute(
        "SELECT r.*,s.name AS sequence_name,s.active,s.channel FROM sequence_routing_rules r"
        " JOIN sequences s ON s.id=r.sequence_id"
        " WHERE r.enabled=1 AND s.active=1 AND s.channel='email'"
        " ORDER BY r.priority DESC,r.id ASC"
    ).fetchall()

    def matches(row, wanted_type: str) -> bool:
        return (
            (row["country"] is None or _country(row["country"]) == country)
            and (row["language"] is None or row["language"] == language)
            and (row["customer_type"] is None or row["customer_type"] == wanted_type)
        )

    matches_in_order: list[dict] = []
    seen: set[int] = set()
    for wanted_type, level in ((customer_type, "customer_type"), ("general", "general")):
        for row in rows:
            if row["id"] not in seen and matches(row, wanted_type):
                item = dict(row)
                item["match_level"] = level
                matches_in_order.append(item)
                seen.add(row["id"])
    winner = matches_in_order[0] if matches_in_order else None
    return {
        "country": country, "language": language, "customer_type": customer_type,
        "sequence_id": int(winner["sequence_id"]) if winner else None,
        "sequence_name": winner["sequence_name"] if winner else None,
        "rule_id": int(winner["id"]) if winner else None,
        "matches": matches_in_order,
    }


def route(conn, lead: dict) -> int | None:
    return explain(conn, lead)["sequence_id"]
