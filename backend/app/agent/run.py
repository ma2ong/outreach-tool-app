"""The phase-A pipeline: a reply arrives, the agent proposes what to do about it.

Order matters. Classification is cheap and batched, so it runs first for everything;
drafting is expensive and runs only for the intents where a draft is the right answer.
Email replies get a draft because we hold the full text. WhatsApp and Instagram replies
only get a nudge: `inbound.py` scrapes a one-line preview from the conversation list and
deliberately never opens the thread, so half a sentence is all we have — and a reply
composed from half a sentence is exactly what section 2 forbids.
"""
from __future__ import annotations

import datetime as dt

from app import settings
from app.agent import classify, draft, llm, memory, proposals

_K_LAST_AT = "agent_run_last_at"
_K_LAST_RESULT = "agent_run_last_result"

DRAFT_LIMIT = 10          # per run; drafting is the expensive half
SOCIAL_CHANNELS = ("whatsapp", "instagram", "facebook")


def _messages_awaiting_action(conn, limit: int) -> list[dict]:
    """Classified, unhandled replies with no proposal on them yet."""
    rows = conn.execute(
        "SELECT m.id, m.lead_no, m.contact_id, m.channel, m.subject, m.body, m.from_addr,"
        "       m.received_at, m.intent, m.intent_confidence, m.mailbox_email,"
        "       l.company_en, l.do_not_contact"
        " FROM inbox_messages m JOIN leads l ON l.no=m.lead_no"
        " WHERE m.kind='reply' AND m.intent IS NOT NULL AND m.handled_at IS NULL"
        "   AND NOT EXISTS (SELECT 1 FROM agent_proposals p"
        "                   WHERE p.inbox_message_id = m.id)"
        " ORDER BY m.received_at DESC, m.id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def _reject_proposal(conn, msg: dict) -> bool:
    return proposals.create(
        conn, "mark_do_not_contact",
        lead_no=msg["lead_no"], inbox_message_id=msg["id"],
        title=f"{msg['company_en']} 明确拒绝，建议标记不再联系",
        reasoning="客户回复被判定为明确拒绝。标记后全渠道停发，避免继续骚扰。",
        evidence=[{"claim": "客户拒绝", "source": (msg.get("body") or "")[:200]}],
        payload={"reason": (msg.get("body") or "")[:200]},
        risk="high", dedupe_key="reject") is not None


def _social_nudge(conn, msg: dict) -> bool:
    channel = msg["channel"]
    return proposals.create(
        conn, "create_task",
        lead_no=msg["lead_no"], inbox_message_id=msg["id"],
        title=f"去 {channel} 看 {msg['company_en']} 的消息（像是{classify.INTENTS[msg['intent']]}）",
        reasoning=("社媒只抓得到会话列表的一行预览，没有全文，不足以起草回复。"
                   "这里只做提醒，回复由你在手机或网页端亲自看过再发。"),
        evidence=[{"claim": "会话列表预览", "source": (msg.get("body") or "")[:200]}],
        payload={"title": f"回复 {msg['company_en']} 的 {channel} 消息",
                 "type": channel if channel in ("whatsapp", "instagram") else "task",
                 "due_at": dt.date.today().isoformat(), "priority": "high"},
        risk="low", dedupe_key="social_nudge") is not None


def _draft_proposal(conn, msg: dict) -> bool:
    result = draft.build(conn, msg)
    memory.update(conn, result["context"])
    subject = result["subject"] or f"Re: {msg.get('subject') or ''}".strip()
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    reasoning = (f"客户回复被判定为「{classify.INTENTS.get(msg['intent'], msg['intent'])}」"
                 f"（把握 {msg.get('intent_confidence') or 0}）。草稿只用了上下文里已有的事实。")
    if result["open_questions"]:
        reasoning += f" 未能回答：{result['open_questions']}"
    warnings = result["warnings"]
    if warnings:
        reasoning += " ⚠ " + "；".join(warnings)
    return proposals.create(
        conn, "reply_draft",
        lead_no=msg["lead_no"], contact_id=msg.get("contact_id"),
        inbox_message_id=msg["id"],
        title=f"回复 {msg['company_en']}（{msg['intent']}）",
        reasoning=reasoning,
        evidence=result["evidence"],
        payload={"to": msg.get("from_addr") or "", "subject": subject,
                 "body": result["body"], "language": result["language"],
                 "mailbox_email": msg.get("mailbox_email") or ""},
        # A draft that states an unsourced number is exactly what must not slip through
        # on a quick approve, so it is ranked with the decisions that need attention.
        risk="high" if warnings else "medium",
        backend=llm.backend_for(conn, "draft"),
        dedupe_key="draft") is not None


def act_on_replies(conn, limit: int = DRAFT_LIMIT) -> dict:
    """Turn classified replies into proposals. One failure must not stop the rest."""
    proposals.ensure_schema(conn)
    made = {"draft": 0, "nudge": 0, "reject": 0}
    errors: list[str] = []
    for msg in _messages_awaiting_action(conn, limit):
        if msg["do_not_contact"]:
            continue
        try:
            if msg["intent"] == "reject":
                made["reject"] += _reject_proposal(conn, msg)
            elif msg["intent"] not in classify.DRAFTABLE:
                continue          # referral / unclear stay in the inbox for Allen
            elif msg["channel"] in SOCIAL_CHANNELS:
                made["nudge"] += _social_nudge(conn, msg)
            else:
                made["draft"] += _draft_proposal(conn, msg)
        except llm.LLMUnavailable as exc:
            errors.append(str(exc))
            break                 # no backend: stop, do not burn the rest of the batch
        except Exception as exc:  # noqa: BLE001 — one bad reply must not block the queue
            errors.append(f"{msg['company_en']}: {exc}")
    return {**made, "errors": errors}


def run_once(conn) -> dict:
    """One full pass: retire stale proposals, classify, then propose."""
    proposals.ensure_schema(conn)
    expired = proposals.expire_stale(conn)
    classified = classify.run(conn)
    acted = act_on_replies(conn)
    result = {
        "expired": expired,
        "classified": classified.get("classified", 0),
        "classify_note": classified.get("note", ""),
        **{k: v for k, v in acted.items() if k != "errors"},
        "errors": acted["errors"],
    }
    now = dt.datetime.now()
    settings.set_value(conn, _K_LAST_AT, now.isoformat())
    settings.set_value(conn, _K_LAST_RESULT, _describe(now, result))
    return result


def _describe(now: dt.datetime, r: dict) -> str:
    bits = []
    if r["classified"]:
        bits.append(f"分类 {r['classified']} 条")
    if r["draft"]:
        bits.append(f"起草 {r['draft']} 封")
    if r["nudge"]:
        bits.append(f"社媒提醒 {r['nudge']} 条")
    if r["reject"]:
        bits.append(f"建议停发 {r['reject']} 家")
    if r["expired"]:
        bits.append(f"过期清理 {r['expired']} 条")
    if r["errors"]:
        bits.append(f"{len(r['errors'])} 条出错：{r['errors'][0][:60]}")
    return f"{now:%m-%d %H:%M} " + ("，".join(bits) if bits else "没有需要处理的回复")


def status(conn) -> dict:
    proposals.ensure_schema(conn)
    return {
        "last_at": settings.get(conn, _K_LAST_AT) or None,
        "last_result": settings.get(conn, _K_LAST_RESULT) or None,
        "unclassified": len(classify.pending(conn, limit=999)),
        "llm": llm.status(conn),
        **proposals.summary(conn),
    }
