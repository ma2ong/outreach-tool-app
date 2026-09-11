"""Phase C: what Allen's decisions teach the agent.

There is exactly one honest source of feedback here, and it is not a score the model
gives itself. It is what Allen did: which proposals he rejected and why, and what he
changed in a draft before sending it. A rewritten sentence is a labelled example of the
difference between what the agent wrote and what actually goes to a customer.

Two rules keep this from becoming astrology:

1. An edit is evidence, not a prompt rule. Allen explicitly states and activates a
   scoped lesson; no sample count lets recent copy rewrite the Agent by itself.
2. Nothing is applied silently. Lessons are versioned, visible, scoped by market/channel
   and customer type, and can be retired without deleting their evidence.
"""
from __future__ import annotations

import datetime as dt
import json
import sqlite3

from app.agent import proposals

MIN_EXAMPLES = 5           # edited drafts before any are used as guidance
MAX_EXAMPLES = 6           # how many go into a prompt; more is cost, not accuracy
MIN_CAMPAIGN_SENDS = 25    # below this a reply rate is not a reply rate
CATEGORIES = ("fact", "sales_action", "tone", "timing")
STATUSES = ("candidate", "active", "retired")
CHANNELS = ("email", "whatsapp", "instagram", "facebook")

LESSON_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_learning_lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lineage_id INTEGER,
    version INTEGER NOT NULL,
    supersedes_id INTEGER,
    rule_text TEXT NOT NULL,
    category TEXT NOT NULL,
    channel TEXT,
    market TEXT,
    customer_type TEXT,
    source_proposal_ids TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'candidate',
    created_by TEXT NOT NULL DEFAULT 'allen',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    activated_at TEXT,
    retired_at TEXT
);
CREATE TABLE IF NOT EXISTS agent_learning_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    detail TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_learning_lessons_status_scope
    ON agent_learning_lessons(status,channel,market,customer_type);
CREATE INDEX IF NOT EXISTS idx_learning_events_lesson
    ON agent_learning_events(lesson_id,id);
"""


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def ensure_lesson_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(LESSON_SCHEMA)
    conn.commit()


def _lesson(row) -> dict:
    value = dict(row)
    try:
        value["source_proposal_ids"] = json.loads(value.get("source_proposal_ids") or "[]")
    except (TypeError, json.JSONDecodeError):
        value["source_proposal_ids"] = []
    count = len(set(value["source_proposal_ids"]))
    value["evidence_count"] = count
    value["evidence_strength"] = "sufficient" if count >= MIN_EXAMPLES else "insufficient"
    return value


def get_lesson(conn, lesson_id: int) -> dict | None:
    ensure_lesson_schema(conn)
    row = conn.execute("SELECT * FROM agent_learning_lessons WHERE id=?", (lesson_id,)).fetchone()
    return _lesson(row) if row else None


def list_lessons(conn, status: str | None = None) -> list[dict]:
    ensure_lesson_schema(conn)
    sql = "SELECT * FROM agent_learning_lessons"
    params: tuple = ()
    if status:
        if status not in STATUSES:
            raise ValueError("unknown lesson status")
        sql += " WHERE status=?"
        params = (status,)
    sql += " ORDER BY CASE status WHEN 'active' THEN 0 WHEN 'candidate' THEN 1 ELSE 2 END, updated_at DESC,id DESC"
    return [_lesson(row) for row in conn.execute(sql, params)]


def _validate_lesson(rule_text: str, category: str, channel: str | None) -> str:
    text = rule_text.strip()
    if not text:
        raise ValueError("lesson text required")
    if category not in CATEGORIES:
        raise ValueError("unknown lesson category")
    if channel not in (None, *CHANNELS):
        raise ValueError("unknown lesson channel")
    return text


def _event(conn, lesson_id: int, action: str, detail: str = "") -> None:
    conn.execute(
        "INSERT INTO agent_learning_events(lesson_id,action,detail,created_at) VALUES (?,?,?,?)",
        (lesson_id, action, detail, _now()),
    )


def create_lesson(conn, rule_text: str, *, category: str, channel: str | None = None,
                  market: str | None = None, customer_type: str | None = None,
                  source_proposal_ids: list[int] | None = None) -> dict:
    from app import countries
    ensure_lesson_schema(conn)
    text = _validate_lesson(rule_text, category, channel)
    ids = sorted({int(value) for value in (source_proposal_ids or [])})
    if ids:
        found = conn.execute(
            f"SELECT COUNT(*) FROM agent_proposals WHERE id IN ({','.join('?' * len(ids))})"
            " AND kind='reply_draft' AND original_payload IS NOT NULL", ids,
        ).fetchone()[0]
        if found != len(ids):
            raise ValueError("lesson evidence must be edited reply drafts")
    now = _now()
    cur = conn.execute(
        "INSERT INTO agent_learning_lessons(lineage_id,version,rule_text,category,channel,"
        " market,customer_type,source_proposal_ids,status,created_at,updated_at)"
        " VALUES (NULL,1,?,?,?,?,?,?,'candidate',?,?)",
        (text, category, channel, countries.normalize(market), customer_type,
         json.dumps(ids), now, now),
    )
    lesson_id = int(cur.lastrowid)
    conn.execute("UPDATE agent_learning_lessons SET lineage_id=? WHERE id=?", (lesson_id, lesson_id))
    _event(conn, lesson_id, "created")
    conn.commit()
    return get_lesson(conn, lesson_id)


def set_lesson_status(conn, lesson_id: int, status: str) -> dict:
    ensure_lesson_schema(conn)
    if status not in ("active", "retired"):
        raise ValueError("lesson status must be active or retired")
    current = get_lesson(conn, lesson_id)
    if not current:
        raise LookupError("lesson not found")
    if current["status"] == status:
        return current
    now = _now()
    activated = now if status == "active" else current.get("activated_at")
    retired = now if status == "retired" else None
    conn.execute(
        "UPDATE agent_learning_lessons SET status=?,activated_at=?,retired_at=?,updated_at=? WHERE id=?",
        (status, activated, retired, now, lesson_id),
    )
    _event(conn, lesson_id, "activated" if status == "active" else "retired")
    conn.commit()
    return get_lesson(conn, lesson_id)


def revise_lesson(conn, lesson_id: int, rule_text: str, *,
                  category: str | None = None, channel: str | None = None,
                  market: str | None = None, customer_type: str | None = None) -> dict:
    from app import countries
    ensure_lesson_schema(conn)
    old = get_lesson(conn, lesson_id)
    if not old:
        raise LookupError("lesson not found")
    next_category = category or old["category"]
    # None means preserve here; clearing scope is performed by creating a replacement.
    next_channel = old["channel"] if channel is None else channel
    text = _validate_lesson(rule_text, next_category, next_channel)
    next_market = old["market"] if market is None else countries.normalize(market)
    next_customer_type = old["customer_type"] if customer_type is None else customer_type
    now = _now()
    version = conn.execute(
        "SELECT COALESCE(MAX(version),0)+1 FROM agent_learning_lessons WHERE lineage_id=?",
        (old["lineage_id"],),
    ).fetchone()[0]
    conn.execute(
        "UPDATE agent_learning_lessons SET status='retired',retired_at=?,updated_at=? WHERE id=?",
        (now, now, lesson_id),
    )
    cur = conn.execute(
        "INSERT INTO agent_learning_lessons(lineage_id,version,supersedes_id,rule_text,category,"
        " channel,market,customer_type,source_proposal_ids,status,created_at,updated_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,'candidate',?,?)",
        (old["lineage_id"], version, lesson_id, text, next_category, next_channel,
         next_market, next_customer_type, json.dumps(old["source_proposal_ids"]), now, now),
    )
    new_id = int(cur.lastrowid)
    _event(conn, lesson_id, "superseded", str(new_id))
    _event(conn, new_id, "created", f"revision of {lesson_id}")
    conn.commit()
    return get_lesson(conn, new_id)


def lesson_events(conn, lesson_id: int) -> list[dict]:
    ensure_lesson_schema(conn)
    return [dict(row) for row in conn.execute(
        "SELECT * FROM agent_learning_events WHERE lesson_id=? ORDER BY id", (lesson_id,),
    )]


def _payload(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}


def edited_drafts(conn, limit: int = MAX_EXAMPLES) -> list[dict]:
    """Pairs of (what the agent wrote, what Allen sent), newest first."""
    proposals.ensure_schema(conn)
    rows = conn.execute(
        "SELECT p.id, p.decided_at, p.payload, p.original_payload, l.company_en, l.country,"
        " l.tags,l.target_fit,l.business,l.hook,l.brief"
        " FROM agent_proposals p LEFT JOIN leads l ON l.no=p.lead_no"
        " WHERE p.kind='reply_draft' AND p.status IN ('edited_approved','executed')"
        "   AND p.original_payload IS NOT NULL"
        " ORDER BY p.decided_at DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for r in rows:
        original = _payload(r["original_payload"])
        edited = _payload(r["payload"])
        agent = original.get("body", "").strip()
        allen = edited.get("body", "").strip()
        if agent and allen and agent != allen:
            from app import copy_segments
            out.append({"id": r["id"], "company": r["company_en"], "country": r["country"],
                        "channel": edited.get("channel") or original.get("channel") or "email",
                        "customer_type": copy_segments.segment_of(dict(r)),
                        "decided_at": r["decided_at"], "agent": agent, "allen": allen})
    return out


def rejections(conn, days: int = 90) -> list[dict]:
    """Why proposals get turned down, most common first."""
    proposals.ensure_schema(conn)
    rows = conn.execute(
        "SELECT kind, reject_reason, COUNT(*) c FROM agent_proposals"
        " WHERE status='rejected' AND reject_reason IS NOT NULL"
        "   AND decided_at >= ?"
        " GROUP BY kind, reject_reason ORDER BY c DESC",
        ((dt.datetime.now(dt.UTC) - dt.timedelta(days=days)).isoformat(),)).fetchall()
    return [{"kind": r["kind"], "reason": r["reject_reason"],
             "label": proposals.REJECT_REASONS.get(r["reject_reason"], r["reject_reason"]),
             "count": r["c"]} for r in rows]


def accuracy(conn) -> dict:
    """How often a proposal survives contact with Allen."""
    proposals.ensure_schema(conn)
    rows = {r["status"]: r["c"] for r in conn.execute(
        "SELECT status, COUNT(*) c FROM agent_proposals"
        " WHERE status IN ('executed','failed','rejected','expired') GROUP BY status")}
    edited = conn.execute(
        "SELECT COUNT(*) c FROM agent_proposals WHERE original_payload IS NOT NULL"
    ).fetchone()["c"]
    decided = sum(rows.get(k, 0) for k in ("executed", "rejected"))
    return {
        "decided": decided,
        "executed": rows.get("executed", 0),
        "rejected": rows.get("rejected", 0),
        "expired": rows.get("expired", 0),
        "failed": rows.get("failed", 0),
        "edited": edited,
        "accept_rate_pct": round(rows.get("executed", 0) * 100 / decided, 1) if decided else 0.0,
        "edit_rate_pct": round(edited * 100 / rows.get("executed", 1), 1)
        if rows.get("executed") else 0.0,
    }


def draft_guidance(conn, *, channel: str | None = None, country: str | None = None,
                   customer_type: str | None = None) -> str:
    """Only Allen-approved, scope-matching lessons enter a customer prompt."""
    from app import countries
    wanted_market = countries.normalize(country)
    matches = []
    for lesson in list_lessons(conn, "active"):
        if lesson["channel"] and lesson["channel"] != channel:
            continue
        if lesson["market"] and countries.normalize(lesson["market"]) != wanted_market:
            continue
        if lesson["customer_type"] and lesson["customer_type"] != customer_type:
            continue
        matches.append(lesson)
    if not matches:
        return ""
    lines = [f"- [{item['category']}] {item['rule_text']}" for item in matches[:8]]
    return ("\n\nALLEN-APPROVED DRAFTING LESSONS — apply only these scoped rules; "
            "they are not customer facts:\n" + "\n".join(lines))


# ---------------------------------------------------------------- what stopped working

def weak_campaigns(conn, days: int = 90) -> list[dict]:
    """Campaigns with enough volume to judge and a reply rate of zero.

    Volume gate first: two sends and no reply is not evidence of anything, and an agent
    that proposes killing things on two data points trains Allen to ignore it.
    """
    since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    rows = conn.execute(
        "SELECT s.campaign, s.channel, COUNT(DISTINCT s.lead_no) AS leads,"
        " COUNT(DISTINCT CASE WHEN o.status='replied' THEN s.lead_no END) AS replied,"
        " MAX(date(s.sent_at)) AS last_sent"
        " FROM send_log s LEFT JOIN outreach o"
        "   ON o.lead_no=s.lead_no AND o.channel=s.channel"
        " WHERE date(s.sent_at) >= ?"
        " GROUP BY s.campaign, s.channel"
        " HAVING leads >= ? AND replied = 0"
        " ORDER BY leads DESC", (since, MIN_CAMPAIGN_SENDS)).fetchall()
    return [dict(r) for r in rows]


def summary(conn) -> dict:
    examples = edited_drafts(conn, MAX_EXAMPLES)
    lessons = list_lessons(conn)
    learned_ids = {pid for lesson in lessons for pid in lesson["source_proposal_ids"]}
    for example in examples:
        example["learned"] = example["id"] in learned_ids
    return {
        "accuracy": accuracy(conn),
        "rejections": rejections(conn),
        "edited_examples": examples,
        "examples_needed": max(0, MIN_EXAMPLES - len(examples)),
        "guidance_active": any(item["status"] == "active" for item in lessons),
        "lessons": lessons,
        "lesson_categories": list(CATEGORIES),
        "weak_campaigns": weak_campaigns(conn),
    }
