"""One account view for the sales Agent.

Customer 360 stores nothing. It joins the existing CRM truths so planning, coaching and
future UI can answer "what is happening with this customer?" without inventing a second
account state.
"""
from __future__ import annotations


def build(conn, lead_no: int) -> dict | None:
    from app import (
        activities, case_library, contacts, decision_maker_radar, opportunities,
        sales_documents, sales_intelligence,
    )
    from app.agent import opportunity_coach

    sales_intelligence.ensure_schema(conn)
    sales_documents.ensure_schema(conn)
    decision_maker_radar.ensure_schema(conn)
    case_library.ensure_schema(conn)
    lead = conn.execute("SELECT * FROM leads WHERE no=?", (lead_no,)).fetchone()
    if lead is None:
        return None

    account = dict(lead)
    people = contacts.list_all(conn, lead_no=lead_no)
    contact_candidates = decision_maker_radar.list_candidates(
        conn, lead_no=lead_no, status="new", limit=10)
    opps = opportunities.list_all(conn, lead_no=lead_no)
    coached = [opportunity_coach.coach_opportunity(conn, opp) for opp in opps
               if opp["stage"] in opportunities.OPEN_STAGES]
    coached.sort(key=lambda row: (-row["urgency"], row["health"], row["opportunity_id"]))
    product_advice = [
        {
            "opportunity_id": row["opportunity_id"],
            "title": row["title"],
            "status": row["product_advice"].get("status"),
            "ready_to_recommend": row["product_advice"].get("ready_to_recommend"),
            "reason": row["product_advice"].get("reason"),
            "recommendations": row["product_advice"].get("recommendations", []),
        }
        for row in coached
    ]
    approved_case_matches = []
    for opp in opps:
        if opp["stage"] not in opportunities.OPEN_STAGES:
            continue
        matches = case_library.match(conn, opp, limit=5, shareable_only=True)
        approved_case_matches.append({
            "opportunity_id": opp["id"], "title": opp["title"], "cases": matches,
        })
    primary_opp = opps[0] if opps else None
    coverage = opportunity_coach.contact_coverage(conn, lead_no, primary_opp or {})
    signals = sales_intelligence.list_signals(conn, lead_no=lead_no, limit=10)
    score = sales_intelligence.score_lead(conn, lead_no, _ensure=False)

    open_tasks = [dict(r) for r in conn.execute(
        "SELECT id, opportunity_id, type, title, due_at, priority, source, note"
        " FROM activities WHERE lead_no=? AND status='open'"
        " ORDER BY due_at, id LIMIT 20", (lead_no,)
    ).fetchall()]
    inbound = [dict(r) for r in conn.execute(
        "SELECT id, contact_id, channel, subject, body, received_at, intent, handled_at"
        " FROM inbox_messages WHERE lead_no=? AND kind='reply'"
        " ORDER BY received_at DESC, id DESC LIMIT 10", (lead_no,)
    ).fetchall()]
    sends = [dict(r) for r in conn.execute(
        "SELECT channel, campaign, sent_at FROM send_log WHERE lead_no=?"
        " ORDER BY sent_at DESC LIMIT 10", (lead_no,)
    ).fetchall()]
    quotes = [dict(r) for r in conn.execute(
        "SELECT id, quote_no, opportunity_id, contact_id, title, status, currency, total,"
        " incoterm, destination, valid_until, sent_at, accepted_at, created_at, updated_at"
        " FROM quotes WHERE lead_no=? ORDER BY created_at DESC LIMIT 10", (lead_no,)
    ).fetchall()]
    orders = [dict(r) for r in conn.execute(
        "SELECT id, order_no, quote_id, opportunity_id, status, currency, total,"
        " deposit_amount, paid_amount, balance, expected_ship_date, shipped_at, tracking_no,"
        " created_at, updated_at FROM orders WHERE lead_no=?"
        " ORDER BY created_at DESC LIMIT 10", (lead_no,)
    ).fetchall()]

    risks = []
    for row in coached[:3]:
        risks.extend(f"{row['title']}：{risk}" for risk in row["risks"][:3])
    if coverage["missing"]:
        risks.extend(f"联系人缺口：{item['label']}" for item in coverage["missing"])
    if contact_candidates:
        risks.append(f"有 {len(contact_candidates)} 个公开关键联系人候选尚未确认")
    if account.get("email_status") == "invalid" and not account.get("phone") and not account.get("instagram"):
        risks.append("主邮箱无效且没有替代联系渠道")

    next_actions = []
    waiting = next((m for m in inbound if not m.get("handled_at")), None)
    if waiting:
        next_actions.append({"priority": "urgent", "source": "reply",
                             "action": "先处理客户最新回复", "ref_id": waiting["id"]})
    accepted = next((q for q in quotes if q["status"] == "accepted" and
                     not any(o["quote_id"] == q["id"] for o in orders)), None)
    if accepted:
        next_actions.append({"priority": "urgent", "source": "quote",
                             "action": f"报价 {accepted['quote_no']} 已接受，转为订单",
                             "ref_id": accepted["id"]})
    if contact_candidates:
        best = contact_candidates[0]
        next_actions.append({
            "priority": "high", "source": "contact_candidate",
            "action": f"确认关键联系人候选：{best['name']} / {best['title']}（{best['confidence']}/100）",
            "ref_id": best["id"],
        })
    for row in coached[:3]:
        next_actions.append({"priority": "high" if row["severity"] in ("critical", "high") else "normal",
                             "source": "opportunity", "action": row["next_best_action"],
                             "ref_id": row["opportunity_id"]})
    if not next_actions and score:
        next_actions.append({"priority": "normal", "source": "account",
                             "action": score["next_action"], "ref_id": lead_no})

    return {
        "account": account,
        "score": score,
        "contacts": people,
        "contact_candidates": contact_candidates,
        "contact_coverage": coverage,
        "opportunities": opps,
        "opportunity_coaching": coached,
        "product_advice": product_advice,
        "approved_case_matches": approved_case_matches,
        "buying_signals": signals,
        "open_tasks": open_tasks,
        "recent_inbound": inbound,
        "recent_sends": sends,
        "quotes": quotes,
        "orders": orders,
        "risks": list(dict.fromkeys(risks))[:12],
        "next_best_actions": next_actions[:6],
    }
