"""Evidence-only LED product matching for opportunities and reply drafting.

The advisor never creates a product fact. It reads only product rows Allen explicitly
approved for Agent use, treats explicit contradictions as hard exclusions, and exposes
customer-safe facts without reference prices or private customer history.
"""
from __future__ import annotations

import re

from app.agent import led_playbook


SAFE_FIELDS = (
    "id", "model", "pixel_pitch", "brightness", "use_case", "indoor_outdoor",
    "refresh_rate_hz", "maintenance_access", "cabinet_size", "control_system",
)

_USE_CASE_WORDS = {
    "Rental": ("rental", "event", "concert", "stage", "festival", "租赁", "活动", "舞台"),
    "Virtual Production": ("xr", "virtual production", "studio", "broadcast", "虚拟制作", "摄影棚"),
    "DOOH": ("dooh", "billboard", "facade", "outdoor advertising", "广告", "户外大屏"),
    "Sports": ("sport", "stadium", "arena", "scoreboard", "体育", "球场"),
    "Control Room": ("control room", "command center", "monitoring", "控制室", "指挥中心"),
    "Broadcast": ("broadcast", "tv studio", "camera", "电视", "演播室"),
    "Retail": ("retail", "store", "mall", "showroom", "零售", "商场", "展厅"),
    "Church": ("church", "worship", "教会", "礼拜"),
    "Fixed Installation": ("fixed", "installation", "conference", "boardroom", "固定安装", "会议室"),
}


def _text(value) -> str:
    return str(value or "").strip()


def _numbers(value) -> list[float]:
    out = []
    for raw in re.findall(r"\d+(?:\.\d+)?", _text(value)):
        try:
            out.append(float(raw))
        except ValueError:
            pass
    return out


def _pitch(value) -> float | None:
    values = _numbers(value)
    return values[0] if values else None


def _range(value) -> tuple[float, float] | None:
    values = _numbers(value)
    if not values:
        return None
    if len(values) == 1:
        return values[0], values[0]
    return min(values[0], values[1]), max(values[0], values[1])


def _environment(value: str | None) -> str | None:
    raw = _text(value).lower()
    if not raw:
        return None
    if "out" in raw or "户外" in raw or "室外" in raw:
        return "Outdoor"
    if "in" in raw or "室内" in raw:
        return "Indoor"
    return None


def _inferred_product_environment(product: dict) -> str | None:
    explicit = _environment(product.get("indoor_outdoor"))
    if explicit:
        return explicit
    # Model names such as "Outdoor Rental" are themselves approved catalog text. Use
    # them only for matching; customer-facing facts still expose indoor_outdoor only
    # when the explicit field exists.
    return _environment(product.get("model"))


def _use_case_match(product: dict, application: str) -> bool:
    haystack = f"{_text(product.get('model'))} {_text(product.get('use_case'))}".lower()
    return any(word in haystack for word in _USE_CASE_WORDS.get(application, ()))


def approved_products(conn) -> list[dict]:
    columns = ",".join(SAFE_FIELDS) + ", agent_approved"
    return [dict(r) for r in conn.execute(
        f"SELECT {columns} FROM products WHERE COALESCE(agent_approved,0)=1 ORDER BY id"
    ).fetchall()]


def _history(conn, product: dict) -> dict:
    """Internal confidence only. Never returned by customer_safe_context()."""
    from app import sales_documents

    sales_documents.ensure_schema(conn)
    model = _text(product.get("model"))
    pitch = _text(product.get("pixel_pitch"))
    if not model and not pitch:
        return {"sent_quotes": 0, "accepted_quotes": 0, "orders": 0}
    where = ["q.status IN ('sent','accepted')"]
    params: list = []
    identity = []
    if model:
        identity.append("lower(COALESCE(qi.model,''))=lower(?)")
        params.append(model)
    if pitch:
        identity.append("lower(COALESCE(qi.pixel_pitch,''))=lower(?)")
        params.append(pitch)
    row = conn.execute(
        "SELECT COUNT(DISTINCT q.id) sent_quotes,"
        " COUNT(DISTINCT CASE WHEN q.status='accepted' THEN q.id END) accepted_quotes,"
        " COUNT(DISTINCT o.id) orders"
        " FROM quote_items qi JOIN quotes q ON q.id=qi.quote_id"
        " LEFT JOIN orders o ON o.quote_id=q.id"
        " WHERE " + " AND ".join(where) + " AND (" + " OR ".join(identity) + ")",
        params,
    ).fetchone()
    return {k: int(row[k] or 0) for k in ("sent_quotes", "accepted_quotes", "orders")}


def score_product(product: dict, opportunity: dict) -> dict:
    """Score one approved product; explicit incompatibilities are hard exclusions."""
    reasons: list[str] = []
    gaps: list[str] = []
    score = 20  # approval itself is evidence that this is a real sellable product row
    excluded = False

    application = led_playbook.normalize_use_case(opportunity.get("use_case"))
    if application:
        if _use_case_match(product, application):
            score += 22
            reasons.append(f"应用匹配：{application}")
        else:
            gaps.append(f"产品应用字段没有明确覆盖 {application}")

    wanted_env = _environment(opportunity.get("indoor_outdoor"))
    product_env = _inferred_product_environment(product)
    if wanted_env:
        if product_env and product_env != wanted_env:
            excluded = True
            reasons.append(f"环境冲突：项目 {wanted_env} / 产品 {product_env}")
        elif product_env == wanted_env:
            score += 20
            reasons.append(f"环境匹配：{wanted_env}")
        else:
            gaps.append("产品未记录室内/户外属性")

    wanted_pitch = _pitch(opportunity.get("pixel_pitch"))
    pitch_range = _range(product.get("pixel_pitch"))
    if wanted_pitch is not None:
        if pitch_range is None:
            gaps.append("产品未记录点间距")
        elif not (pitch_range[0] - 1e-6 <= wanted_pitch <= pitch_range[1] + 1e-6):
            excluded = True
            reasons.append(f"点间距冲突：项目 P{wanted_pitch:g} 不在产品范围")
        else:
            score += 28
            reasons.append(f"点间距覆盖 P{wanted_pitch:g}")

    wanted_brightness = opportunity.get("brightness_nits")
    brightness_range = _range(product.get("brightness"))
    if wanted_brightness not in (None, "", 0):
        try:
            wanted_brightness = float(wanted_brightness)
        except (TypeError, ValueError):
            wanted_brightness = None
        if wanted_brightness:
            if brightness_range is None:
                gaps.append("产品未记录亮度")
            elif brightness_range[1] + 1e-6 < wanted_brightness:
                excluded = True
                reasons.append(f"亮度冲突：项目要求 {wanted_brightness:g} nits，产品记录上限不足")
            elif brightness_range[0] <= wanted_brightness <= brightness_range[1]:
                score += 16
                reasons.append(f"亮度范围覆盖 {wanted_brightness:g} nits")
            else:
                # A product rated above the requested minimum is not incompatible.
                score += 10
                reasons.append("产品记录亮度不低于项目要求")

    wanted_refresh = opportunity.get("refresh_rate_hz")
    product_refresh = product.get("refresh_rate_hz")
    if wanted_refresh not in (None, "", 0):
        try:
            wanted_refresh = int(wanted_refresh)
        except (TypeError, ValueError):
            wanted_refresh = None
        if wanted_refresh:
            if not product_refresh:
                gaps.append("产品未记录刷新率")
            elif int(product_refresh) < wanted_refresh:
                excluded = True
                reasons.append(f"刷新率冲突：项目要求 {wanted_refresh}Hz，产品记录 {product_refresh}Hz")
            else:
                score += 14
                reasons.append(f"刷新率满足 ≥{wanted_refresh}Hz")

    wanted_maintenance = _text(opportunity.get("maintenance_access")).lower()
    product_maintenance = _text(product.get("maintenance_access")).lower()
    if wanted_maintenance:
        if not product_maintenance:
            gaps.append("产品未记录维护方式")
        elif wanted_maintenance not in product_maintenance and product_maintenance not in wanted_maintenance:
            gaps.append("维护方式需要人工确认")
        else:
            score += 8
            reasons.append("维护方式匹配")

    if opportunity.get("control_system") and not product.get("control_system"):
        gaps.append("产品未记录控制系统适配信息")
    if opportunity.get("cabinet_size") and not product.get("cabinet_size"):
        gaps.append("产品未记录箱体尺寸/形式")

    return {
        "product_id": product["id"],
        "model": product["model"],
        "score": max(0, min(100, score)),
        "excluded": excluded,
        "reasons": reasons,
        "gaps": gaps,
        "facts": {field: product.get(field) for field in SAFE_FIELDS if field != "id" and product.get(field) not in (None, "", 0)},
    }


def advise(conn, opportunity: dict, *, limit: int = 3) -> dict:
    products = approved_products(conn)
    qualification = led_playbook.qualification(opportunity)
    if not products:
        return {
            "status": "no_approved_products", "qualification_pct": qualification["completeness"],
            "ready_to_recommend": False, "recommendations": [],
            "reason": "产品库里还没有明确批准给 Agent 使用的产品事实",
        }
    ranked = []
    for product in products:
        row = score_product(product, opportunity)
        if row["excluded"]:
            continue
        row["history"] = _history(conn, product)
        # History improves internal tie-breaking only; it never becomes a customer fact.
        row["internal_rank"] = row["score"] + min(8, row["history"]["orders"] * 3 + row["history"]["accepted_quotes"])
        ranked.append(row)
    ranked.sort(key=lambda r: (-r["internal_rank"], len(r["gaps"]), r["product_id"]))
    ready = qualification["completeness"] >= 45 and bool(ranked)
    return {
        "status": "ready" if ready else "needs_more_project_facts",
        "qualification_pct": qualification["completeness"],
        "ready_to_recommend": ready,
        "recommendations": ranked[:max(1, min(int(limit), 10))],
        "reason": None if ready else (qualification["next_question"] or "需要更多项目事实才能安全推荐产品"),
    }


def customer_safe_context(advice: dict) -> dict:
    """Strip prices, customer history and internal scoring before LLM reply context."""
    return {
        "status": advice.get("status"),
        "qualification_pct": advice.get("qualification_pct"),
        "ready_to_recommend": advice.get("ready_to_recommend", False),
        "reason": advice.get("reason"),
        "products": [
            {
                "model": row["model"],
                "facts": row["facts"],
                "gaps": row["gaps"],
            }
            for row in advice.get("recommendations", [])
        ],
    }
