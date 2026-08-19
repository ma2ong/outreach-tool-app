"""The end-of-day note.

Allen does not sit in this tool all day. If the agent classified nine replies, drafted
four and is holding six decisions, that is worth one message on his phone — otherwise
the queue only exists for whoever remembers to open the page.

Feishu is optional: a custom-bot webhook URL in `backend/lark_webhook.txt`. Without it
the same text still lands on the Agent page, so nothing depends on the integration.
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


def webhook_url() -> str:
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        WEBHOOK_FILE)
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def compose(conn, today: dt.date | None = None) -> str:
    """What happened today, in the order Allen cares about."""
    from app.agent import proposals
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

    lines = [f"【{day} 客户开发日报】"]
    lines.append(f"发出 {sent} 条，收到 {replies} 条客户回复")
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


def push(text: str) -> str:
    """Send to Feishu. Returns '' on success, or the reason it did not go."""
    url = webhook_url()
    if not url:
        return "未配置 backend/lark_webhook.txt，日报只在页面上显示"
    body = json.dumps({"msg_type": "text", "content": {"text": text}}).encode("utf-8")
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return f"推送失败：{exc}"
    if data.get("code") not in (0, None):
        return f"飞书拒绝：{data.get('msg')}"
    return ""


def send_daily(conn, today: dt.date | None = None) -> dict:
    """Compose and push once per day. Idempotent: a second call the same day is a no-op."""
    today = today or dt.date.today()
    if settings.get(conn, _K_LAST_SENT) == today.isoformat():
        return {"sent": False, "reason": "今天已经发过日报"}
    text = compose(conn, today)
    problem = push(text)
    settings.set_value(conn, _K_LAST_SENT, today.isoformat())
    return {"sent": not problem, "reason": problem, "text": text}
