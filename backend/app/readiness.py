import json

from app import activities, autosend, mailboxes, settings
from app.channels.email_adapter import get_password


def _reply_error_text(result) -> str:
    """The real reason, not a guess. 'Check your mailbox settings' sent Allen looking at
    config for what was actually the network being down at logon."""
    if isinstance(result, dict):
        errs = result.get("errors") or []
        if errs:
            first = errs[0]
            return f"{first.get('email', '')} {first.get('error', '')}".strip()[:140]
    return str(result or "")[:140]


def _check(check_id: str, label: str, status: str, detail: str, action_page: str) -> dict:
    return {
        "id": check_id,
        "label": label,
        "status": status,
        "detail": detail,
        "action_page": action_page,
    }


def build(conn) -> dict:
    active_mailboxes = conn.execute(
        "SELECT COUNT(*) AS c FROM mailboxes WHERE active=1").fetchone()["c"]
    fallback = bool(get_password())
    email_total = conn.execute(
        "SELECT COUNT(*) AS c FROM leads WHERE email IS NOT NULL AND email != ''").fetchone()["c"]
    email_checked = conn.execute(
        "SELECT COUNT(*) AS c FROM leads WHERE email_status IN ('valid', 'role', 'invalid')"
    ).fetchone()["c"]
    pending_replies = conn.execute(
        "SELECT COUNT(*) AS c FROM inbox_messages"
        " WHERE kind='reply' AND handled_at IS NULL"
    ).fetchone()["c"]
    activity_stats = activities.stats(conn)
    auto = autosend.status(conn)
    reply_status = settings.get(conn, "reply_sync_last_status")
    reply_at = settings.get(conn, "reply_sync_last_at") or None
    reply_success_at = settings.get(conn, "reply_sync_last_success_at") or None
    raw_reply_result = settings.get(conn, "reply_sync_last_result")
    try:
        reply_result = json.loads(raw_reply_result) if raw_reply_result else None
    except json.JSONDecodeError:
        reply_result = raw_reply_result

    checks = []
    if active_mailboxes or fallback:
        detail = (
            f"{active_mailboxes} 个轮换邮箱可用"
            if active_mailboxes else "备用 Gmail 已配置"
        )
        checks.append(_check("mailbox", "邮箱连接", "ok", detail, "channels"))
    else:
        checks.append(_check(
            "mailbox", "邮箱连接", "blocked",
            "没有可用邮箱，邮件发送和回复同步都无法运行", "channels"))

    if reply_status == "success":
        reply_detail = f"最近同步成功：{reply_at}"
        reply_level = "ok"
    elif reply_status == "partial":
        reply_detail = f"部分邮箱失败：{_reply_error_text(reply_result)}；系统会自动重试"
        reply_level = "attention"
    elif reply_status == "error":
        reply_detail = f"回复同步失败：{_reply_error_text(reply_result)}；系统每分钟自动重试"
        reply_level = "blocked"
    else:
        reply_detail = "尚未同步过回复，建议先执行一次"
        reply_level = "attention"
    checks.append(_check("reply_sync", "回复同步", reply_level, reply_detail, "inbox"))

    checks.append(_check(
        "pending_replies", "客户回复处理",
        "attention" if pending_replies else "ok",
        f"{pending_replies} 条真人回复仍需回复或安排下一步" if pending_replies else "没有遗漏的真人回复",
        "inbox",
    ))

    due_activities = activity_stats["overdue"] + activity_stats["today"]
    checks.append(_check(
        "sales_activities", "销售任务",
        "attention" if due_activities else "ok",
        (f"{activity_stats['overdue']} 项逾期，{activity_stats['today']} 项今天到期"
         if due_activities else f"没有逾期或今日任务，未来已安排 {activity_stats['upcoming']} 项"),
        "activities",
    ))

    p = auto["preview"]
    if p["due"] == 0:
        checks.append(_check("sequences", "邮件跟进", "ok", "当前没有到期邮件", "sequences"))
    else:
        checks.append(_check(
            "sequences", "邮件跟进", "attention",
            f"{p['due']} 条到期，今日安全额度内可发 {p['will_send']} 条", "sequences"))

    coverage = round(email_checked * 100 / email_total) if email_total else 100
    checks.append(_check(
        "email_quality", "邮箱质量", "ok" if coverage >= 80 else "attention",
        f"已验证 {email_checked}/{email_total} 个邮箱（{coverage}%）", "leads"))

    checks.append(_check(
        "autosend", "邮件自动跟进", "ok" if auto["enabled"] else "attention",
        "已启用，每日只运行一次" if auto["enabled"] else "默认关闭，可确认预览后启用",
        "dashboard"))

    levels = {c["status"] for c in checks}
    overall = "blocked" if "blocked" in levels else ("attention" if "attention" in levels else "ready")
    return {
        "status": overall,
        "checks": checks,
        "metrics": {
            "active_mailboxes": active_mailboxes,
            "fallback_gmail": fallback,
            "email_total": email_total,
            "email_checked": email_checked,
            "email_verified_coverage": coverage,
            "reply_sync_last_at": reply_at,
            "reply_sync_last_success_at": reply_success_at,
            "reply_sync_last_status": reply_status or None,
            "reply_sync_last_result": reply_result,
            "pending_replies": pending_replies,
            "activities": activity_stats,
            "autosend": auto,
        },
    }
