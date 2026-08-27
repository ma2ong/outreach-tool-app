"""Which copy actually works, broken out by who read it (docs/69).

The only number available before this was "361 letters, 1 reply". It compresses four
markets, five customer types, three steps and two languages into one figure, so it
cannot answer the question anyone actually has: is the opener weak, is the list wrong,
is it the third letter that burns people, or does this work in the US and not in Korea?

Every adjustment made without that breakdown is a guess. Today's switch to angle two was
an informed guess, and still a guess.

A reply is credited to the last variant that reached this customer on this channel.
Imperfect — the earlier letters did work too — but stable, and the boundary is clean at
the moment the angle changes: replies after the switch belong to the new angle.
"""
from __future__ import annotations

import sqlite3

# Grouping keys the table can be cut by. Anything else is a typo, not a dimension.
DIMENSIONS = ("variant", "step", "audience", "market", "channel")


def _rows(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, params)]


def breakdown(conn, by: tuple[str, ...] = ("variant", "market"),
              days: int = 90) -> list[dict]:
    """Sends and replies grouped however you ask for them.

    Rows written before docs/69 have no variant and are excluded rather than counted as
    a group called NULL: they are unmeasured, not a variant that performed at zero.
    """
    for key in by:
        if key not in DIMENSIONS:
            raise ValueError(f"未知维度 {key}")
    cols = ", ".join(f"s.{k}" for k in by)
    sql = f"""
        SELECT {cols},
               COUNT(*) AS sent,
               COUNT(DISTINCT s.lead_no) AS leads,
               COUNT(DISTINCT CASE WHEN r.lead_no IS NOT NULL THEN s.lead_no END) AS replied
        FROM send_log s
        LEFT JOIN (
            SELECT DISTINCT lead_no, channel FROM outreach WHERE status='replied'
        ) r ON r.lead_no = s.lead_no AND r.channel = s.channel
        WHERE s.variant IS NOT NULL
          AND s.sent_at >= datetime('now', ?)
        GROUP BY {cols}
        ORDER BY sent DESC
    """
    out = []
    for row in _rows(conn, sql, (f"-{days} days",)):
        leads = row["leads"] or 0
        row["reply_rate"] = round(100.0 * (row["replied"] or 0) / leads, 1) if leads else 0.0
        out.append(row)
    return out


def unmeasured(conn, days: int = 90) -> int:
    """Letters sent before the experiment fields existed. Shown, never counted as zero."""
    return conn.execute(
        "SELECT COUNT(*) FROM send_log WHERE variant IS NULL"
        " AND sent_at >= datetime('now', ?)", (f"-{days} days",)).fetchone()[0]


def variant_for(lead_no: int, variants: list[str]) -> str | None:
    """Which arm this customer belongs to (docs/69 R3).

    Keyed on the lead number so a customer never switches arms between one letter and
    the next — an experiment where the same person sees both versions measures nothing.
    Splitting also means a bad new angle costs half a list rather than all of it, which
    is exactly what today's all-at-once switch to angle two risked.
    """
    if not variants:
        return None
    return variants[lead_no % len(variants)]
