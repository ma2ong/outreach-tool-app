"""The phase-A pipeline: a reply arrives, the agent proposes what to do about it.

Order matters. Classification is cheap and batched, so it runs first for everything;
drafting is expensive and runs only for the intents where a draft is the right answer.

Email arrives with its full text. A DM does not: the daily scan reads the chat list and
gets one preview line. So a DM worth answering has its conversation opened first, and
only then is it drafted — and if the thread cannot be read (session expired, no handle,
markup moved), it falls back to a task pointing Allen at the right chat. Drafting from
the preview is never an option; that is the sentence-and-a-half problem section 2 exists
to prevent.
"""
from __future__ import annotations

import datetime as dt
import json

from app import autosend, settings
from app.agent import classify, conversation, draft, llm, memory, mission, proposals

_K_LAST_AT = "agent_run_last_at"
_K_LAST_RESULT = "agent_run_last_result"
_K_PLAN_ENABLED = "agent_plan_enabled"
_K_PLAN_DATE = "agent_plan_last_date"
_K_PLAN_RESULT = "agent_plan_last_result"
_K_PLAN_ATTEMPT_DATE = "agent_plan_attempt_date"
_K_PLAN_ATTEMPTS = "agent_plan_attempts"
_K_PLAN_LAST_ATTEMPT = "agent_plan_last_attempt_at"

DRAFT_LIMIT = 10          # per run; drafting is the expensive half
SOCIAL_CHANNELS = ("whatsapp", "instagram", "facebook")
STALE_REPLY_DAYS = proposals.EXPIRE_DAYS


def _messages_awaiting_action(conn, limit: int) -> list[dict]:
    """Classified, unhandled replies with no proposal on them yet."""
    rows = conn.execute(
        "SELECT m.id, m.lead_no, m.contact_id, m.channel, m.subject, m.body, m.from_addr,"
        "       m.received_at, m.intent, m.intent_confidence, m.intent_needs,"
        "       m.mailbox_email, m.thread_json,"
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


def _quote_alert(conn, msg: dict) -> bool:
    """A customer asked for a price. Tell Allen, prepare the ground, write nothing.

    His rule (2026-08-19): the agent finds customers, reaches out and handles simple
    replies; the quote is his. So this does the reading — which customer, which channel,
    what they specified — and stops there. No draft exists for him to be tempted by.
    """
    needs = (msg.get("intent_needs") or "").strip()
    channel = "邮件" if msg["channel"] == "email" else msg["channel"]
    label = "要报价" if msg["intent"] == "quote" else "在谈价格"
    note = f"客户原话：{(msg.get('body') or '')[:400]}"
    conversation.takeover(
        conn, msg["lead_no"], msg["channel"],
        f"客户{label}，报价和谈价只能由 Allen 处理", msg["id"],
        f"给 {msg['company_en']} 报价" + (f"：{needs}" if needs else ""))
    return proposals.create(
        conn, "create_task",
        lead_no=msg["lead_no"], contact_id=msg.get("contact_id"),
        inbox_message_id=msg["id"],
        title=f"{msg['company_en']}{label}——你来定价" + (f"（{needs}）" if needs else ""),
        reasoning=(f"{channel}回复，判定为「{classify.INTENTS[msg['intent']]}」。"
                   "报价由你来做，所以这里只提醒并把客户说的要求整理出来，没有起草任何回复。"),
        evidence=[{"claim": needs or "客户要求见原文", "source": (msg.get("body") or "")[:200]}],
        payload={"title": f"给 {msg['company_en']} 报价" + (f"：{needs}" if needs else ""),
                 "type": "quote", "due_at": dt.date.today().isoformat(),
                 "priority": "high", "note": note},
        risk="low", dedupe_key="quote_alert") is not None


def _human_takeover_nudge(conn, msg: dict, state: dict) -> bool:
    """A later message stays with Allen until he explicitly returns the channel."""
    return proposals.create(
        conn, "create_task", lead_no=msg["lead_no"], inbox_message_id=msg["id"],
        title=f"你正在接管 {msg['company_en']}，有一条新消息",
        reasoning=(f"{msg['channel']} 会话仍由你接管：{state.get('reason') or '人工处理中'}。"
                   "Agent 没有起草，避免在报价/谈判中抢回对话。"),
        evidence=[{"claim": "客户新消息", "source": (msg.get("body") or "")[:200]}],
        payload={"title": f"处理 {msg['company_en']} 的新消息", "type": "task",
                 "due_at": dt.date.today().isoformat(), "priority": "high",
                 "note": (msg.get("body") or "")[:400]},
        risk="low", dedupe_key="human_takeover_nudge") is not None


def _reply_is_stale(msg: dict) -> bool:
    """Unknown or old timestamps are unsafe inputs for an automatic customer reply."""
    raw = str(msg.get("received_at") or "").strip()
    try:
        received = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return True
    if received.tzinfo is None:
        received = received.replace(tzinfo=dt.UTC)
    return received.astimezone(dt.UTC) < dt.datetime.now(dt.UTC) - dt.timedelta(
        days=STALE_REPLY_DAYS)


def _stale_reply_nudge(conn, msg: dict) -> bool:
    """Preserve the lead without pretending an old inbox item just arrived."""
    conversation.takeover(
        conn, msg["lead_no"], msg["channel"],
        f"历史回复超过 {STALE_REPLY_DAYS} 天，需要 Allen 判断上下文是否仍有效",
        msg["id"], f"人工查看 {msg['company_en']} 的历史回复")
    return proposals.create(
        conn, "create_task", lead_no=msg["lead_no"], contact_id=msg.get("contact_id"),
        inbox_message_id=msg["id"],
        title=f"人工查看 {msg['company_en']} 的历史回复——Agent 不自动补发",
        reasoning=(f"这条回复收到已超过 {STALE_REPLY_DAYS} 天，自动回复可能脱离当前上下文。"
                   "Agent 已把该渠道交给你，并保留原文供判断。"),
        evidence=[{"claim": "历史回复", "source": (msg.get("body") or "")[:200]}],
        payload={"title": f"查看并处理 {msg['company_en']} 的历史回复", "type": "task",
                 "due_at": dt.date.today().isoformat(), "priority": "high",
                 "note": (msg.get("body") or "")[:400]},
        risk="low", dedupe_key="stale_reply_nudge") is not None


def _social_nudge(conn, msg: dict, why: str) -> bool:
    """The fallback when the conversation could not be read. Better a pointer to the
    right chat than a reply composed from a preview line."""
    channel = msg["channel"]
    return proposals.create(
        conn, "create_task",
        lead_no=msg["lead_no"], inbox_message_id=msg["id"],
        title=f"去 {channel} 看 {msg['company_en']} 的消息（像是{classify.INTENTS[msg['intent']]}）",
        reasoning=f"没能读到这条对话的全文，所以没起草：{why}",
        evidence=[{"claim": "会话列表预览", "source": (msg.get("body") or "")[:200]}],
        payload={"title": f"回复 {msg['company_en']} 的 {channel} 消息",
                 "type": channel if channel in ("whatsapp", "instagram") else "task",
                 "due_at": dt.date.today().isoformat(), "priority": "high"},
        risk="low", dedupe_key="social_nudge") is not None


def _social_draft(conn, msg: dict) -> tuple[str, bool]:
    """Open the chat, read what was actually said, then draft from that.

    Opening the thread clears its unread mark on the phone. That is the trade Allen
    accepted so DM replies get written from the real conversation instead of a preview
    line. It happens only for a message already worth answering, never on a schedule.

    Returns which kind of proposal was made, so a fallback to a nudge is counted as one.
    """
    from app.agent import social
    thread: list[dict] = []
    try:
        thread = social.fetch_thread(conn, msg)
        reason = "" if social.last_inbound(thread) else "对话里读不到客户的最后一条消息"
    except social.NoTarget as exc:
        reason = str(exc)
    except Exception as exc:  # noqa: BLE001 — a browser hiccup falls back, never crashes
        reason = f"打开对话失败：{str(exc)[:120]}"
    if reason:
        return "nudge", _social_nudge(conn, msg, reason)
    return "draft", _draft_proposal(
        conn, {**msg, "thread_json": json.dumps(thread, ensure_ascii=False)})


def _draft_proposal(conn, msg: dict) -> bool:
    result = draft.build(conn, msg)
    memory.update(conn, result["context"])
    if msg["channel"] in SOCIAL_CHANNELS:
        subject = ""          # a chat message has none, and a stray "Re:" would show in the UI
    else:
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
    proposal = proposals.create(
        conn, "reply_draft",
        lead_no=msg["lead_no"], contact_id=msg.get("contact_id"),
        inbox_message_id=msg["id"],
        title=f"回复 {msg['company_en']}（{msg['intent']}）",
        reasoning=reasoning,
        evidence=result["evidence"],
        payload={"channel": msg["channel"],
                 "to": msg.get("from_addr") or "", "subject": subject,
                 "body": result["body"], "language": result["language"],
                 "mailbox_email": msg.get("mailbox_email") or "",
                 "open_questions": result["open_questions"]},
        # A draft that states an unsourced number is exactly what must not slip through
        # on a quick approve, so it is ranked with the decisions that need attention.
        risk="high" if warnings else "medium",
        backend=result.get("backend") or llm.backend_for(conn, "draft"),
        dedupe_key="draft")
    if proposal and proposal["status"] != "executed":
        conversation.waiting_us(conn, msg["lead_no"], msg["channel"], msg["id"])
    return proposal is not None


def act_on_replies(conn, limit: int = DRAFT_LIMIT) -> dict:
    """Turn classified replies into proposals. One failure must not stop the rest."""
    proposals.ensure_schema(conn)
    made = {"draft": 0, "nudge": 0, "reject": 0, "quote": 0}
    draftable = classify.draftable(conn)
    errors: list[str] = []
    for msg in _messages_awaiting_action(conn, limit):
        if msg["do_not_contact"]:
            continue
        try:
            if msg["intent"] == "reject":
                made["reject"] += _reject_proposal(conn, msg)
            elif msg["intent"] in classify.QUOTE_INTENTS:
                made["quote"] += _quote_alert(conn, msg)
            elif ((state := conversation.get(conn, msg["lead_no"], msg["channel"]))
                  and state["owner"] == "allen"):
                made["nudge"] += _human_takeover_nudge(conn, msg, state)
            elif msg["intent"] not in draftable:
                continue          # referral / unclear stay in the inbox for Allen
            elif _reply_is_stale(msg):
                made["nudge"] += _stale_reply_nudge(conn, msg)
            elif msg["channel"] in SOCIAL_CHANNELS:
                kind, ok = _social_draft(conn, msg)
                made[kind] += ok
            else:
                made["draft"] += _draft_proposal(conn, msg)
        except llm.LLMUnavailable as exc:
            errors.append(str(exc))
            break                 # no backend: stop, do not burn the rest of the batch
        except Exception as exc:  # noqa: BLE001 — one bad reply must not block the queue
            errors.append(f"{msg['company_en']}: {exc}")
    return {**made, "errors": errors}


PLAN_WINDOW = (8, 12)     # the daily plan is a morning thing; after noon it is stale
PLAN_MAX_ATTEMPTS = 3
PLAN_RETRY_MINUTES = 30
REPORT_HOUR = 18          # the day is over; say what happened


def _plan_attempts(conn, today: str) -> int:
    if settings.get(conn, _K_PLAN_ATTEMPT_DATE) != today:
        return 0
    try:
        return max(0, int(settings.get(conn, _K_PLAN_ATTEMPTS, "0")))
    except (TypeError, ValueError):
        return 0


def _last_plan_attempt(conn) -> dt.datetime | None:
    raw = settings.get(conn, _K_PLAN_LAST_ATTEMPT)
    if not raw:
        return None
    try:
        return dt.datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        return None


def plan_due(conn, now: dt.datetime | None = None) -> bool:
    """Once successfully per day, with a bounded retry window after failures.

    On by default: the plan only ever produces proposals, so the cost of it running is
    a queue Allen ignores, while the cost of it not running is a day nobody planned.
    """
    now = now or dt.datetime.now()
    if settings.get(conn, _K_PLAN_ENABLED, "1") != "1":
        return False
    if not (PLAN_WINDOW[0] <= now.hour < PLAN_WINDOW[1]):
        return False
    today = now.date().isoformat()
    if settings.get(conn, _K_PLAN_DATE) == today:
        return False
    if _plan_attempts(conn, today) >= PLAN_MAX_ATTEMPTS:
        return False
    last_attempt = _last_plan_attempt(conn)
    if last_attempt and settings.get(conn, _K_PLAN_ATTEMPT_DATE) == today:
        if now - last_attempt < dt.timedelta(minutes=PLAN_RETRY_MINUTES):
            return False
    return True


def make_plan(conn, now: dt.datetime | None = None) -> dict:
    """Build today's plan and record one of at most three daily attempts."""
    from app.agent import plan as plan_mod
    now = now or dt.datetime.now()
    today = now.date().isoformat()
    attempts = _plan_attempts(conn, today) + 1
    settings.set_value(conn, _K_PLAN_ATTEMPT_DATE, today)
    settings.set_value(conn, _K_PLAN_ATTEMPTS, str(attempts))
    settings.set_value(conn, _K_PLAN_LAST_ATTEMPT, now.isoformat())
    try:
        result = plan_mod.build_plan(conn)
    except (llm.LLMUnavailable, llm.LLMError) as exc:
        fallback = plan_mod.build_mission_fallback(conn)
        if fallback["proposed"]:
            settings.set_value(conn, _K_PLAN_DATE, today)
            result = {
                "summary": "计划模型不可用，已按销售任务书执行安全找客兜底",
                "proposed": fallback["proposed"],
                "rejected": fallback["rejected"],
                "considered": 0,
                "degraded": True,
                "error": str(exc),
            }
            settings.set_value(
                conn, _K_PLAN_RESULT,
                f"{now:%m-%d %H:%M} 计划模型失败，任务书已降级执行找客：{exc}")
            return result
        settings.set_value(
            conn, _K_PLAN_RESULT,
            f"{now:%m-%d %H:%M} 计划失败（第 {attempts}/{PLAN_MAX_ATTEMPTS} 次）：{exc}")
        return {"proposed": 0, "error": str(exc)}
    settings.set_value(conn, _K_PLAN_DATE, today)
    note = f"{now:%m-%d %H:%M} 今日计划：{result['summary'] or ''}（{result['proposed']} 条建议）"
    if result["rejected"]:
        note += f"，{len(result['rejected'])} 条不合规被丢弃"
    if result.get("duplicates"):
        # Otherwise a fully-planned day reads exactly like a dead button.
        note += f"，{len(result['duplicates'])} 条与今天已有的重复（去「已执行」看结果）"
    settings.set_value(conn, _K_PLAN_RESULT, note)
    return result


def run_once(conn, now: dt.datetime | None = None) -> dict:
    """One full pass: retire stale proposals, classify, propose, and — once a morning —
    plan the day."""
    from app.agent import oversight

    proposals.ensure_schema(conn)
    run_id = oversight.start_run(conn)
    incident: dict = {}
    try:
        incident = oversight.evaluate(conn)
        expired = proposals.expire_stale(conn)
        classified = classify.run(conn)
        acted = act_on_replies(conn)
        planned = make_plan(conn, now) if plan_due(conn, now) else {"proposed": 0}
        _maybe_report(conn, now)
        result = {
            "expired": expired,
            "classified": classified.get("classified", 0),
            "classify_note": classified.get("note", ""),
            "planned": planned.get("proposed", 0),
            **{k: v for k, v in acted.items() if k != "errors"},
            "errors": acted["errors"] + ([planned["error"]] if planned.get("error") else []),
            "safety_paused": bool(incident.get("paused")),
        }
        finished = dt.datetime.now()
        settings.set_value(conn, _K_LAST_AT, finished.isoformat())
        settings.set_value(conn, _K_LAST_RESULT, _describe(finished, result))
        oversight.finish_run(conn, run_id, "success", result=result, incident=incident)
        return result
    except Exception as exc:
        oversight.finish_run(conn, run_id, "failed", incident=incident, error=str(exc))
        raise


def _maybe_report(conn, now: dt.datetime | None) -> None:
    """Push the evening summary once the day is done.

    Only when some route exists: without one `send_daily` would mark the day as reported
    and Allen would never see it anywhere but the page he did not open.
    """
    from app.agent import report
    now = now or dt.datetime.now()
    if now.hour < REPORT_HOUR or not report.push_enabled(conn) or not report.targets():
        return
    try:
        report.send_daily(conn, now.date())
    except Exception:  # noqa: BLE001 — a chat webhook must never break the pipeline
        pass


def _describe(now: dt.datetime, r: dict) -> str:
    bits = []
    if r.get("safety_paused"):
        bits.append("已安全暂停邮件自动跟进")
    if r["classified"]:
        bits.append(f"分类 {r['classified']} 条")
    if r["draft"]:
        bits.append(f"起草 {r['draft']} 封")
    if r.get("quote"):
        bits.append(f"要你报价 {r['quote']} 家")
    if r["nudge"]:
        bits.append(f"社媒提醒 {r['nudge']} 条")
    if r["reject"]:
        bits.append(f"建议停发 {r['reject']} 家")
    if r.get("planned"):
        bits.append(f"今日计划 {r['planned']} 条")
    if r["expired"]:
        bits.append(f"过期清理 {r['expired']} 条")
    if r["errors"]:
        bits.append(f"{len(r['errors'])} 条出错：{r['errors'][0][:60]}")
    return f"{now:%m-%d %H:%M} " + ("，".join(bits) if bits else "没有需要处理的回复")


def status(conn) -> dict:
    from app.agent import oversight

    proposals.ensure_schema(conn)
    today = dt.date.today().isoformat()
    return {
        "last_at": settings.get(conn, _K_LAST_AT) or None,
        "last_result": settings.get(conn, _K_LAST_RESULT) or None,
        "unclassified": len(classify.pending(conn, limit=999)),
        "mission": mission.get(conn),
        "mission_progress": mission.progress(conn),
        "outcome": oversight.daily_outcome(conn),
        # The reason and the evidence, so the panel can offer a way out instead of
        # only announcing that email went quiet.
        "safety_pause": autosend.safety_pause(conn),
        # Present only while a resume is standing: says what was accepted and when it
        # stops covering the situation.
        "risk_ack": autosend.risk_ack(conn),
        "bounce_limit": autosend.ACK_TOLERANCE_PCT,
        "recent_runs": oversight.latest_runs(conn),
        "takeovers": conversation.takeovers(conn),
        "llm": llm.status(conn),
        "plan": {
            "enabled": settings.get(conn, _K_PLAN_ENABLED, "1") == "1",
            "last_date": settings.get(conn, _K_PLAN_DATE) or None,
            "last_result": settings.get(conn, _K_PLAN_RESULT) or None,
            "window": list(PLAN_WINDOW),
            "attempts": _plan_attempts(conn, today),
            "max_attempts": PLAN_MAX_ATTEMPTS,
            "retry_minutes": PLAN_RETRY_MINUTES,
        },
        **proposals.summary(conn),
    }


def set_plan_enabled(conn, on: bool) -> None:
    settings.set_value(conn, _K_PLAN_ENABLED, "1" if on else "0")
