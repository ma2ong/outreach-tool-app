"""Let the memory grow from everything that happens, not from one rare moment (docs/87).

`memory.py` describes what a salesperson remembers — what they wanted, where it stalled,
what not to say to them — and it was written carefully: each fact its own row, carrying
where it came from, so a synthesis returns changes and an item nobody touches survives.

It held zero rows. `memory.update` is called from exactly one place, `run._draft_proposal`,
which fires when a customer replies *and* the agent decides to draft an answer. That path
had run often enough to produce 1,105 proposals and never once written a memory.

Meanwhile the book already held 2,373 records of things that happened to customers:

    send_log             944
    activities         1,089
    relationship_events   301
    inbox_messages         39

Including 22 `fact` rows that read 「银行到账 USD 22,860（2026-08-26）」 — the single most
valuable thing to know about a company, and the letter that goes to them tomorrow has no
idea.

Nothing here calls a model. These are facts the book already recorded in plain language;
asking an LLM to restate them would add cost, latency and a chance to get them wrong.
Synthesis still owns what a reply *means* — this owns what happened.

Idempotent by evidence: an event already cited by a live item is not written again, so
this can run after every cycle and on a full catch-up without duplicating anything.
"""
from __future__ import annotations

import json
import re

from app.agent import memory

# What a person would carry forward. Deliberately not every send: "we sent letter 2" is
# already on the outreach row, and a memory that repeats the activity log is a memory
# nobody reads.
_FACT_KINDS = ("fact",)

# Facts our own tooling recorded about itself, not about the company. The crawler noting
# 「社媒动态：活动」 fifteen times, or the browser reporting 「facebook 主页看不了」, is
# pipeline bookkeeping — a person carries none of it into the next conversation, and
# fifteen identical profile items would bury the one that says they paid us $22,860.
_SELF_REFERENTIAL = re.compile(
    r"社媒动态|社媒主页上补到|主页看不了|页面是空的|抓取失败|采集|打不开")

MAX_CATCH_UP_LEADS = 2000


def _cited(conn, lead_no: int) -> set[str]:
    """Evidence refs already carried by this lead's live items."""
    refs: set[str] = set()
    for row in conn.execute(
            "SELECT evidence FROM lead_memory_items"
            " WHERE lead_no=? AND superseded_at IS NULL", (lead_no,)):
        try:
            refs.update(str(r) for r in json.loads(row["evidence"] or "[]"))
        except json.JSONDecodeError:
            continue
    return refs


def _pending(conn, lead_no: int) -> list[dict]:
    """Events about this lead that no memory item cites yet, oldest first."""
    cited = _cited(conn, lead_no)
    seen = {r["content"] for r in conn.execute(
        "SELECT content FROM lead_memory_items"
        " WHERE lead_no=? AND superseded_at IS NULL", (lead_no,))}
    out = []

    placeholders = ",".join("?" * len(_FACT_KINDS))
    for row in conn.execute(
            f"SELECT id, at, summary FROM relationship_events"
            f" WHERE lead_no=? AND kind IN ({placeholders}) ORDER BY at",
            (lead_no, *_FACT_KINDS)):
        ref = f"event:{row['id']}"
        summary = str(row["summary"] or "").strip()
        if ref in cited or not summary or _SELF_REFERENTIAL.search(summary):
            continue
        # The same sentence twice is one memory. Events repeat; what a person knows
        # does not.
        if summary in seen:
            continue
        seen.add(summary)
        # A payment, a role correction, a hard constraint — these do not expire, so they
        # are profile rather than log.
        out.append({"kind": "profile", "content": str(row["summary"]).strip(),
                    "evidence": ref})

    for row in conn.execute(
            "SELECT id, received_at, kind, intent, body FROM inbox_messages"
            " WHERE lead_no=? AND kind IN ('reply','bounce') ORDER BY received_at",
            (lead_no,)):
        ref = f"inbox:{row['id']}"
        if ref in cited:
            continue
        if row["kind"] == "bounce":
            out.append({"kind": "profile", "evidence": ref,
                        "content": "这个邮箱退过信，发之前先确认地址还有效。"})
            continue
        out.append({"kind": "log", "evidence": ref,
                    "content": _reply_line(row)})
    return out


def _reply_line(row) -> str:
    """What a person would write down about a reply: when, how it read, their words."""
    from app.agent import classify
    from app.reply_details import own_words

    when = str(row["received_at"] or "")[:10]
    label = classify.INTENTS.get(row["intent"], row["intent"]) if row["intent"] else ""
    said = " ".join(own_words(row["body"]).split())[:160]
    head = f"{when} 回复" + (f"（{label}）" if label else "")
    return f"{head}：{said}" if said else head


def remember(conn, lead_no: int) -> int:
    """Write the events this lead's memory is missing. Returns how many were written."""
    from app import relationship_events

    memory.ensure_schema(conn)
    relationship_events.ensure_schema(conn)
    written = 0
    now = memory._now()
    for item in _pending(conn, lead_no):
        conn.execute(
            "INSERT INTO lead_memory_items(lead_no, kind, content, origin, evidence,"
            " created_at, updated_at) VALUES (?,?,?,'event',?,?,?)",
            (lead_no, item["kind"], item["content"][:memory.MAX_CONTENT_CHARS],
             json.dumps([item["evidence"]]), now, now))
        written += 1
    if written:
        memory._retire_overflow(conn, lead_no)
        conn.commit()
        memory._sync_summary(conn, lead_no)
    return written


def catch_up(conn, limit: int = MAX_CATCH_UP_LEADS) -> dict:
    """Every lead that has an event and is missing it. Safe to run repeatedly."""
    from app import relationship_events

    memory.ensure_schema(conn)
    relationship_events.ensure_schema(conn)
    leads = [r["lead_no"] for r in conn.execute(
        "SELECT DISTINCT lead_no FROM ("
        "  SELECT lead_no FROM relationship_events WHERE kind='fact'"
        "  UNION SELECT lead_no FROM inbox_messages WHERE kind IN ('reply','bounce')"
        ") WHERE lead_no IS NOT NULL LIMIT ?", (limit,))]
    written = sum(remember(conn, no) for no in leads)
    return {"leads": len(leads), "written": written}
