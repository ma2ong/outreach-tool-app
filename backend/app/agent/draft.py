"""Reply drafting.

The hard part is not writing English — it is not writing things that are untrue. A cold
email that invents a lead time costs a customer; the same sentence in a reply, sent to
someone who is actively evaluating us, costs the deal. So the model gets everything we
genuinely know about this customer and an explicit refusal instruction for everything
else, and the output is checked for the specific numbers a model likes to invent
(prices, lead times, MOQ) before Allen ever sees it flagged as safe.

Nothing here sends. The product is a proposal (Spec 22 section 3).
"""
from __future__ import annotations

import re

from app.agent import llm, proposals

MAX_HISTORY = 6

SYSTEM = """You draft replies for Allen, founder of a Shenzhen LED display manufacturer,
answering a customer who replied to his outreach.

FACTS YOU MAY USE — nothing else exists:
- the customer's own words, quoted in the context below
- the notes taken from their website
- the opportunity fields and any quote we already sent them
- our product range: P0.7-P10 indoor and outdoor LED panels

Allen prices every deal himself. You never quote, never name an amount, never offer a
discount or a payment term, even one that appears in the context. If they are asking to
be quoted, say he will come back with it.

NEVER state a price, lead time, MOQ, production capacity, certification, warranty
period, or past project reference unless that exact value appears in the context.
When you do not have a number the customer asked for, say you will confirm and come
back with it. A sentence you cannot source is a defect, not a style choice.

VOICE: direct, short sentences, no marketing adjectives, no "we are pleased to".
Write the way a factory owner writes: answer the question, then ask the one question
that moves this forward. 120 words or fewer.
Do not describe the company as a leader, premier, or top supplier.
Write from "Shenzhen, China" without naming the company.

LANGUAGE: reply in the language the customer wrote in, but only English or Korean.
For any other language, reply in English.

Return JSON:
{"subject": "...", "body": "...", "language": "en|ko",
 "evidence": [{"claim": "<what you asserted>", "source": "<where it came from>"}],
 "open_questions": "<what you had to leave unanswered, or empty>"}"""

# Same facts, same refusals, different register. A DM formatted like an email — subject
# line, greeting, sign-off block — reads as a mail merge, which is the one thing a reply
# in a chat window must not look like.
SYSTEM_DM = SYSTEM.replace(
    """VOICE: direct, short sentences, no marketing adjectives, no "we are pleased to".
Write the way a factory owner writes: answer the question, then ask the one question
that moves this forward. 120 words or fewer.
Do not describe the company as a leader, premier, or top supplier.
Write from "Shenzhen, China" without naming the company.""",
    """VOICE: this is a chat message, not an email. No greeting line, no sign-off, no name
at the bottom. Answer the question, then ask the one question that moves this forward.
60 words or fewer — one or two sentences is normal here.
Do not describe the company as a leader, premier, or top supplier.
Say you are in Shenzhen, China only if it comes up naturally. Never name the company.
Leave "subject" as an empty string: chat messages do not have one.""")

# Numbers a model invents when it wants to sound helpful. Finding one is not proof of a
# fabrication, but it is proof this draft needs a human's eyes before it goes out.
_RISK_PATTERNS = [
    (re.compile(r"(?:US\$|\$|USD|EUR|€)\s?\d", re.I), "价格"),
    (re.compile(r"\b\d+\s*(?:-\s*\d+\s*)?(?:working\s+)?days?\b", re.I), "交期"),
    (re.compile(r"\b\d+\s*(?:-\s*\d+\s*)?weeks?\b", re.I), "交期"),
    (re.compile(r"\bMOQ\b|\bminimum order\b", re.I), "起订量"),
    (re.compile(r"\b\d+\s*(?:year|month)s?\s+warranty\b", re.I), "质保"),
]


def _fetch(conn, sql: str, params: tuple) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def system_for(channel: str) -> str:
    return SYSTEM_DM if channel in ("whatsapp", "instagram", "facebook") else SYSTEM


def build_context(conn, message: dict) -> dict:
    """Everything we actually know about this customer, and nothing we do not."""
    # Own the dependency rather than trusting FastAPI startup order: the agent also runs
    # from the poll loop and from scripts that only initialised the base schema.
    from app import opportunities, sales_documents
    opportunities.ensure_schema(conn)
    sales_documents.ensure_schema(conn)
    lead_no = message["lead_no"]
    lead = conn.execute(
        "SELECT no, company_en, country, city, website, brief, hook, target_fit, stage"
        " FROM leads WHERE no=?", (lead_no,)).fetchone()
    memory = proposals.get_memory(conn, lead_no)
    history = _fetch(
        conn,
        "SELECT kind, subject, body, received_at, intent FROM inbox_messages"
        " WHERE lead_no=? AND kind='reply' AND id != ?"
        " ORDER BY received_at DESC LIMIT ?", (lead_no, message["id"], MAX_HISTORY))
    sends = _fetch(
        conn,
        "SELECT channel, campaign, date(sent_at) AS day FROM send_log"
        " WHERE lead_no=? ORDER BY sent_at DESC LIMIT ?", (lead_no, MAX_HISTORY))
    opps = _fetch(
        conn,
        "SELECT title, stage, amount, currency, quantity, pixel_pitch, use_case,"
        " indoor_outdoor, width_m, height_m, destination, incoterm, next_action"
        " FROM opportunities WHERE lead_no=? ORDER BY updated_at DESC LIMIT 3", (lead_no,))
    quotes = _fetch(
        conn,
        "SELECT quote_no, status, currency, total, incoterm, lead_time, payment_terms,"
        " warranty, valid_until FROM quotes WHERE lead_no=? ORDER BY created_at DESC LIMIT 3",
        (lead_no,))
    from app.agent import social
    return {
        "lead": dict(lead) if lead else {},
        "memory": (memory or {}).get("summary", ""),
        "message": message,
        "history": history,
        "sends": sends,
        "opportunities": opps,
        "quotes": quotes,
        "thread": social.stored_thread(message),
    }


def _render(ctx: dict) -> str:
    lead = ctx["lead"]
    out = [
        f"CUSTOMER: {lead.get('company_en')} ({lead.get('city') or ''} {lead.get('country') or ''})",
        f"WEBSITE NOTES: {lead.get('brief') or '(none)'}",
    ]
    if ctx["memory"]:
        out.append(f"WHAT WE KNOW SO FAR: {ctx['memory']}")
    if ctx["opportunities"]:
        out.append("OPPORTUNITY FIELDS: " + "; ".join(
            ", ".join(f"{k}={v}" for k, v in o.items() if v not in (None, "", 0))
            for o in ctx["opportunities"]))
    else:
        out.append("OPPORTUNITY FIELDS: none recorded")
    if ctx["quotes"]:
        out.append("QUOTES ALREADY SENT: " + "; ".join(
            ", ".join(f"{k}={v}" for k, v in q.items() if v not in (None, "", 0))
            for q in ctx["quotes"]))
    else:
        out.append("QUOTES ALREADY SENT: none — we have never given this customer a price")
    if ctx["sends"]:
        out.append("WE CONTACTED THEM: " + "; ".join(
            f"{s['day']} {s['channel']} ({s['campaign']})" for s in ctx["sends"]))
    for h in ctx["history"]:
        out.append(f"EARLIER FROM CUSTOMER ({h.get('received_at') or '?'}): "
                   f"{(h.get('body') or '')[:600]}")
    m = ctx["message"]
    if ctx.get("thread"):
        from app.agent import social
        out.append("THE CHAT SO FAR (US = we sent it, THEM = the customer)\n"
                   + social.transcript(ctx["thread"])[-3000:]
                   + "\n\nAnswer their last message.")
    else:
        out.append(f"\nTHE MESSAGE TO ANSWER\nSubject: {m.get('subject') or ''}\n"
                   f"{(m.get('body') or '')[:2500]}")
    if m.get("intent"):
        out.append(f"(classified intent: {m['intent']})")
    return "\n\n".join(out)


def check_claims(body: str, ctx: dict) -> list[str]:
    """Flag numbers the draft states that the context does not contain."""
    known = " ".join(str(v) for q in ctx["quotes"] for v in q.values() if v is not None)
    known += " " + " ".join(str(v) for o in ctx["opportunities"] for v in o.values()
                            if v is not None)
    warnings = []
    for pattern, label in _RISK_PATTERNS:
        for hit in pattern.findall(body or ""):
            text = hit if isinstance(hit, str) else " ".join(hit)
            digits = re.findall(r"\d+", text)
            if digits and all(d in known for d in digits):
                continue
            warnings.append(f"{label}：草稿里出现「{text.strip()}」，上下文里查不到这个值")
            break
    return warnings


def build(conn, message: dict) -> dict:
    """Draft one reply. Returns the parsed model output plus our own warnings."""
    ctx = build_context(conn, message)
    from app.agent import learn
    system = system_for(message.get("channel") or "email") + learn.draft_guidance(conn)
    data = llm.complete_json(conn, "draft", system, _render(ctx))
    body = str(data.get("body") or "").strip()
    if not body:
        raise llm.LLMError("模型没有返回正文")
    return {
        "subject": str(data.get("subject") or "").strip(),
        "body": body,
        "language": str(data.get("language") or "en").strip(),
        "evidence": data.get("evidence") or [],
        "open_questions": str(data.get("open_questions") or "").strip(),
        "warnings": check_claims(body, ctx),
        "context": ctx,
        "backend": data.get("_llm_backend") or llm.backend_for(conn, "draft"),
        "fallback_from": data.get("_llm_fallback_from"),
    }
