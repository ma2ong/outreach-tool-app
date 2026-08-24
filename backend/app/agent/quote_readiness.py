"""Internal quote-readiness packet for LED opportunities.

This module intentionally stops before commercial commitment. It may assemble an exact
technical starter line from verified project/product facts, but it never supplies unit
price, freight, discount, payment terms, lead time, warranty or validity.
"""
from __future__ import annotations

from app.agent import led_playbook, product_advisor, solution_engineer


HUMAN_DECISIONS = (
    ("unit_price", "产品单价 / 计价方式"),
    ("shipping", "运费 / 物流费用"),
    ("incoterm", "Incoterm"),
    ("payment_terms", "付款条件"),
    ("lead_time", "生产 / 交期"),
    ("warranty", "质保条款"),
    ("valid_until", "报价有效期"),
    ("discount", "折扣（如有）"),
)


def _latest_quote(conn, opportunity_id: int) -> dict | None:
    from app import sales_documents

    sales_documents.ensure_schema(conn)
    row = conn.execute(
        "SELECT id, quote_no, status, currency, incoterm, destination, valid_until,"
        " payment_terms, lead_time, warranty, shipping, discount, total, updated_at"
        " FROM quotes WHERE opportunity_id=? ORDER BY id DESC LIMIT 1",
        (opportunity_id,),
    ).fetchone()
    return dict(row) if row else None


def _starter(solution: dict, opportunity: dict) -> dict | None:
    if not solution.get("ready"):
        return None
    product = solution.get("product") or {}
    layout = solution.get("selected_layout") or {}
    resolution = solution.get("resolution") or {}
    model = product.get("model")
    if not model or not layout:
        return None
    note_parts = [
        f"箱体 {layout.get('cabinet_columns')}×{layout.get('cabinet_rows')}",
        f"每屏 {layout.get('cabinets_per_screen')} 箱",
    ]
    if resolution:
        note_parts.append(
            f"分辨率 {resolution.get('screen_width_px')}×{resolution.get('screen_height_px')}px"
        )
    return {
        "description": opportunity.get("title") or model,
        "model": model,
        "pixel_pitch": product.get("pixel_pitch") or opportunity.get("pixel_pitch"),
        "width_m": layout.get("actual_width_m"),
        "height_m": layout.get("actual_height_m"),
        "quantity": int((solution.get("target") or {}).get("quantity") or 1),
        "area_sqm_per_screen": layout.get("area_sqm_per_screen"),
        "area_sqm_project": layout.get("area_sqm_project"),
        "cabinets_per_screen": layout.get("cabinets_per_screen"),
        "total_cabinets": layout.get("total_cabinets"),
        "screen_width_px": resolution.get("screen_width_px") if resolution else None,
        "screen_height_px": resolution.get("screen_height_px") if resolution else None,
        "pricing_unit_suggestion": "sqm",
        "note": "；".join(note_parts),
        "unit_price": None,
    }


def assess(conn, opportunity: dict, *, product_id: int | None = None) -> dict:
    """Return a human-pricing packet without crossing the commercial approval boundary."""
    qualification = led_playbook.qualification(opportunity)
    products = product_advisor.advise(conn, opportunity, limit=3)
    solution = solution_engineer.advise(conn, opportunity, product_id=product_id)

    # Lazy import avoids making Opportunity Coach depend on this commercial read model.
    from app.agent import opportunity_coach
    coverage = opportunity_coach.contact_coverage(conn, opportunity["lead_no"], opportunity)

    latest_quote = _latest_quote(conn, opportunity["id"])
    blockers: list[str] = []
    warnings: list[str] = []

    if not products.get("ready_to_recommend") and product_id is None:
        blockers.append(products.get("reason") or "产品匹配尚未达到安全推荐条件")
    if not solution.get("ready"):
        blockers.extend(solution.get("engineering_errors") or solution.get("gaps") or ["工程配置未准备好"])

    integrity = solution.get("engineering_integrity") or {}
    blockers.extend(integrity.get("errors") or [])
    warnings.extend(integrity.get("warnings") or [])

    if qualification["completeness"] < 60:
        warnings.append(
            f"项目资格完整度仅 {qualification['completeness']}%，报价前仍应补齐关键客户事实"
        )
    if not coverage["commercial_authority"]:
        warnings.append("尚未确认 Owner / Purchasing / Procurement 等商务决策人")
    if not coverage["project_authority"]:
        warnings.append("尚未确认 Project / AV / Technical 等项目技术负责人")

    layout = solution.get("selected_layout") or {}
    if layout and (layout.get("delta_width_mm") or layout.get("delta_height_mm")):
        warnings.append("实际箱体网格尺寸与客户目标尺寸存在差异；正式报价应使用实际尺寸并与客户确认")

    if latest_quote and latest_quote["status"] in ("sent", "accepted"):
        warnings.append(
            f"该商机已有 {latest_quote['status']} 报价 {latest_quote['quote_no']}，避免重复创建对外报价"
        )

    technical_ready = bool(solution.get("ready") and not integrity.get("errors"))
    ready_for_human_pricing = bool(technical_ready and (products.get("ready_to_recommend") or product_id is not None))

    commercial_values = latest_quote or {}
    human_decisions = []
    for key, label in HUMAN_DECISIONS:
        value = commercial_values.get(key)
        decided = value not in (None, "", 0, 0.0)
        human_decisions.append({
            "key": key,
            "label": label,
            "decided": decided,
            "value": value if decided else None,
            "owner": "human",
        })

    return {
        "opportunity_id": opportunity["id"],
        "lead_no": opportunity["lead_no"],
        "company_en": opportunity.get("company_en"),
        "title": opportunity.get("title"),
        "internal_only": True,
        "commercial_authority": "human_required",
        "technical_ready": technical_ready,
        "ready_for_human_pricing": ready_for_human_pricing,
        "qualification_pct": qualification["completeness"],
        "product_status": products.get("status"),
        "solution_status": solution.get("status"),
        "quote_starter": _starter(solution, opportunity),
        "latest_quote": latest_quote,
        "human_decisions": human_decisions,
        "blockers": list(dict.fromkeys(blockers)),
        "warnings": list(dict.fromkeys(warnings)),
        "safety": [
            "Quote Readiness 不产生单价、总价或折扣。",
            "付款条件、交期、质保和运费只能由人工确认。",
            "本结果不会自动创建、发送或标记正式报价。",
        ],
    }
