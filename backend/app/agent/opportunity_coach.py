"""Pipeline coaching for real LED opportunities.

Stage labels are not progress. A healthy deal has enough project facts for its stage,
relevant authority coverage and one dated next action. This module turns those rules
into deterministic coaching and, when nobody else owns the step, an internal task
proposal. It never sends a customer-facing message.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re

from app.agent import led_playbook, proposals

MAX_WORLD_ROWS = 12
MAX_SAFETY_NET = 3

COMMERCIAL_TITLES = re.compile(
    r"\b(owner|founder|ceo|president|principal|procurement|purchasing|buyer|commercial)\b|"
    r"대표|사장|구매|采购|老板|总经理",
    re.I,
)
PROJECT_TITLES = re.compile(
    r"\b(project|technical|engineer|engineering|av manager|av director|production|operations)\b|"
    r"프로젝트|기술|엔지니어|영상|工程|技术|项目",
    re.I,
)
STAGE_WEIGHT = {"negotiation": 4, "quoted": 3, "requirements": 2, "qualified": 1}


def _date(value: str | None) -> dt.date | None:
    if not value:
        return None
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def contact_coverage(conn, lead_no: int, opportunity: dict | None = None) -> dict:
    from app import contacts

    rows = contacts.list_all(conn, lead_no=lead_no)
    commercial = False
    project = False
    evidence = []
    for contact in rows:
        title = (contact.get("title") or "").strip()
        role = contact.get("role") or "other"
        if role == "decision_maker" or COMMERCIAL_TITLES.search(title):
            commercial = True
            evidence.append({"kind": "commercial", "contact_id": contact["id"],
                             "name": contact.get("name"), "title": title,
                             "source": "explicit role" if role == "decision_maker" else "title"})
        if role == "technical" or PROJECT_TITLES.search(title):
            project = True
            evidence.append({"kind": "project", "contact_id": contact["id"],
                             "name": contact.get("name"), "title": title,
                             "source": "explicit role" if role == "technical" else "title"})
    expected = led_playbook.expected_roles(opportunity or {})
    missing = []
    if not commercial:
        missing.append(expected[0])
    if not project:
        missing.append(expected[1])
    return {
        "commercial_authority": commercial,
        "project_authority": project,
        "missing": missing,
        "evidence": evidence,
        "contacts": len(rows),
    }


def _fresh_signal(conn, lead_no: int, today: dt.date) -> dict | None:
    from app import sales_intelligence

    signals = sales_intelligence.list_signals(conn, lead_no=lead_no, limit=20)
    for signal in signals:
        if signal.get("status") == "dismissed":
            continue
        when = _date(signal.get("occurred_at") or signal.get("captured_at"))
        if when and (today - when).days <= 90 and int(signal.get("confidence") or 0) >= 60:
            return signal
    return None


def coach_opportunity(conn, opportunity: dict, *, today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    qual = led_playbook.qualification(opportunity)
    coverage = contact_coverage(conn, opportunity["lead_no"], opportunity)
    signal = _fresh_signal(conn, opportunity["lead_no"], today)
    next_date = _date(opportunity.get("next_action_date"))
    overdue = bool(next_date and next_date < today)
    missing_next_action = not bool((opportunity.get("next_action") or "").strip())
    missing_next_date = next_date is None
    stale = bool(opportunity.get("stale"))
    open_task = conn.execute(
        "SELECT id, title, due_at FROM activities WHERE opportunity_id=? AND status='open'"
        " ORDER BY due_at, id LIMIT 1",
        (opportunity["id"],),
    ).fetchone()

    health = 100
    risks = []
    if qual["completeness"] < 35:
        health -= 25
        risks.append("项目关键参数严重不足")
    elif qual["completeness"] < 60:
        health -= 15
        risks.append("项目资格信息仍不完整")
    elif qual["completeness"] < 80:
        health -= 6
    if missing_next_action:
        health -= 20
        risks.append("没有明确下一步动作")
    if missing_next_date:
        health -= 15
        risks.append("下一步没有日期")
    elif overdue:
        health -= 20
        risks.append(f"下一步已逾期 {(today - next_date).days} 天")
    if stale:
        health -= 10
        risks.append("商机长时间没有有效活动")
    if not coverage["commercial_authority"]:
        health -= 12
        risks.append("缺采购/商务决策人")
    if not coverage["project_authority"]:
        health -= 8
        risks.append("缺项目/技术负责人")
    if opportunity.get("stage") in ("quoted", "negotiation") and qual["completeness"] < 60:
        health -= 8
        risks.append("已进入报价/谈判，但技术资格仍偏弱")
    health = max(0, min(100, health))

    if overdue and opportunity.get("next_action"):
        next_best = f"立即完成逾期下一步：{opportunity['next_action']}"
    elif missing_next_action:
        next_best = qual["next_question"] or "先给这个商机定义一个具体下一步动作"
    elif missing_next_date:
        next_best = f"给下一步“{opportunity['next_action']}”确定日期和负责人"
    elif opportunity.get("stage") in ("quoted", "negotiation") and not coverage["commercial_authority"]:
        next_best = "补齐 Owner / Purchasing / Procurement 等商务决策人，再推进报价决定"
    elif opportunity.get("stage") in ("quoted", "negotiation") and not coverage["project_authority"]:
        next_best = "补齐 Project / AV / Technical 负责人，确认技术方案由谁签字"
    elif qual["next_question"]:
        next_best = qual["next_question"]
    elif signal:
        next_best = signal.get("suggested_angle") or f"核实新采购信号：{signal['headline']}"
    else:
        next_best = opportunity.get("next_action") or "确认项目下一次决策节点"

    severity = "critical" if health < 45 else "high" if health < 65 else "medium" if health < 80 else "low"
    urgency = 0
    urgency += STAGE_WEIGHT.get(opportunity.get("stage"), 0) * 10
    urgency += 25 if overdue else 15 if missing_next_date or missing_next_action else 0
    urgency += 10 if signal else 0
    urgency += min(20, round(float(opportunity.get("amount") or 0) / 5000))

    return {
        "opportunity_id": opportunity["id"],
        "lead_no": opportunity["lead_no"],
        "company_en": opportunity.get("company_en"),
        "title": opportunity["title"],
        "stage": opportunity["stage"],
        "amount": opportunity.get("amount"),
        "currency": opportunity.get("currency"),
        "health": health,
        "severity": severity,
        "urgency": urgency,
        "qualification": qual,
        "contact_coverage": coverage,
        "next_action": opportunity.get("next_action"),
        "next_action_date": opportunity.get("next_action_date"),
        "overdue": overdue,
        "stale": stale,
        "open_task": dict(open_task) if open_task else None,
        "fresh_signal": signal,
        "risks": risks,
        "next_best_action": next_best,
    }


def portfolio(conn, *, today: dt.date | None = None,
              limit: int = MAX_WORLD_ROWS) -> list[dict]:
    from app import opportunities

    today = today or dt.date.today()
    rows = [coach_opportunity(conn, opp, today=today)
            for opp in opportunities.list_all(conn, today=today)
            if opp["stage"] in opportunities.OPEN_STAGES]
    rows.sort(key=lambda row: (-row["urgency"], row["health"], row["opportunity_id"]))
    return rows[:max(1, min(int(limit), 100))]


def _issue_digest(row: dict) -> str:
    facts = {
        "health": row["health"], "risks": row["risks"],
        "next": row["next_best_action"],
        "missing": [m["key"] for m in row["qualification"]["missing"][:5]],
        "commercial": row["contact_coverage"]["commercial_authority"],
        "project": row["contact_coverage"]["project_authority"],
        "next_action_date": row.get("next_action_date"),
    }
    raw = json.dumps(facts, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def safety_net(conn, *, today: dt.date | None = None,
               limit: int = MAX_SAFETY_NET) -> dict:
    """Create internal proposals only when no existing opportunity task owns the step."""
    today = today or dt.date.today()
    made = []
    considered = []
    for row in portfolio(conn, today=today, limit=30):
        if len(considered) >= limit:
            break
        if row["severity"] == "low" or row["open_task"]:
            continue
        considered.append(row)
        title = f"商机体检：{row['company_en']} / {row['title']}"
        proposal = proposals.create(
            conn, "create_task", lead_no=row["lead_no"],
            title=title[:200],
            reasoning=(f"LED Opportunity Coach：健康度 {row['health']}/100（{row['severity']}）。"
                       + ("；".join(row["risks"]) if row["risks"] else "需要明确下一步")),
            evidence=[
                {"claim": "项目资格完整度", "source": f"{row['qualification']['completeness']}%"},
                {"claim": "建议下一步", "source": row["next_best_action"]},
            ],
            payload={
                "title": title[:200], "type": "task", "due_at": today.isoformat(),
                "priority": "high" if row["severity"] in ("critical", "high") else "normal",
                "note": (f"健康度 {row['health']}/100。"
                         f"风险：{'；'.join(row['risks']) or '需完善'}。"
                         f"下一步：{row['next_best_action']}")[:500],
            },
            risk="low",
            dedupe_key=f"opportunity-coach-{row['opportunity_id']}-{_issue_digest(row)}",
        )
        if proposal:
            made.append(proposal["id"])
    return {"considered": len(considered), "proposed": len(made), "ids": made,
            "opportunities": considered}
