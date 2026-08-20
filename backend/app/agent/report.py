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


def targets() -> list[str]:
    """Which delivery routes are configured right now."""
    return [name for name, value in (("whatsapp", whatsapp_number()),
                                     ("feishu", webhook_url()),
                                     ("wecom", wecom_url())) if value]


def compose(conn, today: dt.date | None = None) -> str:
    """What happened today, in the order Allen cares about."""
    from app.agent import oversight, proposals
    from app.agent import run as agent_run
    today = today or dt.date.today()
    proposals.ensure_schema(conn)
    day = today.isoformat()
    counts = {r["status"]: r["c"] for r in conn.execute(
        "SELECT status, COUNT(*) c FROM agent_proposals"
        " WHERE date(created_at)=? GROUP BY status", (day,))}
    executed = conn.execute(
        "SELECT COUNT(*) c FROM agent_proposals WHERE date(executed_at)=?"
        " AND status='executed'", (day,)).fetchone()["c"]
    replies = conn.execute(
        "SELECT COUNT(*) c FROM inbox_messages WHERE kind='reply'"
        " AND date(received_at)=?", (day,)).fetchone()["c"]
    sent = conn.execute(
        "SELECT COUNT(*) c FROM send_log WHERE date(sent_at, 'localtime')=?",
        (day,)).fetchone()["c"]
    pending = proposals.summary(conn)["pending"]

    waiting_quotes = conn.execute(
        "SELECT COUNT(*) c FROM agent_proposals"
        " WHERE status='pending' AND kind='create_task'"
        "   AND (title LIKE '%你来定价%')").fetchone()["c"]

    lines = [f"【{day} 客户开发日报】"]
    lines.append(f"发出 {sent} 条，收到 {replies} 条客户回复")
    outcome = oversight.daily_outcome(conn)
    lines.append(
        f"合格新客 {outcome['achieved']}/{outcome['target']}（完成 {outcome['completion_pct']}%）")
    if not outcome["met"] and outcome["blockers"]:
        lines.append("未达标原因：" + "；".join(b["message"] for b in outcome["blockers"][:3]))
    # The one thing Allen asked to be told about directly: pricing is his.
    if waiting_quotes:
        lines.append(f"⚠ {waiting_quotes} 家在等你报价（Agent 不代报，需求已整理好）")
    if executed:
        lines.append(f"已执行 {executed} 条你确认过的提议")
    made = sum(counts.values())
    if made:
        lines.append(f"今天新提了 {made} 条建议"
                     + (f"，其中 {counts.get('rejected', 0)} 条被你驳回"
                        if counts.get("rejected") else ""))
    lines.append(f"还有 {pending} 条等你确认" if pending else "没有等你确认的事")
    last = agent_run.status(conn).get("last_result")
    if last:
        lines.append(f"最近一次运行：{last}")
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
