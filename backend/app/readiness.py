import json

from app import activities, autosend, contacts, mailboxes, settings
from app.agent import run as agent_run
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


def browser_installed() -> bool:
    """Whether Playwright has the chromium *it will ask for*. Cheap: two file reads, and
    the answer changes only when someone runs an install or upgrades the package.

    It used to glob `chromium*` and accept any revision found. That passes while every
    launch fails, which is the failure shape this whole module exists to prevent: an
    upgrade leaves the old revision on disk, Playwright asks for the new one, and the
    check says the browser is there. Ask the package which revision it wants.
    """
    import glob
    import json
    import os

    root = os.path.join(os.path.expanduser("~"), "AppData", "Local", "ms-playwright")
    wanted = None
    try:
        import playwright
        manifest = os.path.join(os.path.dirname(playwright.__file__),
                                "driver", "package", "browsers.json")
        with open(manifest, encoding="utf-8") as fh:
            for browser in json.load(fh).get("browsers", []):
                if browser.get("name") == "chromium":
                    wanted = str(browser.get("revision") or "")
                    break
    except Exception:  # noqa: BLE001 — an unreadable manifest falls back to the old test
        wanted = None

    pattern = f"chromium-{wanted}" if wanted else "chromium*"
    return bool(glob.glob(os.path.join(root, pattern, "chrome-win*", "chrome.exe"))
                or glob.glob(os.path.join(root, pattern, "chrome-linux", "chrome")))


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
    contact_stats = contacts.stats(conn)
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

    checks.append(_check(
        "contact_quality", "采购联系人",
        "ok" if contact_stats["decision_makers"] else "attention",
        (f"已标记 {contact_stats['decision_makers']} 位决策人，共 {contact_stats['named_contacts']} 位实名联系人"
         if contact_stats["decision_makers"] else
         f"已有 {contact_stats['named_contacts']} 位实名联系人，但尚未标记决策人/采购角色"),
        "leads",
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

    # "Enabled" is not "working". A run that marked the day done and then died leaves a
    # result line from an older date, which is the only visible trace — so compare them
    # rather than showing a green tick beside an engine that has not sent for a fortnight.
    stale_autosend = bool(
        auto["enabled"] and auto["last_date"] and auto["last_result"]
        and not auto["last_result"].startswith(auto["last_date"][5:]))
    if auto.get("safety_pause"):
        autosend_level = "blocked"
        autosend_detail = "Agent 已安全暂停：" + auto["safety_pause"]["reason"]
    elif not auto["enabled"]:
        autosend_level, autosend_detail = "attention", "默认关闭，可确认预览后启用"
    elif stale_autosend:
        autosend_level = "blocked"
        autosend_detail = (f"已启用但今天没跑成：最近一次结果还停在「{auto['last_result']}」，"
                           f"当前 {p['due']} 条到期未发")
    else:
        autosend_level, autosend_detail = "ok", "已启用，每日只运行一次"
    checks.append(_check("autosend", "邮件自动跟进", autosend_level, autosend_detail,
                         "dashboard"))

    # A model backend that quietly stops working looks exactly like "no replies worth
    # drafting today", which is the one failure Allen would never notice on his own.
    agent_status = agent_run.status(conn)
    broken = [f"{t}：{v['reason']}" for t, v in agent_status["llm"]["tasks"].items()
              if not v["ok"]]
    if broken:
        checks.append(_check("agent_llm", "Agent 模型接入", "attention",
                             "；".join(broken), "agent"))
    else:
        checks.append(_check(
            "agent_llm", "Agent 模型接入", "ok",
            f"分类走 {agent_status['llm']['tasks']['classify']['backend']}，"
            f"起草走 {agent_status['llm']['tasks']['draft']['backend']}", "agent"))

    # A missing browser only announces itself when Allen clicks 连接 and gets a 502.
    # Same lesson as autosend: the failure should be visible before he goes looking.
    if not browser_installed():
        checks.append(_check(
            "browser", "社媒浏览器", "blocked",
            "Playwright 的 Chromium 没装（升级后需重新下载）：在 backend 目录运行 "
            "python -m playwright install chromium。WhatsApp/Instagram 的连接、"
            "回复扫描和社媒起草在此之前都用不了", "channels"))

    # Copy that the guard will refuse is invisible until Allen picks it and gets a block
    # he cannot explain. Judged against a lead with every field filled in, so a refusal
    # here means this copy can never go to anyone (docs/82).
    from app import copy_health
    copy_scan = copy_health.scan(conn)
    if copy_scan["refused"]:
        names = "、".join(str(x["name"])[:16] for x in copy_scan["refused"][:3])
        more = f" 等 {len(copy_scan['refused'])} 条" if len(copy_scan["refused"]) > 3 else ""
        why = "、".join(f"{k} {v}" for k, v in copy_scan["by_reason"].items())
        checks.append(_check(
            "copy", "文案可发性", "attention",
            f"{names}{more}发不出去（{why}）——选中它们发送会被拦下，"
            "改掉或退役；{company} 缺失和退出语是最常见的两个原因", "outreach"))
    else:
        checks.append(_check(
            "copy", "文案可发性", "ok",
            f"{copy_scan['checked']} 条模板和序列步骤都能通过发送前检查", "outreach"))

    pending_proposals = agent_status["pending"]
    checks.append(_check(
        "agent_proposals", "Agent 待审批",
        "attention" if pending_proposals else "ok",
        f"{pending_proposals} 条提议等你确认" if pending_proposals else "没有待审批的提议",
        "agent"))

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
            "contacts": contact_stats,
            "autosend": auto,
            "agent": agent_status,
        },
    }
