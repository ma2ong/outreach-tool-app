"""The end-of-day note.

Allen does not sit in this tool all day. If the agent classified nine replies, drafted
four and is holding six decisions, that is worth one message on his phone — otherwise
the queue only exists for whoever remembers to open the page.

Where it goes is Allen's choice, and all of it is optional — without any target the
same text still lands on the Agent page, so nothing depends on the integration:

- `backend/report_whatsapp.txt`  — his own number. Preferred: the tool already holds a
  logged-in WhatsApp session, so nothing new is configured and no third party sees a
  customer name. One message a day to himself carries no account risk.
- `backend/lark_webhook.txt`     — Feishu custom-bot webhook URL.
- `backend/wecom_webhook.txt`    — WeCom (企业微信) group-bot webhook URL. Personal
  WeChat has no API; forwarding services exist but would read the report, which
  contains customer names and deal sizes, so they are not offered here.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import urllib.error
import urllib.request

from app import settings

_K_LAST_SENT = "agent_report_last_date"
_K_PUSH = "agent_report_push"
WEBHOOK_FILE = "lark_webhook.txt"
WECOM_FILE = "wecom_webhook.txt"
WHATSAPP_FILE = "report_whatsapp.txt"


def _read(name: str) -> str:
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        name)
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def webhook_url() -> str:
    return _read(WEBHOOK_FILE)


def wecom_url() -> str:
    return _read(WECOM_FILE)


def whatsapp_number() -> str:
    return "".join(ch for ch in _read(WHATSAPP_FILE) if ch.isdigit())


def push_enabled(conn) -> bool:
    """Whether the day's note is pushed to a phone as well as shown on the dashboard.

    Off by default. The report exists because Allen does not sit in this tool all day —
    but it now leads the dashboard, which is the screen he opens first, and a daily
    message to himself on WhatsApp was one more thing arriving on a phone he is already
    looking away from. A configured number no longer means "send it".
    """
    return settings.get(conn, _K_PUSH, "0") == "1"


def set_push(conn, enabled: bool) -> bool:
    settings.set_value(conn, _K_PUSH, "1" if enabled else "0")
    return enabled


def targets() -> list[str]:
    """Which delivery routes are configured right now."""
    return [name for name, value in (("whatsapp", whatsapp_number()),
                                     ("feishu", webhook_url()),
                                     ("wecom", wecom_url())) if value]


CH_LABEL = {"email": "邮件", "whatsapp": "WhatsApp",
            "instagram": "Instagram", "facebook": "Facebook"}
# Enough names to recognise the batch, not so many that the report becomes a list.
NAMED = 3


def _names(rows: list, total: int) -> str:
    """"A、B、C 等 12 家" — recognisable without turning into a wall of names."""
    shown = "、".join(r["company_en"] or f"#{r['lead_no']}" for r in rows[:NAMED])
    if total <= NAMED:
        return f"{shown}（共 {total} 家）"
    return f"{shown} 等 {total} 家"


def _campaign_label(campaign: str) -> str:
    """"序列:冷邮件 3 步跟进（英语）" -> "冷邮件 3 步跟进（英语）"."""
    return (campaign or "").split(":", 1)[-1].strip() or "手动发送"


def _sent_section(conn, day: str) -> list[str]:
    """What went out today, by channel and by campaign, with the companies named."""
    rows = conn.execute(
        "SELECT s.channel, s.campaign, s.lead_no, l.company_en"
        " FROM send_log s LEFT JOIN leads l ON l.no = s.lead_no"
        " WHERE date(s.sent_at, 'localtime')=? ORDER BY s.channel, s.id", (day,)).fetchall()
    if not rows:
        return ["■ 今天发出去的", "  没有发出任何触达"]
    lines = ["■ 今天发出去的"]
    by_channel: dict[str, list] = {}
    for row in rows:
        by_channel.setdefault(row["channel"], []).append(row)
    for channel, sent in by_channel.items():
        lines.append(f"  {CH_LABEL.get(channel, channel)} {len(sent)} 条")
        by_campaign: dict[str, list] = {}
        for row in sent:
            by_campaign.setdefault(_campaign_label(row["campaign"]), []).append(row)
        for campaign, group in by_campaign.items():
            lines.append(f"    · {campaign}：{_names(group, len(group))}")
    return lines


def _inbound_section(conn, day: str) -> list[str]:
    """What came back. A real reply is named; the machines are counted.

    Kept apart on purpose: reading an autoresponder as a human answer is what silently
    stopped a live follow-up sequence in August.
    """
    rows = conn.execute(
        "SELECT m.kind, m.lead_no, l.company_en FROM inbox_messages m"
        " LEFT JOIN leads l ON l.no = m.lead_no"
        " WHERE date(m.received_at)=?", (day,)).fetchall()
    replies = [r for r in rows if r["kind"] == "reply"]
    autos = [r for r in rows if r["kind"] == "auto"]
    bounces = [r for r in rows if r["kind"] == "bounce"]
    unsubs = [r for r in rows if r["kind"] == "unsubscribe"]
    lines = ["■ 客户那边的动静"]
    if replies:
        lines.append(f"  真人回复 {len(replies)} 条：{_names(replies, len(replies))}")
    else:
        lines.append("  没有真人回复")
    machine = []
    if autos:
        machine.append(f"自动回复 {len(autos)}")
    if bounces:
        machine.append(f"退信 {len(bounces)}（这些地址已停发）")
    if unsubs:
        machine.append(f"退订 {len(unsubs)}")
    if machine:
        lines.append("  " + "，".join(machine))
    return lines


def _development_section(conn, day: str) -> list[str]:
    """What was developed today, not just what was sent (docs/68 R4.1).

    The report used to answer "how many letters went out" and nothing else, which made
    an empty pipeline invisible until the day there was nothing left to send. Prospecting
    that found nothing is reported too — a silent zero reads like it did not run.
    """
    from app import relationship_events

    lines = []
    new_leads = conn.execute(
        "SELECT COUNT(*) c FROM leads WHERE date(created_at)=?", (day,)).fetchone()["c"]
    facts = relationship_events.recent(conn, kind="fact", days=1, limit=500)
    enriched = {f["lead_no"] for f in facts if f["source"] == "discovery"}
    runs = conn.execute(
        "SELECT COUNT(*) c FROM agent_proposals WHERE kind='discover_run'"
        " AND date(created_at)=? AND status='executed'", (day,)).fetchone()["c"]

    if new_leads:
        lines.append(f"  新开发客户 {new_leads} 家")
    if enriched:
        lines.append(f"  给 {len(enriched)} 家老客户补上了新信息"
                     f"（联系方式、职位、最近的项目）")
    if not new_leads and not enriched:
        lines.append("  今天没有开发到新客户，也没有补到老客户的新信息"
                     + (f"（跑了 {runs} 轮搜索）" if runs else "（今天没有跑开发）"))

    # An unconfigured channel and a broken one are different problems, and a line that
    # merges them teaches nothing about which (docs/70 R4).
    from app import discovery_sources
    # An optional alternative that is fine to leave unconfigured is not a problem to
    # report; saying so daily would just be a standing reminder of a door that is shut.
    off = [s for s in discovery_sources.status()
           if not s["available"] and not s.get("optional")]
    if off:
        lines.append("  未启用的渠道：" + "、".join(f"{s['label']}（{s['reason']}）"
                                                for s in off))
    return ["■ 客户开发", *lines]


def _pipeline_section(conn, day: str) -> list[str]:
    from app.opportunities import ensure_schema as ensure_opportunity_schema

    ensure_opportunity_schema(conn)
    lines = []
    new_leads = conn.execute(
        "SELECT country, COUNT(*) c FROM leads WHERE date(created_at)=?"
        " GROUP BY country ORDER BY c DESC", (day,)).fetchall()
    if new_leads:
        detail = "、".join(f"{r['country'] or '未知'} {r['c']}" for r in new_leads[:4])
        total = sum(r["c"] for r in new_leads)
        lines.append(f"  新进客户 {total} 家（{detail}）")
    won = conn.execute(
        "SELECT COUNT(*) c, COALESCE(SUM(amount),0) amt FROM opportunities"
        " WHERE date(updated_at)=? AND stage='won'", (day,)).fetchone()
    if won and won["c"]:
        lines.append(f"  成交 {won['c']} 个项目，金额 {won['amt']:.0f}")
    return ["■ 管道变化", *lines] if lines else []


def _next_section(conn) -> list[str]:
    """What is queued for tomorrow. A report about a finished day still owes this."""
    from app import social_queue

    lines = []
    due = conn.execute(
        "SELECT COUNT(*) c FROM sequence_enrollments e JOIN sequences s ON s.id=e.sequence_id"
        " WHERE e.status='active' AND s.channel='email' AND e.next_due_date <= date('now')"
    ).fetchone()["c"]
    if due:
        lines.append(f"  邮件跟进到期 {due} 条")
    try:
        social_queue.ensure_schema(conn)
        ready = conn.execute(
            "SELECT channel, COUNT(*) c FROM social_dm_queue"
            " WHERE queue_date=date('now') AND status='ready' GROUP BY channel").fetchall()
        if ready:
            detail = "、".join(f"{CH_LABEL.get(r['channel'], r['channel'])} {r['c']}"
                              for r in ready)
            lines.append(f"  社媒私信备好 {sum(r['c'] for r in ready)} 条待你确认（{detail}）")
    except Exception:  # noqa: BLE001 — an old DB without the table simply has none
        pass
    return ["■ 接下来", *lines] if lines else []


def compose(conn, today: dt.date | None = None) -> str:
    """What happened today, written the way an assistant reports to the person in charge.

    Order is what Allen has to act on first, not what is easiest to count: decisions
    waiting on him, then what went out and to whom, then what came back, then the
    pipeline, then tomorrow. The old version was six numbers with no nouns in them —
    "发出 40 条" says nothing about which channel, which customers, or what to do next,
    and a report nobody can act on is one they stop opening.
    """
    from app.agent import oversight, proposals
    from app.agent import run as agent_run
    today = today or dt.date.today()
    proposals.ensure_schema(conn)
    day = today.isoformat()

    pending = proposals.summary(conn)["pending"]
    waiting_quotes = conn.execute(
        "SELECT COUNT(*) c FROM agent_proposals"
        " WHERE status='pending' AND kind='create_task'"
        "   AND (title LIKE '%你来定价%' OR title LIKE '%报价%')").fetchone()["c"]

    lines = [f"【{day} 客户开发日报】", ""]

    # Anything that cannot move without him goes first.
    lines.append("■ 等你定的事")
    if waiting_quotes:
        lines.append(f"  ⚠ {waiting_quotes} 家在等报价 —— 只有你能给数字，需求已整理好")
    if pending:
        lines.append(f"  {pending} 条提议等你确认")
    if not waiting_quotes and not pending:
        lines.append("  没有")
    lines.append("")

    lines.extend(_sent_section(conn, day))
    lines.append("")
    lines.extend(_inbound_section(conn, day))

    # Development sits beside sending, not under it: the day an empty pipeline appears
    # is the day this line goes to zero, and that has to be visible before the sending
    # numbers quietly follow it down.
    lines.extend(["", *_development_section(conn, day)])

    pipeline = _pipeline_section(conn, day)
    if pipeline:
        lines.extend(["", *pipeline])

    outcome = oversight.daily_outcome(conn)
    lines.extend(["", "■ 今日目标",
                  f"  合格新客 {outcome['achieved']}/{outcome['target']}"
                  f"（完成 {outcome['completion_pct']}%）"])
    if not outcome["met"] and outcome["blockers"]:
        for blocker in outcome["blockers"][:2]:
            lines.append(f"  未达标：{blocker['message']}")

    nxt = _next_section(conn)
    if nxt:
        lines.extend(["", *nxt])

    executed = conn.execute(
        "SELECT COUNT(*) c FROM agent_proposals WHERE date(executed_at)=?"
        " AND status='executed'", (day,)).fetchone()["c"]
    made = conn.execute(
        "SELECT COUNT(*) c FROM agent_proposals WHERE date(created_at)=?",
        (day,)).fetchone()["c"]
    if executed or made:
        lines.extend(["", "■ Agent 今天做的",
                      f"  执行了 {executed} 条已确认的提议，新提了 {made} 条建议"])
    last = agent_run.status(conn).get("last_result")
    if last:
        lines.append(f"  最近一次运行：{last}")
    return "\n".join(lines)


def _post(url: str, payload: dict, reject_key: str) -> str:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return f"推送失败：{exc}"
    if data.get("errcode") or data.get("code"):
        return f"{reject_key}拒绝：{data.get('errmsg') or data.get('msg')}"
    return ""


def _push_whatsapp(text: str) -> str:
    """Message Allen's own number through the session the tool already holds."""
    from app.api.channels import ENGINE
    try:
        ENGINE.send_message("whatsapp", whatsapp_number(), text, None)
    except Exception as exc:  # noqa: BLE001 — an expired session must not break the run
        return f"WhatsApp 发送失败：{str(exc)[:140]}"
    return ""


def push(text: str) -> str:
    """Deliver the report. Returns '' if it reached at least one place, else the reason.

    Every configured route is tried: a Feishu outage should not silently swallow the
    day's summary when WhatsApp would have carried it.
    """
    routes = []
    if whatsapp_number():
        routes.append(("WhatsApp", lambda: _push_whatsapp(text)))
    if webhook_url():
        routes.append(("飞书", lambda: _post(
            webhook_url(), {"msg_type": "text", "content": {"text": text}}, "飞书")))
    if wecom_url():
        routes.append(("企业微信", lambda: _post(
            wecom_url(), {"msgtype": "text", "text": {"content": text}}, "企业微信")))
    if not routes:
        return ("没有配置日报接收方式，只在页面上显示。想收到推送，"
                "把你自己的 WhatsApp 号写进 backend/report_whatsapp.txt，"
                "或把机器人地址写进 backend/lark_webhook.txt / wecom_webhook.txt")
    problems = []
    for name, send in routes:
        problem = send()
        if not problem:
            return ""
        problems.append(f"{name}：{problem}")
    return "；".join(problems)


def send_daily(conn, today: dt.date | None = None) -> dict:
    """Compose and push once per day. Idempotent: a second call the same day is a no-op."""
    today = today or dt.date.today()
    if settings.get(conn, _K_LAST_SENT) == today.isoformat():
        return {"sent": False, "reason": "今天已经发过日报"}
    text = compose(conn, today)
    problem = push(text)
    settings.set_value(conn, _K_LAST_SENT, today.isoformat())
    return {"sent": not problem, "reason": problem, "text": text}
