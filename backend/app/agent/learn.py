"""Phase C: what Allen's decisions teach the agent.

There is exactly one honest source of feedback here, and it is not a score the model
gives itself. It is what Allen did: which proposals he rejected and why, and what he
changed in a draft before sending it. A rewritten sentence is a labelled example of the
difference between what the agent wrote and what actually goes to a customer.

Two rules keep this from becoming astrology:

1. Nothing is applied until there is enough of it. `MIN_EXAMPLES` edited drafts before
   any of them are shown to the model; below that the sample is noise and copying it
   would make the agent worse in a way that is hard to notice.
2. Nothing is applied silently. What the agent learned is readable on the Agent page in
   the same words as the examples themselves, so a bad lesson can be seen and deleted.
"""
from __future__ import annotations

import datetime as dt
import json

from app.agent import proposals

MIN_EXAMPLES = 5           # edited drafts before any are used as guidance
MAX_EXAMPLES = 6           # how many go into a prompt; more is cost, not accuracy
MIN_CAMPAIGN_SENDS = 25    # below this a reply rate is not a reply rate


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
        "SELECT p.id, p.decided_at, p.payload, p.original_payload, l.company_en, l.country"
        " FROM agent_proposals p LEFT JOIN leads l ON l.no=p.lead_no"
        " WHERE p.kind='reply_draft' AND p.status IN ('edited_approved','executed')"
        "   AND p.original_payload IS NOT NULL"
        " ORDER BY p.decided_at DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for r in rows:
        agent = _payload(r["original_payload"]).get("body", "").strip()
        allen = _payload(r["payload"]).get("body", "").strip()
        if agent and allen and agent != allen:
            out.append({"id": r["id"], "company": r["company_en"], "country": r["country"],
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


def draft_guidance(conn) -> str:
    """Few-shot guidance for the drafting prompt, or '' while the sample is too small."""
    examples = edited_drafts(conn, MAX_EXAMPLES)
    if len(examples) < MIN_EXAMPLES:
        return ""
    blocks = []
    for e in examples:
        blocks.append(f"--- {e.get('company') or 'a customer'}\n"
                      f"YOU WROTE: {e['agent'][:600]}\n"
                      f"ALLEN SENT: {e['allen'][:600]}")
    return ("\n\nHOW ALLEN REWRITES YOUR DRAFTS — match the second version's habits "
            "(length, directness, what he cuts, what he adds). These are real replies "
            "he sent:\n" + "\n\n".join(blocks))


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
    return {
        "accuracy": accuracy(conn),
        "rejections": rejections(conn),
        "edited_examples": examples,
        "examples_needed": max(0, MIN_EXAMPLES - len(examples)),
        "guidance_active": len(examples) >= MIN_EXAMPLES,
        "weak_campaigns": weak_campaigns(conn),
    }
