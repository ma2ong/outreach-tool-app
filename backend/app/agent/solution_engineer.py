"""Deterministic internal LED project configuration engineering.

Every number here is derived from explicit opportunity fields and an explicitly
Agent-approved product row. Missing facts stay missing. The module never prices,
commits delivery, guesses controller specifications, or turns nominal pitch text into
an exact cabinet resolution.
"""
from __future__ import annotations

import math
import re

from app.agent import product_advisor
from app.db import init_schema


ENGINEERING_PRODUCT_FIELDS = (
    "id", "model", "agent_approved", "pixel_pitch", "brightness", "use_case",
    "indoor_outdoor", "refresh_rate_hz", "maintenance_access", "cabinet_size",
    "control_system", "cabinet_width_mm", "cabinet_height_mm", "cabinet_resolution_w",
    "cabinet_resolution_h", "module_width_mm", "module_height_mm",
    "max_power_w_cabinet", "avg_power_w_cabinet",
)


def _num(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _positive(value) -> float | None:
    value = _num(value)
    return value if value is not None and value > 0 else None


def _positive_int(value) -> int | None:
    value = _positive(value)
    return int(value) if value is not None and float(value).is_integer() else None


def _product(conn, product_id: int) -> dict | None:
    init_schema(conn)
    fields = ",".join(ENGINEERING_PRODUCT_FIELDS)
    row = conn.execute(f"SELECT {fields} FROM products WHERE id=?", (product_id,)).fetchone()
    return dict(row) if row else None


def _exact_nominal_pitch(value) -> float | None:
    values = re.findall(r"\d+(?:\.\d+)?", str(value or ""))
    if len(values) != 1:
        return None
    try:
        pitch = float(values[0])
    except ValueError:
        return None
    return pitch if pitch > 0 else None


def engineering_integrity(product: dict) -> dict:
    """Cross-check explicit engineering facts without silently correcting any of them."""
    errors: list[str] = []
    warnings: list[str] = []
    derived: dict[str, float] = {}

    cab_w = _positive(product.get("cabinet_width_mm"))
    cab_h = _positive(product.get("cabinet_height_mm"))
    px_w = _positive_int(product.get("cabinet_resolution_w"))
    px_h = _positive_int(product.get("cabinet_resolution_h"))

    pitch_x = cab_w / px_w if cab_w and px_w else None
    pitch_y = cab_h / px_h if cab_h and px_h else None
    if pitch_x is not None:
        derived["effective_pitch_x_mm"] = round(pitch_x, 5)
    if pitch_y is not None:
        derived["effective_pitch_y_mm"] = round(pitch_y, 5)

    effective = None
    if pitch_x is not None and pitch_y is not None:
        effective = (pitch_x + pitch_y) / 2
        derived["effective_pitch_mm"] = round(effective, 5)
        tolerance_xy = max(0.03, effective * 0.02)
        if abs(pitch_x - pitch_y) > tolerance_xy:
            errors.append(
                "箱体宽/像素宽与箱体高/像素高计算出的有效点间距不一致，请核对箱体分辨率"
            )
    elif pitch_x is not None or pitch_y is not None:
        effective = pitch_x if pitch_x is not None else pitch_y
        warnings.append("目前只能从一个方向校核有效点间距；另一方向的箱体尺寸/分辨率不完整")

    nominal = _exact_nominal_pitch(product.get("pixel_pitch"))
    if nominal is not None and effective is not None:
        derived["nominal_pitch_mm"] = nominal
        tolerance_nominal = max(0.05, nominal * 0.03)
        if abs(effective - nominal) > tolerance_nominal:
            errors.append(
                f"录入的箱体尺寸/分辨率对应约 P{effective:.3f}，与产品标称 P{nominal:g} 不一致"
            )

    max_w = _positive(product.get("max_power_w_cabinet"))
    avg_w = _positive(product.get("avg_power_w_cabinet"))
    if max_w and avg_w and avg_w > max_w:
        errors.append("单箱平均功耗不能高于单箱最大功耗，请核对产品工程数据")

    mod_w = _positive(product.get("module_width_mm"))
    mod_h = _positive(product.get("module_height_mm"))
    if cab_w and mod_w and mod_w > cab_w:
        errors.append("模组宽度大于箱体宽度，请核对模组/箱体尺寸")
    if cab_h and mod_h and mod_h > cab_h:
        errors.append("模组高度大于箱体高度，请核对模组/箱体尺寸")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "derived_checks": derived,
    }


def _axis_counts(target_mm: float, cabinet_mm: float) -> dict[str, int]:
    ratio = target_mm / cabinet_mm
    return {
        "fit_inside": max(1, math.floor(ratio)),
        "closest": max(1, math.floor(ratio + 0.5)),
        "cover_target": max(1, math.ceil(ratio)),
    }


def _layout(name: str, count_w: int, count_h: int, *, target_w_mm: float,
            target_h_mm: float, cabinet_w_mm: float, cabinet_h_mm: float,
            quantity: int) -> dict:
    actual_w = count_w * cabinet_w_mm
    actual_h = count_h * cabinet_h_mm
    cabinets = count_w * count_h
    delta_w = actual_w - target_w_mm
    delta_h = actual_h - target_h_mm
    return {
        "name": name,
        "cabinet_columns": count_w,
        "cabinet_rows": count_h,
        "cabinets_per_screen": cabinets,
        "total_cabinets": cabinets * quantity,
        "actual_width_mm": round(actual_w, 3),
        "actual_height_mm": round(actual_h, 3),
        "actual_width_m": round(actual_w / 1000, 4),
        "actual_height_m": round(actual_h / 1000, 4),
        "area_sqm_per_screen": round((actual_w * actual_h) / 1_000_000, 4),
        "area_sqm_project": round((actual_w * actual_h) / 1_000_000 * quantity, 4),
        "delta_width_mm": round(delta_w, 3),
        "delta_height_mm": round(delta_h, 3),
        "delta_width_pct": round(delta_w / target_w_mm * 100, 3),
        "delta_height_pct": round(delta_h / target_h_mm * 100, 3),
    }


def _layout_options(target_w_mm: float, target_h_mm: float, cabinet_w_mm: float,
                    cabinet_h_mm: float, quantity: int) -> list[dict]:
    widths = _axis_counts(target_w_mm, cabinet_w_mm)
    heights = _axis_counts(target_h_mm, cabinet_h_mm)
    options = []
    seen: set[tuple[int, int]] = set()
    for name in ("fit_inside", "closest", "cover_target"):
        key = (widths[name], heights[name])
        if key in seen:
            continue
        seen.add(key)
        options.append(_layout(
            name, key[0], key[1], target_w_mm=target_w_mm, target_h_mm=target_h_mm,
            cabinet_w_mm=cabinet_w_mm, cabinet_h_mm=cabinet_h_mm, quantity=quantity,
        ))
    return options


def _selected(options: list[dict]) -> dict:
    closest = next((row for row in options if row["name"] == "closest"), None)
    if closest:
        return closest
    return min(options, key=lambda row: abs(row["delta_width_mm"]) + abs(row["delta_height_mm"]))


def _resolution(product: dict, layout: dict, quantity: int, gaps: list[str]) -> dict | None:
    cabinet_w_px = _positive_int(product.get("cabinet_resolution_w"))
    cabinet_h_px = _positive_int(product.get("cabinet_resolution_h"))
    if not cabinet_w_px or not cabinet_h_px:
        gaps.append("产品缺少精确箱体分辨率，不能用标称点间距反推精确分辨率")
        return None
    width_px = cabinet_w_px * layout["cabinet_columns"]
    height_px = cabinet_h_px * layout["cabinet_rows"]
    pixels = width_px * height_px
    return {
        "cabinet_resolution": f"{cabinet_w_px}×{cabinet_h_px}",
        "screen_width_px": width_px,
        "screen_height_px": height_px,
        "pixels_per_screen": pixels,
        "pixels_project": pixels * quantity,
    }


def _power(product: dict, layout: dict, quantity: int, voltage: float | None,
           gaps: list[str]) -> dict | None:
    max_w = _positive(product.get("max_power_w_cabinet"))
    avg_w = _positive(product.get("avg_power_w_cabinet"))
    if not max_w and not avg_w:
        gaps.append("产品缺少单箱最大/平均功耗，暂不能计算屏体功耗")
        return None
    cabinets = layout["cabinets_per_screen"]
    out: dict = {
        "max_power_w_cabinet": max_w,
        "avg_power_w_cabinet": avg_w,
    }
    if max_w:
        per_screen = max_w * cabinets
        out["max_power_w_per_screen"] = round(per_screen, 2)
        out["max_power_w_project"] = round(per_screen * quantity, 2)
        if voltage:
            out["input_voltage_v"] = voltage
            out["theoretical_max_current_a_per_screen"] = round(per_screen / voltage, 2)
            out["theoretical_max_current_a_project"] = round(per_screen * quantity / voltage, 2)
            out["current_note"] = "仅为 W÷V 的内部容量估算；不等同断路器、线径、相负载或当地电气设计。"
        else:
            gaps.append("项目未记录输入电压，不能计算理论电流")
    else:
        gaps.append("产品缺少单箱最大功耗，不能计算最大容量/理论电流")
    if avg_w:
        per_screen_avg = avg_w * cabinets
        out["avg_power_w_per_screen"] = round(per_screen_avg, 2)
        out["avg_power_w_project"] = round(per_screen_avg * quantity, 2)
    return out


def _control(resolution: dict | None, opportunity: dict, quantity: int,
             gaps: list[str]) -> dict | None:
    if not resolution:
        gaps.append("没有精确屏体像素数，不能计算控制系统容量")
        return None
    capacity = _positive_int(opportunity.get("controller_capacity_px"))
    if not capacity:
        gaps.append("项目未记录已核实的单台控制器像素容量")
        return None
    pixels = resolution["pixels_per_screen"]
    by_capacity = math.ceil(pixels / capacity)
    out = {
        "controller_capacity_px": capacity,
        "minimum_units_by_pixel_capacity_per_screen": by_capacity,
    }
    ports = _positive_int(opportunity.get("controller_output_ports"))
    max_per_port = _positive_int(opportunity.get("max_pixels_per_port"))
    minimum = by_capacity
    if ports and max_per_port:
        required_ports = math.ceil(pixels / max_per_port)
        by_ports = math.ceil(required_ports / ports)
        minimum = max(minimum, by_ports)
        out.update({
            "controller_output_ports": ports,
            "max_pixels_per_port": max_per_port,
            "required_output_ports_per_screen": required_ports,
            "minimum_units_by_ports_per_screen": by_ports,
        })
    elif ports or max_per_port:
        gaps.append("控制系统端口数/单端口像素上限只填写了一项，不能完成端口容量校核")
    else:
        gaps.append("未记录控制器端口数和单端口像素上限；当前只按总像素容量计算")
    out["minimum_controller_units_per_screen"] = minimum
    out["minimum_controller_units_if_each_screen_independent"] = minimum * quantity
    out["pixel_capacity_utilization_pct"] = round(pixels / (minimum * capacity) * 100, 2)
    return out


def _spares(product: dict, layout: dict, quantity: int, spare_pct: float | None,
            gaps: list[str]) -> dict | None:
    if spare_pct is None:
        gaps.append("项目未设置备品比例，不生成任何备品数量")
        return None
    total_cabinets = layout["total_cabinets"]
    out = {
        "spare_pct": spare_pct,
        "spare_cabinets": math.ceil(total_cabinets * spare_pct / 100),
    }
    cab_w = _positive(product.get("cabinet_width_mm"))
    cab_h = _positive(product.get("cabinet_height_mm"))
    mod_w = _positive(product.get("module_width_mm"))
    mod_h = _positive(product.get("module_height_mm"))
    if not (cab_w and cab_h and mod_w and mod_h):
        gaps.append("产品缺少精确模组尺寸，暂不能计算模组总数/备品")
        return out
    across = cab_w / mod_w
    down = cab_h / mod_h
    if abs(across - round(across)) > 1e-6 or abs(down - round(down)) > 1e-6:
        gaps.append("模组尺寸不能整除箱体尺寸，需要人工确认箱体内部排布")
        return out
    modules_per_cabinet = int(round(across) * round(down))
    total_modules = modules_per_cabinet * total_cabinets
    out.update({
        "modules_per_cabinet": modules_per_cabinet,
        "total_modules": total_modules,
        "spare_modules": math.ceil(total_modules * spare_pct / 100),
    })
    return out


def _choose_product(conn, opportunity: dict, product_id: int | None) -> tuple[dict | None, dict]:
    """Return product and selection metadata without bypassing Product Advisor safety."""
    if product_id is not None:
        product = _product(conn, int(product_id))
        if not product:
            return None, {"status": "product_not_found", "reason": "产品不存在"}
        if not bool(product.get("agent_approved")):
            return None, {"status": "product_not_approved", "reason": "该产品尚未批准给 Agent 使用"}
        scored = product_advisor.score_product(product, opportunity)
        if scored["excluded"]:
            return None, {
                "status": "product_conflict", "reason": "手工选择的产品与项目明确条件冲突",
                "product": {"id": product["id"], "model": product["model"]},
                "conflicts": scored["reasons"],
            }
        return product, {
            "status": "manual_approved_product", "reason": None,
            "score": scored["score"], "gaps": scored["gaps"],
        }

    advice = product_advisor.advise(conn, opportunity, limit=3)
    if not advice.get("ready_to_recommend") or not advice.get("recommendations"):
        return None, {
            "status": advice.get("status") or "product_not_ready",
            "reason": advice.get("reason") or "Product Advisor 尚未达到自动选型条件",
        }
    top = advice["recommendations"][0]
    product = _product(conn, top["product_id"])
    return product, {
        "status": "auto_selected", "reason": None,
        "score": top.get("score"), "gaps": top.get("gaps", []),
    }


def advise(conn, opportunity: dict, *, product_id: int | None = None) -> dict:
    """Build one internal engineering proposal for an opportunity."""
    product, selection = _choose_product(conn, opportunity, product_id)
    base = {
        "opportunity_id": opportunity["id"],
        "lead_no": opportunity["lead_no"],
        "company_en": opportunity.get("company_en"),
        "title": opportunity.get("title"),
        "selection": selection,
        "internal_only": True,
        "commercial_authority": "none",
        "safety_notes": [
            "本结果只做内部工程配置，不生成或发送价格、付款条款、交期承诺。",
            "配电电流仅在有明确电压时做 W÷V 容量估算，不替代电气设计。",
            "控制容量只使用项目中人工核实并录入的容量/端口数据，不内置任何控制器型号参数。",
        ],
    }
    if product is None:
        return {**base, "status": selection["status"], "ready": False,
                "product": None, "gaps": [selection.get("reason") or "没有可用产品"]}

    product_public = {field: product.get(field) for field in ENGINEERING_PRODUCT_FIELDS
                      if field not in ("agent_approved",) and product.get(field) not in (None, "")}
    integrity = engineering_integrity(product)
    if integrity["errors"]:
        return {
            **base,
            "status": "invalid_product_engineering_facts",
            "ready": False,
            "product": product_public,
            "engineering_integrity": integrity,
            "engineering_errors": integrity["errors"],
            "gaps": integrity["errors"],
        }

    gaps: list[str] = []
    target_w_m = _positive(opportunity.get("width_m"))
    target_h_m = _positive(opportunity.get("height_m"))
    quantity = _positive_int(opportunity.get("quantity")) or 1
    cabinet_w = _positive(product.get("cabinet_width_mm"))
    cabinet_h = _positive(product.get("cabinet_height_mm"))

    if not target_w_m or not target_h_m:
        if not target_w_m:
            gaps.append("项目缺少目标宽度")
        if not target_h_m:
            gaps.append("项目缺少目标高度")
        return {**base, "status": "needs_project_dimensions", "ready": False,
                "product": product_public, "engineering_integrity": integrity, "gaps": gaps}
    if not cabinet_w or not cabinet_h:
        if not cabinet_w:
            gaps.append("产品缺少精确箱体宽度 mm")
        if not cabinet_h:
            gaps.append("产品缺少精确箱体高度 mm")
        return {**base, "status": "needs_product_engineering_facts", "ready": False,
                "product": product_public, "engineering_integrity": integrity, "gaps": gaps}

    options = _layout_options(target_w_m * 1000, target_h_m * 1000, cabinet_w, cabinet_h, quantity)
    layout = _selected(options)
    if layout["delta_width_mm"] or layout["delta_height_mm"]:
        gaps.append(
            "最接近箱体网格与客户目标尺寸存在差异："
            f"宽 {layout['delta_width_mm']:+g}mm，高 {layout['delta_height_mm']:+g}mm；报价前需确认实际尺寸。"
        )
    resolution = _resolution(product, layout, quantity, gaps)
    voltage = _positive(opportunity.get("input_voltage_v"))
    power = _power(product, layout, quantity, voltage, gaps)
    control = _control(resolution, opportunity, quantity, gaps)
    spare_raw = opportunity.get("spare_pct")
    spare_pct = None if spare_raw in (None, "") else float(spare_raw)
    spares = _spares(product, layout, quantity, spare_pct, gaps)

    sections_ready = {
        "layout": True,
        "resolution": resolution is not None,
        "power": power is not None,
        "control": control is not None,
        "spares": spares is not None,
    }
    completeness = round(sum(1 for ready in sections_ready.values() if ready) / len(sections_ready) * 100)
    return {
        **base,
        "status": "ready" if resolution is not None else "layout_ready_resolution_missing",
        "ready": resolution is not None,
        "engineering_completeness_pct": completeness,
        "engineering_integrity": integrity,
        "engineering_errors": [],
        "product": product_public,
        "target": {
            "width_m": target_w_m, "height_m": target_h_m, "quantity": quantity,
            "requested_area_sqm_per_screen": round(target_w_m * target_h_m, 4),
            "requested_area_sqm_project": round(target_w_m * target_h_m * quantity, 4),
        },
        "layout_options": options,
        "selected_layout": layout,
        "resolution": resolution,
        "power": power,
        "control": control,
        "spares": spares,
        "sections_ready": sections_ready,
        "gaps": list(dict.fromkeys(gaps)),
        "facts_used": {
            "project": {
                key: opportunity.get(key) for key in (
                    "width_m", "height_m", "quantity", "input_voltage_v",
                    "controller_capacity_px", "controller_output_ports",
                    "max_pixels_per_port", "spare_pct",
                ) if opportunity.get(key) not in (None, "")
            },
            "product": product_public,
        },
    }
