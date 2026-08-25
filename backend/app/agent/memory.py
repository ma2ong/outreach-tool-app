"""The running story of one customer, kept as sourced items rather than rewritten prose.

Fields answer "what is true about this company". A person remembers something else:
what they wanted, where it stalled, what not to say to them. That is what makes the
next message sound like it came from someone who was there for the last one.

It used to be one 200-character paragraph, rewritten end to end after every reply. That
shape forgets: 200 characters cannot hold three months, so each rewrite silently dropped
whatever the model did not happen to restate, and nothing recorded that it had ever been
there. Now each fact is its own row, carrying where it came from, and a synthesis returns
*changes* — an item nobody touches survives untouched.

`summary` is still what draft.py and the API read; it is rendered from the items now
instead of being the thing that gets rewritten.

Runs on the classify backend: summarising is cheap work, and it runs once per reply.
"""
from __future__ import annotations

import datetime as dt
import json
import re

from app.agent import llm, proposals

KINDS = ("profile", "log")
MAX_CHANGES_PER_SYNTHESIS = 12
MAX_CONTENT_CHARS = 500
MAX_ITEMS_PER_LEAD = 40
MAX_EVIDENCE_BODY_CHARS = 1200

SCHEMA = """
CREATE TABLE IF NOT EXISTS lead_memory_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_no INTEGER NOT NULL,
    kind TEXT NOT NULL DEFAULT 'log',
    content TEXT NOT NULL,
    origin TEXT NOT NULL DEFAULT 'synthesized',
    evidence TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    superseded_at TEXT,
    FOREIGN KEY(lead_no) REFERENCES leads(no) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_memory_items_lead
    ON lead_memory_items(lead_no, superseded_at);
"""

SYSTEM = """You maintain a salesperson's memory of one B2B customer as a set of items.

Return JSON: {"changes": [...]}. Each change is one of:
- {"action":"create","kind":"profile"|"log","content":"...","evidence":["inbox:12"]}
- {"action":"update","id":<existing id>,"content":"...","evidence":["inbox:12"]}
- {"action":"remove","id":<existing id>,"evidence":["inbox:12"]}

Rules:
1. Return only what changed. Items you do not mention are kept as they are; never
   restate an unchanged item, and never remove one just to tidy up.
2. kind "profile" is durable: who they are, how they buy, what they prefer, hard
   constraints, relationships. kind "log" is time-bound: projects, decisions, quotes,
   travel, where this deal is stuck right now.
3. Every change must cite evidence IDs from the EVIDENCE section. A fact you cannot
   source does not go in. Do not cite an ID that is not listed there.
4. Items marked [ALLEN] were written by the salesperson himself. Use them as context.
   Never update or remove one.
5. Today's date is given. A dated plan may be rewritten as past when the clock has
   passed it, but never assert that it happened — only the customer can tell us that.
6. State only what the input says. Do not infer motives, do not infer religion,
   politics or health, and do not read silence as disinterest. When unsure, leave it out.
7. Remove an item only when newer evidence contradicts or supersedes it.
8. Each content is one standalone fact in plain English, under 500 characters.
   Drop anything already obvious from the company record (name, country, grade)."""

_EVIDENCE_RE = re.compile(r"^(inbox|note):(\d+)$")
_EVIDENCE_TABLE = {"inbox": "inbox_messages", "note": "notes"}


def ensure_schema(conn) -> None:
    proposals.ensure_schema(conn)
    conn.executescript(SCHEMA)
    conn.commit()


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def _known_evidence(conn, refs: list[str]) -> set[str]:
    """The subset of `refs` that names a row that actually exists.

    Checked against the tables rather than trusted, because an ID the model invented is
    exactly how an unsourced fact would slip in wearing a citation.
    """
    found: set[str] = set()
    for ref in refs:
        match = _EVIDENCE_RE.match(str(ref).strip())
        if not match:
            continue
        table = _EVIDENCE_TABLE[match.group(1)]
        row = conn.execute(f"SELECT 1 FROM {table} WHERE id=?", (int(match.group(2)),)).fetchone()
        if row:
            found.add(f"{match.group(1)}:{int(match.group(2))}")
    return found


def items(conn, lead_no: int, include_superseded: bool = False) -> list[dict]:
    ensure_schema(conn)
    sql = ("SELECT * FROM lead_memory_items WHERE lead_no=?"
           + ("" if include_superseded else " AND superseded_at IS NULL")
           + " ORDER BY CASE kind WHEN 'profile' THEN 0 ELSE 1 END, id")
    return [dict(row) for row in conn.execute(sql, (lead_no,))]


def _retire_overflow(conn, lead_no: int) -> None:
    """Keep the memory bounded from the oldest `log` up.

    A durable fact and one Allen wrote himself are never retired by a cap: they are the
    part that is still true after the project they were written for is over.
    """
    live = conn.execute(
        "SELECT id FROM lead_memory_items WHERE lead_no=? AND superseded_at IS NULL"
        " AND kind='log' AND origin='synthesized' ORDER BY id", (lead_no,)).fetchall()
    total = conn.execute(
        "SELECT COUNT(*) c FROM lead_memory_items WHERE lead_no=? AND superseded_at IS NULL",
        (lead_no,)).fetchone()["c"]
    excess = total - MAX_ITEMS_PER_LEAD
    for row in live[:max(0, excess)]:
        conn.execute("UPDATE lead_memory_items SET superseded_at=? WHERE id=?",
                     (_now(), row["id"]))


def _render_summary(conn, lead_no: int) -> str:
    """One line per item, durable facts first: the shape draft.py has always been given."""
    return " ".join(item["content"] for item in items(conn, lead_no))


def _sync_summary(conn, lead_no: int) -> str:
    summary = _render_summary(conn, lead_no)
    count = conn.execute(
        "SELECT COUNT(*) c FROM lead_memory_items WHERE lead_no=? AND superseded_at IS NULL",
        (lead_no,)).fetchone()["c"]
    proposals.set_memory(conn, lead_no, summary, count)
    return summary


def write_explicit(conn, lead_no: int, content: str, kind: str = "profile") -> dict:
    """A memory Allen wrote himself. Synthesis may read it and may never touch it."""
    ensure_schema(conn)
    text = str(content or "").strip()[:MAX_CONTENT_CHARS]
    if not text:
        raise ValueError("记忆内容不能为空")
    now = _now()
    cur = conn.execute(
        "INSERT INTO lead_memory_items(lead_no, kind, content, origin, evidence,"
        " created_at, updated_at) VALUES (?,?,?,'explicit','[]',?,?)",
        (lead_no, kind if kind in KINDS else "profile", text, now, now))
    conn.commit()
    _sync_summary(conn, lead_no)
    return dict(conn.execute("SELECT * FROM lead_memory_items WHERE id=?",
                             (cur.lastrowid,)).fetchone())


def forget(conn, lead_no: int, item_id: int) -> bool:
    """Allen retiring a memory by hand — the only path that may touch an explicit item."""
    ensure_schema(conn)
    cur = conn.execute(
        "UPDATE lead_memory_items SET superseded_at=?, updated_at=?"
        " WHERE id=? AND lead_no=? AND superseded_at IS NULL", (_now(), _now(), item_id, lead_no))
    conn.commit()
    if cur.rowcount:
        _sync_summary(conn, lead_no)
    return bool(cur.rowcount)


def apply_changes(conn, lead_no: int, changes: list[dict]) -> dict:
    """Apply a synthesis result. Anything unsourced, out of bounds or aimed at an
    explicit item is dropped whole rather than trimmed into something half true."""
    ensure_schema(conn)
    applied = rejected = 0
    now = _now()
    for change in list(changes)[:MAX_CHANGES_PER_SYNTHESIS]:
        if not isinstance(change, dict):
            rejected += 1
            continue
        action = str(change.get("action") or "").strip()
        evidence = _known_evidence(conn, list(change.get("evidence") or []))
        if action not in ("create", "update", "remove") or not evidence:
            rejected += 1
            continue
        if action == "create":
            content = str(change.get("content") or "").strip()[:MAX_CONTENT_CHARS]
            if not content:
                rejected += 1
                continue
            kind = change.get("kind") if change.get("kind") in KINDS else "log"
            conn.execute(
                "INSERT INTO lead_memory_items(lead_no, kind, content, origin, evidence,"
                " created_at, updated_at) VALUES (?,?,?,'synthesized',?,?,?)",
                (lead_no, kind, content, json.dumps(sorted(evidence)), now, now))
            applied += 1
            continue
        row = conn.execute(
            "SELECT id, origin FROM lead_memory_items WHERE id=? AND lead_no=?"
            " AND superseded_at IS NULL", (change.get("id"), lead_no)).fetchone()
        # An explicit item is Allen's; a missing one may already have been superseded.
        if row is None or row["origin"] == "explicit":
            rejected += 1
            continue
        if action == "remove":
            conn.execute(
                "UPDATE lead_memory_items SET superseded_at=?, updated_at=?, evidence=?"
                " WHERE id=?", (now, now, json.dumps(sorted(evidence)), row["id"]))
            applied += 1
            continue
        content = str(change.get("content") or "").strip()[:MAX_CONTENT_CHARS]
        if not content:
            rejected += 1
            continue
        conn.execute(
            "UPDATE lead_memory_items SET content=?, evidence=?, updated_at=? WHERE id=?",
            (content, json.dumps(sorted(evidence)), now, row["id"]))
        applied += 1
    rejected += max(0, len(changes) - MAX_CHANGES_PER_SYNTHESIS)
    _retire_overflow(conn, lead_no)
    conn.commit()
    summary = _sync_summary(conn, lead_no)
    return {"applied": applied, "rejected": rejected, "summary": summary}


def _render(conn, ctx: dict) -> str:
    """The prompt input: current items with their IDs, then the evidence they may cite."""
    lead = ctx["lead"]
    parts = [f"TODAY: {dt.date.today().isoformat()}",
             f"COMPANY: {lead.get('company_en')} — {lead.get('brief') or 'no website notes'}"]
    current = items(conn, lead.get("no"))
    if current:
        parts.append("CURRENT MEMORY:\n" + "\n".join(
            f"- id={item['id']} [{item['kind']}]"
            f"{' [ALLEN]' if item['origin'] == 'explicit' else ''} {item['content']}"
            for item in current))
    if ctx.get("opportunities"):
        parts.append("OPPORTUNITY: " + "; ".join(
            ", ".join(f"{k}={v}" for k, v in o.items() if v not in (None, "", 0))
            for o in ctx["opportunities"]))
    evidence = []
    for h in ctx.get("history") or []:
        if h.get("id"):
            evidence.append(f"inbox:{h['id']} (earlier) {(h.get('body') or '')[:400]}")
    message = ctx.get("message") or {}
    if message.get("id"):
        evidence.append(f"inbox:{message['id']} (newest, intent: {message.get('intent') or '?'})"
                        f" {(message.get('body') or '')[:MAX_EVIDENCE_BODY_CHARS]}")
    parts.append("EVIDENCE (cite only these IDs):\n" + ("\n".join(evidence) or "(none)"))
    return "\n\n".join(parts)


def update(conn, ctx: dict) -> str:
    """Synthesise this lead's memory from the same context the draft used. Returns the
    summary, or the existing one when the backend is unavailable — memory is a
    nice-to-have, and its absence must never block a reply going out."""
    lead_no = ctx["lead"].get("no")
    if not lead_no:
        return ""
    ensure_schema(conn)
    existing = _render_summary(conn, lead_no)
    try:
        data = llm.complete_json(conn, "classify", SYSTEM, _render(conn, ctx))
    except (llm.LLMUnavailable, llm.LLMError):
        return existing
    changes = data.get("changes")
    if not isinstance(changes, list) or not changes:
        return existing
    return apply_changes(conn, lead_no, changes)["summary"]
