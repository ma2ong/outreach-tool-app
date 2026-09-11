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

import json
import re

from app.agent import llm, proposals

MAX_HISTORY = 6

SYSTEM = """You draft replies for Allen, founder of a Shenzhen LED display manufacturer,
answering a customer who replied to his outreach.

FACTS YOU MAY USE — nothing else exists:
- the customer's own words, quoted in the context below
- the notes taken from their website
- the opportunity fields and any quote we already sent them
- exact product facts inside APPROVED PRODUCT FACTS, when that section exists
- exact project facts inside APPROVED SHAREABLE CASES, when that section exists

Do NOT infer a product specification from a model name, price range, application label,
or a missing field. If APPROVED PRODUCT FACTS says a field is missing or has a gap,
treat it as unknown. If product guidance says more project facts are needed, do not turn
that into a recommendation.

APPROVED SHAREABLE CASES are the only past-project references you may mention. Never use
customer names, quote/order history, CRM notes, or an internal project name as a case.
Use only the public label/summary and exact fields shown in that section.

Allen prices every deal himself. You never quote, never name an amount, never offer a
discount or a payment term, even one that appears in the context. If they are asking to
be quoted, say he will come back with it.

NEVER state a price, lead time, MOQ, production capacity, certification, warranty
period, or past project reference unless that exact value appears in the permitted
customer-facing facts above. When you do not have a number the customer asked for, say
you will confirm and come back with it. A sentence you cannot source is a defect, not a
style choice.

When the context contains an LED SALES COACH section, it is a deterministic sales
qualification guide, not a source of new facts. After answering the customer's current
question, prefer its NEXT QUESTION as the single follow-up question if that question is
still unanswered by the customer's latest message. Do not dump the whole missing-field
list on the customer. Do not turn a missing value into a recommendation by guessing it.

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

FOLLOWUP_SYSTEM = """You draft one short follow-up after an LED display prospect replied,
we answered, and they have been silent for seven days. Use only the supplied customer
words, our last sent reply, CRM facts, APPROVED PRODUCT FACTS and APPROVED SHAREABLE CASES.
Never invent or imply a price, discount, payment term, delivery promise, lead time, MOQ,
warranty, certification or technical value. Do not say "just following up". Refer to
the concrete project/question already in the conversation and ask one easy next-step
question. Do not add a new promise. English or Korean, matching the customer. Email is
70 words or fewer; chat is 35 words or fewer. Return JSON with the same fields as the
reply drafter: subject, body, language, evidence and open_questions."""

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
    from app import case_library, opportunities, sales_documents
    from app.agent import led_playbook, product_advisor, project_facts
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
        "SELECT id, lead_no, title, stage, amount, currency, quantity, pixel_pitch, use_case,"
        " indoor_outdoor, width_m, height_m, viewing_distance_m, brightness_nits,"
        " refresh_rate_hz, maintenance_access, cabinet_size, control_system,"
        " installation_type, project_timing, budget_range, decision_process,"
        " technical_notes, destination, incoterm, next_action, next_action_date"
        " FROM opportunities WHERE lead_no=? ORDER BY updated_at DESC LIMIT 3", (lead_no,))
    qualification = None
    product_guidance = None
    case_guidance = []
    active_opportunity = None
    for opportunity in opps:
        if opportunity.get("stage") not in ("won", "lost"):
            active_opportunity = opportunity
            qualification = led_playbook.qualification(opportunity)
            advice = product_advisor.advise(conn, opportunity, limit=3)
            product_guidance = product_advisor.customer_safe_context(advice)
            case_guidance = case_library.customer_safe_matches(conn, opportunity, limit=2)
            break
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
        "active_opportunity": active_opportunity,
        "qualification_guidance": qualification,
        "product_guidance": product_guidance,
        "case_guidance": case_guidance,
        "quotes": quotes,
        "project_facts": project_facts.for_lead(conn, lead_no),
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
    sourced = ctx.get("project_facts") or {}
    if sourced.get("facts"):
        seen = set()
        lines = []
        for fact in sourced["facts"]:
            key = (fact.get("field"), fact.get("normalized_value"))
            if key in seen:
                continue
            seen.add(key)
            lines.append(
                f"{fact['field']}={fact['value']} (inbox:{fact['source_message_id']}; "
                f"exact quote: {fact['source_quote']})"
            )
            if len(lines) >= 20:
                break
        out.append("CUSTOMER-STATED PROJECT FACTS (literal, sourced):\n" + "\n".join(lines))
        if sourced.get("conflicts"):
            conflicts = "; ".join(
                f"{item['field']} has {', '.join(item['values'])}"
                for item in sourced["conflicts"][:8]
            )
            out.append(
                "PROJECT FACT CONFLICT — do not choose a value; ask the customer to confirm: "
                + conflicts
            )
    else:
        out.append("CUSTOMER-STATED PROJECT FACTS: none")
    guide = ctx.get("qualification_guidance")
    if guide:
        missing = ", ".join(item["label"] for item in guide["missing"][:8]) or "none"
        out.append(
            "LED SALES COACH (guidance only; these are NOT customer facts): "
            f"application={guide['application']}; qualification={guide['completeness']}%; "
            f"missing={missing}; NEXT QUESTION={guide.get('next_question') or 'none'}")
    products = ctx.get("product_guidance")
    if products:
        lines = [
            f"status={products.get('status')}; qualification={products.get('qualification_pct')}%; "
            f"ready_to_recommend={products.get('ready_to_recommend')}; reason={products.get('reason') or 'none'}"
        ]
        for product in products.get("products", []):
            facts = ", ".join(f"{k}={v}" for k, v in product.get("facts", {}).items()) or "no approved technical facts"
            gaps = "; ".join(product.get("gaps", [])) or "none"
            lines.append(f"PRODUCT {product.get('model')}: facts[{facts}]; gaps[{gaps}]")
        out.append("APPROVED PRODUCT FACTS (customer-safe; no prices or private history):\n" + "\n".join(lines))
    else:
        out.append("APPROVED PRODUCT FACTS: none")
    cases = ctx.get("case_guidance") or []
    if cases:
        lines = []
        for case in cases:
            lines.append(", ".join(f"{k}={v}" for k, v in case.items() if v not in (None, "", 0)))
        out.append("APPROVED SHAREABLE CASES (human-approved external references only):\n" + "\n".join(lines))
    else:
        out.append("APPROVED SHAREABLE CASES: none")
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
    attachments = m.get("attachments")
    if attachments is None:
        try:
            attachments = json.loads(m.get("attachments_json") or "[]")
        except (TypeError, ValueError):
            attachments = []
    if attachments:
        labels = ", ".join(
            f"{item.get('filename') or 'unnamed'} ({item.get('content_type') or 'unknown'}, "
            f"{int(item.get('size') or 0)} bytes)" for item in attachments[:20]
        )
        out.append(
            "UNPARSED ATTACHMENTS (metadata only; do not infer their content): " + labels
        )
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
    for product in (ctx.get("product_guidance") or {}).get("products", []):
        known += " " + " ".join(str(v) for v in product.get("facts", {}).values() if v is not None)
    for case in ctx.get("case_guidance") or []:
        known += " " + " ".join(str(v) for v in case.values() if v is not None)
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
    system = system_for(message.get("channel") or "email") + learn_guidance(
        conn, message=message, context=ctx,
    )
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


def build_followup(conn, message: dict) -> dict:
    """Draft a bounded post-reply nudge from the last actually executed response."""
    ctx = build_context(conn, message)
    rows = conn.execute(
        "SELECT id FROM agent_proposals WHERE kind='reply_draft' AND lead_no=?"
        " AND status='executed' ORDER BY executed_at DESC,id DESC",
        (message["lead_no"],),
    ).fetchall()
    last_sent = None
    for row in rows:
        candidate = proposals.get(conn, row["id"])
        payload = (candidate or {}).get("payload") or {}
        if (payload.get("channel") or "email") == (message.get("channel") or "email"):
            last_sent = payload
            break
    if not last_sent or not str(last_sent.get("body") or "").strip():
        raise llm.LLMError("找不到上一封已确认发送的回复，不能凭空起草复联")
    prompt = (
        _render(ctx)
        + "\n\nOUR LAST CONFIRMED SENT REPLY\n"
        + str(last_sent["body"])[:2500]
        + "\n\nThe customer has not replied since. Draft the one bounded follow-up now."
    )
    system = FOLLOWUP_SYSTEM + "\n\n" + learn_guidance(
        conn, message=message, context=ctx,
    )
    data = llm.complete_json(conn, "draft", system, prompt)
    body = str(data.get("body") or "").strip()
    if not body:
        raise llm.LLMError("模型没有返回复联正文")
    return {
        "subject": str(data.get("subject") or last_sent.get("subject") or "").strip(),
        "body": body,
        "language": str(data.get("language") or "en").strip(),
        "evidence": data.get("evidence") or [],
        "open_questions": str(data.get("open_questions") or "").strip(),
        "warnings": check_claims(body, ctx),
        "context": ctx,
        "backend": data.get("_llm_backend") or llm.backend_for(conn, "draft"),
        "fallback_from": data.get("_llm_fallback_from"),
    }


def learn_guidance(conn, *, message: dict | None = None,
                   context: dict | None = None) -> str:
    from app.agent import learn
    from app import copy_segments
    message = message or {}
    lead = (context or {}).get("lead") or {}
    return learn.draft_guidance(
        conn,
        channel=message.get("channel") or "email",
        country=lead.get("country"),
        customer_type=copy_segments.segment_of(lead),
    )
