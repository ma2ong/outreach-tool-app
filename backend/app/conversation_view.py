"""One customer's whole correspondence, in the order it happened (docs/56).

The inbox already lists what came in. What it cannot show is the other half — what we
said — because until `docs/56` R1 that text was never stored: `send_log` recorded which
sequence step went out and when, while the letter itself differed per lead through
{hook}.

So rows written before that change carry no body, and this reports them as
`body_missing`. Re-rendering the template with today's hook would produce a letter that
reads plausibly and was never sent; Allen would follow up on a sentence the customer
never saw. `docs/45`: a fact we cannot source is not a fact we may state.
"""
from __future__ import annotations

# Bounces and vacation autoresponders are system events, not the customer talking. They
# stay in the timeline — a bounce is why a thread went quiet — but folded away.
_QUIET_KINDS = {"auto", "bounce", "unsubscribe"}


def _rows(conn, sql: str, args: tuple) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, args)]


def timeline(conn, lead_no: int) -> list[dict]:
    """Everything said to and by this customer, oldest first."""
    from app.activities import ensure_schema as ensure_activities

    # activities is owned by its own module, so a fresh database has no such table yet.
    ensure_activities(conn)
    events: list[dict] = []

    for row in _rows(conn, "SELECT id, channel, campaign, sent_at, subject, body"
                           " FROM send_log WHERE lead_no=?", (lead_no,)):
        events.append({
            "kind": "sent", "id": row["id"], "channel": row["channel"],
            "at": row["sent_at"], "subject": row["subject"], "body": row["body"],
            "campaign": row["campaign"],
            # The distinction the UI must not blur: nothing to show, versus an empty
            # message. Only the first is true here.
            "body_missing": not row["body"],
            "quiet": False,
        })

    for row in _rows(conn, "SELECT id, channel, kind, from_addr, subject, body,"
                           " received_at, is_read FROM inbox_messages WHERE lead_no=?",
                     (lead_no,)):
        events.append({
            "kind": "received", "id": row["id"], "channel": row["channel"],
            "at": row["received_at"], "subject": row["subject"], "body": row["body"],
            "from": row["from_addr"], "message_kind": row["kind"],
            "is_read": bool(row["is_read"]), "body_missing": False,
            "quiet": row["kind"] in _QUIET_KINDS,
        })

    for row in _rows(conn, "SELECT id, type, title, note, created_at, completed_at,"
                           " status FROM activities WHERE lead_no=?", (lead_no,)):
        events.append({
            "kind": "activity", "id": row["id"], "at": row["created_at"],
            "activity_type": row["type"], "title": row["title"], "body": row["note"],
            "status": row["status"], "body_missing": False, "quiet": True,
        })

    # A row with no timestamp cannot be placed; it sorts last rather than silently
    # claiming the epoch, which would put it before the first contact.
    events.sort(key=lambda e: (e["at"] is None, e["at"] or ""))
    return events


def state(conn, lead_no: int) -> dict | None:
    """Whose turn it is, from the state machine that already exists."""
    from app.agent.conversation import ensure_schema

    ensure_schema(conn)
    row = conn.execute(
        "SELECT channel, owner, state, reason, next_action, due_at, updated_at"
        " FROM conversation_states WHERE lead_no=? ORDER BY updated_at DESC LIMIT 1",
        (lead_no,)).fetchone()
    return dict(row) if row else None


def summary(conn, lead_no: int) -> dict:
    events = timeline(conn, lead_no)
    said = [e for e in events if e["kind"] == "sent"]
    heard = [e for e in events if e["kind"] == "received" and not e["quiet"]]
    return {
        "lead_no": lead_no,
        "events": events,
        "state": state(conn, lead_no),
        "sent_count": len(said),
        "reply_count": len(heard),
        # Worth surfacing on its own: it is the reason most of this history reads thin.
        "missing_bodies": sum(1 for e in said if e["body_missing"]),
        "last_at": events[-1]["at"] if events else None,
    }
