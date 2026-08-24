"""Read-only operating picture for the autonomous sales agent.

The Agent already has several durable sources of truth (proposal ledger, conversation
ownership, Account Brain and Opportunity Coach).  This module deliberately aggregates
those sources instead of inventing a second planner or execution path.
"""
from __future__ import annotations

import datetime as dt
from typing import Callable, TypeVar

from app import activities, autosend
from app.agent import account_brain, classify, conversation, opportunity_coach, proposals

LEDGER_LIMIT = 20
BACKLOG_LIMIT = 20
ACCOUNT_LIMIT = 8
OPPORTUNITY_LIMIT = 8
FAILURE_LOOKBACK_DAYS = 7

_T = TypeVar("_T")
_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "info": 3}


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _parse_time(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.UTC)
    return parsed.astimezone(dt.UTC)


def _safe(label: str, errors: list[dict], fn: Callable[[], _T], fallback: _T) -> _T:
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 — the control center must degrade, not vanish
        errors.append({"source": label, "error": f"{type(exc).__name__}: {str(exc)[:240]}"})
        return fallback


def execution_mode(row: dict) -> str:
    """Attribute a proposal without adding a migration just for presentation.

    Historic auto executions never received a decision timestamp; approved executions
    always did.  That lets the existing ledger explain who authorized an action.
    """
    status = row.get("status")
    if status == "pending":
        return "awaiting_approval"
    if status in proposals.APPROVED_STATUSES:
        return "executing"
    if row.get("decided_at"):
        return "approved"
    if row.get("executed_at") and status in ("executed", "failed"):
        return "auto"
    return "not_executed"


def _age_hours(value: str | None, now: dt.datetime) -> int | None:
    when = _parse_time(value)
    if not when:
        return None
    return max(0, int((now - when).total_seconds() // 3600))


def _proposal_rows(conn, limit: int = 200) -> list[dict]:
    proposals.ensure_schema(conn)
    rows = conn.execute(
        "SELECT p.*,l.company_en,l.country FROM agent_proposals p"
        " LEFT JOIN leads l ON l.no=p.lead_no"
        " ORDER BY COALESCE(p.executed_at,p.decided_at,p.updated_at,p.created_at) DESC,p.id DESC"
        " LIMIT ?",
        (max(1, min(int(limit), 500)),),
    ).fetchall()
    return [dict(row) for row in rows]


def _receipt(row: dict, now: dt.datetime) -> dict:
    return {
        "id": row["id"],
        "kind": row["kind"],
        "lead_no": row.get("lead_no"),
        "company_en": row.get("company_en"),
        "country": row.get("country"),
        "title": row.get("title") or "",
        "risk": row.get("risk") or "medium",
        "status": row.get("status") or "",
        "mode": execution_mode(row),
        "created_at": row.get("created_at"),
        "decided_at": row.get("decided_at"),
        "executed_at": row.get("executed_at"),
        "age_hours": _age_hours(row.get("created_at"), now),
        "result": (row.get("execution_result") or "")[:300],
    }


def _blocker(code: str, severity: str, title: str, detail: str, action: str,
             count: int = 1) -> dict:
    return {
        "code": code,
        "severity": severity,
        "title": title,
        "detail": detail,
        "action": action,
        "count": max(0, int(count)),
    }


def snapshot(conn, *, now: dt.datetime | None = None) -> dict:
    """Return one non-mutating autonomy/attention snapshot for the Agent page."""
    # Schema ownership is additive/idempotent. Ensuring activities here prevents a
    # newly-created DB from looking "partially broken" before the first task is ever made.
    activities.ensure_schema(conn)
    proposals.ensure_schema(conn)

    now = now or _now()
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.UTC)
    now = now.astimezone(dt.UTC)
    local_today = now.astimezone().date()
    errors: list[dict] = []

    rows = _safe("proposal_ledger", errors, lambda: _proposal_rows(conn), [])
    pending = [r for r in rows if r.get("status") in proposals.OPEN_STATUSES]
    true_pending = [r for r in pending if r.get("status") == "pending"]
    high_pending = [r for r in true_pending if r.get("risk") == "high"]

    lookback = now - dt.timedelta(days=FAILURE_LOOKBACK_DAYS)
    recent_failed = [
        r for r in rows
        if r.get("status") == "failed"
        and ((_parse_time(r.get("executed_at")) or _parse_time(r.get("updated_at")) or now) >= lookback)
    ]
    executed_today = [
        r for r in rows
        if r.get("status") == "executed"
        and (stamp := _parse_time(r.get("executed_at"))) is not None
        and stamp.astimezone().date() == local_today
    ]
    auto_today = [r for r in executed_today if execution_mode(r) == "auto"]
    approved_today = [r for r in executed_today if execution_mode(r) == "approved"]

    takeovers = _safe("conversation_takeovers", errors, lambda: conversation.takeovers(conn), [])
    unclassified = _safe("reply_classification", errors,
                         lambda: len(classify.pending(conn, limit=999)), 0)
    safety_pause = _safe("autosend_safety", errors, lambda: autosend.safety_pause(conn), None)
    due_accounts = _safe(
        "account_brain", errors,
        lambda: account_brain.due_accounts(conn, today=local_today, limit=ACCOUNT_LIMIT), [],
    )
    opportunity_rows = _safe(
        "opportunity_coach", errors,
        lambda: opportunity_coach.portfolio(conn, today=local_today, limit=30), [],
    )
    unhealthy = [r for r in opportunity_rows if r.get("severity") in ("critical", "high")]

    autonomy = _safe("autonomy", errors, lambda: proposals.autonomy_map(conn), {})
    autonomy_counts = {
        level: sum(1 for value in autonomy.values() if value == level)
        for level in proposals.AUTONOMY
    }

    blockers: list[dict] = []
    if safety_pause:
        blockers.append(_blocker(
            "safety_pause", "critical", "邮件自动跟进已安全暂停",
            str(safety_pause.get("reason") or "邮件安全闸已触发"),
            "先处理退信/邮箱健康问题，再由你明确恢复自动发信。",
        ))
    if unclassified:
        blockers.append(_blocker(
            "unclassified_replies", "high", f"{unclassified} 条客户回复还没完成意图分类",
            "Agent 只有在读懂客户意图后才会起草、停发或交给你报价。",
            "检查模型后端和最近 Agent 运行；分类完成后会进入下一动作。", unclassified,
        ))
    if high_pending:
        blockers.append(_blocker(
            "high_risk_approvals", "high", f"{len(high_pending)} 条高风险动作等你确认",
            "高风险动作不会因为追求自动化而绕过你的确认边界。",
            "在下方待确认队列优先处理这些动作。", len(high_pending),
        ))
    if recent_failed:
        blockers.append(_blocker(
            "recent_failures", "high", f"近 {FAILURE_LOOKBACK_DAYS} 天有 {len(recent_failed)} 条 Agent 动作失败",
            "失败动作不会盲目自动重试，尤其发送类动作可能已经部分完成。",
            "查看行动账本的失败结果，确认真实结果后再决定是否重跑。", len(recent_failed),
        ))
    if takeovers:
        blockers.append(_blocker(
            "human_takeovers", "medium", f"{len(takeovers)} 个会话仍由你接管",
            "报价、谈价或手动接管期间 Agent 不会抢回客户对话。",
            "商业事项处理完后，在 Agent 页明确“交回 Agent”。", len(takeovers),
        ))
    if due_accounts:
        blockers.append(_blocker(
            "due_accounts", "medium", f"{len(due_accounts)} 个已触达客户到了下一步时间",
            "这些客户没有回复、开放任务或活跃序列来拥有下一步。",
            "Account Brain 会按自主度创建内部下一步；若长期都在等你，可考虑仅把“建销售任务”调为自动。",
            len(due_accounts),
        ))
    if unhealthy:
        blockers.append(_blocker(
            "unhealthy_opportunities", "high",
            f"{len(unhealthy)} 个开放商机处于高/严重风险",
            "Opportunity Coach 检测到项目事实、决策人、产品/工程证据或下一步存在缺口。",
            "优先处理下方最高紧急度商机，不要只依赖 CRM 阶段标签。", len(unhealthy),
        ))
    off_kinds = [kind for kind, level in autonomy.items() if level == "off"]
    if off_kinds:
        blockers.append(_blocker(
            "autonomy_off", "info", f"{len(off_kinds)} 类 Agent 动作被你关闭",
            "这是明确的自主度设置，不代表 Worker 故障。",
            "如果这是有意设置，无需处理；否则在“任务书与自主度”里重新开启。", len(off_kinds),
        ))
    if errors:
        blockers.append(_blocker(
            "partial_snapshot", "medium", "控制中心有部分数据未能读取",
            "；".join(f"{item['source']}: {item['error']}" for item in errors[:3]),
            "刷新一次；如果持续出现，查看右下角 Sales Worker/生产健康状态。", len(errors),
        ))

    blockers.sort(key=lambda item: (_SEVERITY_ORDER.get(item["severity"], 9), -item["count"]))

    # A compact next-best-action list. These are recommendations only; the module does
    # not call proposals.create(), change a stage, send a message, or alter autonomy.
    next_actions: list[dict] = []
    for row in unhealthy[:OPPORTUNITY_LIMIT]:
        next_actions.append({
            "type": "opportunity",
            "severity": row.get("severity"),
            "lead_no": row.get("lead_no"),
            "opportunity_id": row.get("opportunity_id"),
            "company_en": row.get("company_en"),
            "title": row.get("title"),
            "due_at": row.get("next_action_date"),
            "score": row.get("health"),
            "action": row.get("next_best_action") or "确认商机下一步",
        })
    for row in due_accounts[:ACCOUNT_LIMIT]:
        next_actions.append({
            "type": "account",
            "severity": "medium",
            "lead_no": row.get("lead_no"),
            "opportunity_id": None,
            "company_en": row.get("company_en"),
            "title": "Account Brain",
            "due_at": row.get("due_date"),
            "score": row.get("score"),
            "action": row.get("next_action") or "确认下一步",
        })
    next_actions.sort(key=lambda item: (
        _SEVERITY_ORDER.get(str(item.get("severity")), 9),
        str(item.get("due_at") or "9999-12-31"),
        -(int(item.get("score") or 0)),
    ))

    pending_receipts = [_receipt(r, now) for r in true_pending[:BACKLOG_LIMIT]]
    ledger = [_receipt(r, now) for r in rows[:LEDGER_LIMIT]]

    critical = any(b["severity"] == "critical" for b in blockers)
    high = any(b["severity"] == "high" for b in blockers)
    state = "critical" if critical else "attention" if high or true_pending else "healthy"
    state_label = {
        "critical": "安全闸阻止了部分自动销售动作",
        "attention": "Agent 正常运行，但有事项需要处理",
        "healthy": "Agent 当前没有关键阻塞",
    }[state]

    return {
        "generated_at": now.isoformat(),
        "state": state,
        "state_label": state_label,
        "counters": {
            "awaiting_approval": len(true_pending),
            "high_risk_approval": len(high_pending),
            "auto_executed_today": len(auto_today),
            "approved_executed_today": len(approved_today),
            "failed_7d": len(recent_failed),
            "human_takeovers": len(takeovers),
            "due_accounts": len(due_accounts),
            "unhealthy_opportunities": len(unhealthy),
            "unclassified_replies": int(unclassified),
        },
        "autonomy": {"by_kind": autonomy, "counts": autonomy_counts},
        "blockers": blockers,
        "next_actions": next_actions[:12],
        "approval_backlog": pending_receipts,
        "ledger": ledger,
        "errors": errors,
    }
