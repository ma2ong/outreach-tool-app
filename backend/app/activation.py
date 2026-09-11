"""A first-run path derived from the operating system's real configuration."""
from __future__ import annotations

import datetime as dt

from app import settings
from app.agent import mission, proposals


_REVIEW_KEYS = {
    "plan": "activation_plan_reviewed_at",
    "autonomy": "activation_autonomy_reviewed_at",
}


def _table_exists(conn, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def _knowledge_count(conn) -> int:
    products = conn.execute(
        "SELECT COUNT(*) c FROM products WHERE COALESCE(agent_approved,0)=1"
    ).fetchone()["c"]
    cases = 0
    if _table_exists(conn, "approved_cases"):
        cases = conn.execute(
            "SELECT COUNT(*) c FROM approved_cases WHERE shareable=1"
            " AND COALESCE(public_label,'')!='' AND COALESCE(public_summary,'')!=''"
        ).fetchone()["c"]
    return int(products) + int(cases)


def _verified_mailboxes(conn) -> int:
    rows = conn.execute("SELECT id FROM mailboxes WHERE active=1").fetchall()
    return sum(bool(settings.get(conn, f"mailbox_test_success:{row['id']}")) for row in rows)


def status(conn) -> dict:
    configured_mission = bool(settings.get(conn, "agent_sales_mission"))
    verified_mailboxes = _verified_mailboxes(conn)
    knowledge = _knowledge_count(conn)
    plan_reviewed = bool(settings.get(conn, _REVIEW_KEYS["plan"]))
    autonomy_reviewed = bool(settings.get(conn, _REVIEW_KEYS["autonomy"]))
    values = {
        "mission": configured_mission,
        "mailbox": verified_mailboxes > 0,
        "knowledge": knowledge > 0,
        "plan": plan_reviewed,
        "autonomy": autonomy_reviewed,
    }
    definitions = [
        ("mission", "确认开发目标", "明确国家、每日合格客户目标和最低质量门槛", "agent"),
        ("mailbox", "验证收发邮箱", "登录测试同时验证 SMTP 和 IMAP，不会发送邮件", "channels"),
        ("knowledge", "批准产品或案例", "至少一条经你批准的事实，Agent 才能专业回答", "products"),
        ("plan", "预演一天的工作", "先看 Agent 会做什么、什么情况会停下来找你", "dashboard"),
        ("autonomy", "确认权限边界", "只确认当前边界，不会自动提高任何自主度", "agent"),
    ]
    steps = [
        {"id": step_id, "label": label, "detail": detail,
         "action_page": page, "complete": values[step_id]}
        for step_id, label, detail, page in definitions
    ]
    completed = sum(1 for step in steps if step["complete"])
    from app import runtime
    live = runtime.status(conn)
    return {
        "prepared": completed == len(steps),
        "completed": completed,
        "total": len(steps),
        "steps": steps,
        "evidence": {
            "verified_mailboxes": verified_mailboxes,
            "approved_knowledge": knowledge,
        },
        "worker": {
            "active": bool(live.get("active")),
            "mode": (live.get("lease") or {}).get("mode"),
            "last_cycle_ok": (live.get("state") or {}).get("last_cycle_ok"),
            "last_error": (live.get("state") or {}).get("last_error"),
            "heartbeat_age_seconds": live.get("heartbeat_age_seconds"),
        },
    }


def preview(conn) -> dict:
    from app import autosend, social_autonomy

    return {
        "mission": mission.get(conn),
        "agent_work": [
            "research_public_company_facts",
            "qualify_and_route_prospects",
            "prepare_and_follow_approved_sequences",
            "classify_replies_and_prepare_next_actions",
        ],
        "allen_owns": [
            "pricing", "discounts", "payment_terms", "delivery_promises",
            "commercial_negotiation", "explicit_handoffs",
        ],
        "email_autosend": bool(autosend.status(conn)["enabled"]),
        "social_modes": social_autonomy.all_modes(conn),
        "guards": [
            "do_not_contact", "bounce_suppression", "daily_caps",
            "per_company_cadence", "message_quality", "delivery_intent",
        ],
    }


def acknowledge(conn, step: str) -> dict:
    key = _REVIEW_KEYS.get(step)
    if key is None:
        raise ValueError("only plan and autonomy review steps can be acknowledged")
    settings.set_value(conn, key, dt.datetime.now(dt.UTC).isoformat())
    return status(conn)
