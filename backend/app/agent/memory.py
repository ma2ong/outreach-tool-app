"""The running story of one customer.

Fields answer "what is true about this company". A person remembers something else:
what they wanted, where it stalled, what not to say to them. That is what makes the
next message sound like it came from someone who was there for the last one, so it is
kept as prose and rewritten after every real interaction.

Runs on the classify backend: summarising is cheap work, and it runs once per reply.
"""
from __future__ import annotations

from app.agent import llm, proposals

SYSTEM = """You maintain a salesperson's running memory of one B2B customer.

Rewrite the memory in at most 200 characters of plain English covering only what is
useful before the next message: who they are, what they want, where it is stuck, what
to say next, and anything to avoid. Use only facts present in the input. Drop anything
already obvious from the company record (name, country, grade). No bullet points.

Return JSON: {"summary": "..."}"""


def _render(ctx: dict, previous: str) -> str:
    lead = ctx["lead"]
    parts = [f"COMPANY: {lead.get('company_en')} — {lead.get('brief') or 'no website notes'}"]
    if previous:
        parts.append(f"PREVIOUS MEMORY: {previous}")
    if ctx["opportunities"]:
        parts.append("OPPORTUNITY: " + "; ".join(
            ", ".join(f"{k}={v}" for k, v in o.items() if v not in (None, "", 0))
            for o in ctx["opportunities"]))
    for h in ctx["history"]:
        parts.append(f"EARLIER FROM CUSTOMER: {(h.get('body') or '')[:400]}")
    m = ctx["message"]
    parts.append(f"NEWEST FROM CUSTOMER (intent: {m.get('intent') or '?'}): "
                 f"{(m.get('body') or '')[:1200]}")
    return "\n\n".join(parts)


def update(conn, ctx: dict) -> str:
    """Rewrite this lead's memory from the same context the draft used. Returns the
    summary, or '' when the backend is unavailable — memory is a nice-to-have, and its
    absence must never block a reply going out."""
    lead_no = ctx["lead"].get("no")
    if not lead_no:
        return ""
    existing = proposals.get_memory(conn, lead_no) or {}
    try:
        data = llm.complete_json(conn, "classify", SYSTEM,
                                 _render(ctx, existing.get("summary", "")))
    except (llm.LLMUnavailable, llm.LLMError):
        return existing.get("summary", "")
    summary = str(data.get("summary") or "").strip()
    if not summary:
        return existing.get("summary", "")
    proposals.set_memory(conn, lead_no, summary,
                         int(existing.get("source_count") or 0) + 1)
    return summary
