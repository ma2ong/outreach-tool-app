"""Intent classification for customer replies.

Runs in batches on the cheap backend (Spec 22 section 8). Two rules shape the design:

1. Deterministic wins. Bounces, unsubscribes and auto-replies are already decided by
   `replies.py` from headers and keywords; the model never gets to overrule a fact.
2. Send less. The classifier only needs the shape of the message, so company names,
   addresses, phone numbers and URLs are stripped before the text leaves the machine.
   Accuracy is unaffected and the data that leaves is a paragraph of English prose.
"""
from __future__ import annotations

import datetime as dt
import re

from app.agent import llm

INTENTS = {
    "inquiry": "泛询盘，问产品但没说具体要什么",
    "spec": "要具体参数、规格、技术资料",
    "quote": "要正式报价（我们还没给过价）",
    "sample": "要样品或样板",
    "negotiation": "已经收到过我们的报价，在谈价格或条款",
    "referral": "转介绍，让我们联系别人",
    "reject": "明确拒绝、不感兴趣、别再发了",
    "unclear": "判断不了",
}

BATCH_SIZE = 20

# Pricing is Allen's, full stop (his instruction, 2026-08-19). A reply that ends in a
# number he has to stand behind is never drafted — the agent tells him it arrived and
# lays out what they asked for, and he writes the quote.
QUOTE_INTENTS = ("quote", "negotiation")
_DEFAULT_DRAFTABLE = ("inquiry", "spec", "sample")
_K_DRAFT_INTENTS = "agent_draft_intents"


def draftable(conn) -> tuple[str, ...]:
    """Which intents the agent may answer. Configurable, but a quote intent can never
    be added: that is a policy, not a preference, so it is enforced here rather than
    left to whoever edits the setting."""
    from app import settings
    raw = settings.get(conn, _K_DRAFT_INTENTS, ",".join(_DEFAULT_DRAFTABLE))
    chosen = [i.strip() for i in raw.split(",") if i.strip() in INTENTS]
    return tuple(i for i in chosen if i not in QUOTE_INTENTS)


def set_draftable(conn, intents: list[str]) -> tuple[str, ...]:
    from app import settings
    clean = [i for i in intents if i in INTENTS and i not in QUOTE_INTENTS]
    settings.set_value(conn, _K_DRAFT_INTENTS, ",".join(clean))
    return draftable(conn)

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_PHONE_RE = re.compile(r"[+()\d][\d\s().-]{7,}\d")

SYSTEM = """You classify inbound B2B replies to an LED display supplier's cold outreach.
For each message return exactly one intent from this list:

inquiry  - general interest, asks about products without stating a need
spec     - asks for specifications, technical data, datasheets
quote    - asks for a price or quotation and we have NOT quoted them before
sample   - asks for a sample or demo unit
negotiation - we already quoted; they are discussing price, terms or discounts
referral - redirects us to another person or company
reject   - not interested, stop contacting, complaint
unclear  - you cannot tell

Decide quote vs negotiation ONLY by the `quoted` flag given for each message.
Never guess an intent to avoid `unclear`; `unclear` is a valid, useful answer.

Also extract `needs`: what this customer actually asked for, in under 20 words —
size, pixel pitch, indoor/outdoor, quantity, deadline, whatever they stated. Use only
what is in their message; empty string if they stated nothing concrete. This is what
Allen reads before pricing, so copy their numbers exactly and invent none.

Return JSON: {"results":[{"id":<id>,"intent":"<intent>","confidence":<0-100>,
"why":"<max 12 words>","needs":"<max 20 words>"}]}. One entry per input id, no extras."""


def redact(text: str, company: str = "") -> str:
    """Strip anything that identifies the customer before the text leaves the machine."""
    out = _URL_RE.sub("[url]", text or "")
    out = _EMAIL_RE.sub("[email]", out)
    out = _PHONE_RE.sub("[phone]", out)
    if company and len(company) > 3:
        out = re.sub(re.escape(company), "[company]", out, flags=re.I)
    return re.sub(r"\n{3,}", "\n\n", out).strip()


def pending(conn, limit: int = BATCH_SIZE) -> list[dict]:
    """Real customer replies that have not been classified yet."""
    from app import opportunities
    opportunities.ensure_schema(conn)
    rows = conn.execute(
        "SELECT m.id, m.lead_no, m.channel, m.subject, m.body, l.company_en,"
        "  EXISTS(SELECT 1 FROM opportunities o WHERE o.lead_no=m.lead_no"
        "         AND o.stage IN ('quoted','negotiation','won')) AS quoted"
        " FROM inbox_messages m JOIN leads l ON l.no=m.lead_no"
        " WHERE m.kind='reply' AND m.intent IS NULL"
        " ORDER BY m.received_at DESC, m.id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def _prompt(messages: list[dict]) -> str:
    parts = []
    for m in messages:
        text = redact(f"{m.get('subject') or ''}\n{m.get('body') or ''}", m.get("company_en") or "")
        parts.append(f"---\nid: {m['id']}\nquoted: {'yes' if m.get('quoted') else 'no'}\n"
                     f"channel: {m.get('channel') or 'email'}\ntext:\n{text[:1500]}")
    return "\n".join(parts)


def _store(conn, message_id: int, intent: str, confidence: int, needs: str = "") -> None:
    conn.execute(
        "UPDATE inbox_messages SET intent=?, intent_confidence=?, intent_needs=?,"
        " intent_at=? WHERE id=?",
        (intent, confidence, needs[:300], dt.datetime.now(dt.UTC).isoformat(), message_id))
    conn.commit()


def run(conn, limit: int = BATCH_SIZE) -> dict:
    """Classify one batch. Returns what happened; raises nothing the caller must catch —
    an unavailable backend is reported, not thrown, so the daily job stays quiet."""
    batch = pending(conn, limit)
    if not batch:
        return {"classified": 0, "pending": 0, "note": "没有待分类的回复", "errors": []}
    try:
        data = llm.complete_json(conn, "classify", SYSTEM, _prompt(batch))
    except llm.LLMUnavailable as exc:
        return {"classified": 0, "pending": len(batch), "note": str(exc),
                "unavailable": True, "errors": [str(exc)]}
    except llm.LLMError as exc:
        note = f"分类失败：{exc}"
        return {"classified": 0, "pending": len(batch), "note": note, "errors": [note]}
    by_id = {m["id"]: m for m in batch}
    done = 0
    errors: list[str] = []
    for item in data.get("results") or []:
        mid = item.get("id")
        intent = str(item.get("intent") or "").strip()
        if mid not in by_id or intent not in INTENTS:
            continue
        try:
            confidence = max(0, min(100, int(item.get("confidence") or 0)))
        except (TypeError, ValueError):
            confidence = 0
        _store(conn, mid, intent, confidence, str(item.get("needs") or "").strip())
        try:
            from app.agent import project_facts
            project_facts.capture(conn, by_id[mid])
        except Exception as exc:  # noqa: BLE001 — classification remains durable
            errors.append(
                f"项目事实提取 message #{mid}: {type(exc).__name__}: {str(exc)[:180]}"
            )
        done += 1
    missing = len(batch) - done
    if missing:
        errors.append(f"分类模型未返回 {missing} 条有效结果")
    return {"classified": done, "pending": missing,
            "note": f"已分类 {done} 条回复", "errors": errors}
