"""Deterministic LED-display qualification playbook.

A veteran salesperson does not ask every question at once. They identify the single
missing fact that most changes configuration, risk or commercial next steps. This module
encodes that ordering without recommending a technical value that is not already known.
"""
from __future__ import annotations

import re


# key -> (Chinese label, why it matters)
FIELD_META = {
    "use_case": ("应用场景", "不同应用决定产品、刷新率、结构和维护侧重点"),
    "indoor_outdoor": ("室内/户外环境", "环境决定亮度、防护、结构与维护要求"),
    "width_m": ("屏幕宽度", "实际尺寸决定箱体排布、分辨率和面积"),
    "height_m": ("屏幕高度", "实际尺寸决定箱体排布、分辨率和面积"),
    "viewing_distance_m": ("主要观看距离", "观看距离是判断合理点间距的重要输入"),
    "pixel_pitch": ("像素间距/清晰度目标", "点间距直接影响分辨率、观看效果与成本"),
    "brightness_nits": ("亮度要求", "环境光和户外朝向会改变所需亮度"),
    "refresh_rate_hz": ("刷新率要求", "拍摄、XR、广播和高端活动对刷新率更敏感"),
    "maintenance_access": ("维护方式/检修空间", "前维护或后维护会改变箱体和安装结构"),
    "cabinet_size": ("箱体尺寸/形式偏好", "租赁、弧形、快速搭建等场景依赖箱体形式"),
    "control_system": ("控制系统/信号源约束", "分辨率、备份、同步异步和集成方式影响方案"),
    "installation_type": ("安装结构/现场条件", "墙装、吊装、落地、弧形等直接影响结构方案"),
    "destination": ("项目目的地", "运输、认证、服务和交付方式需要目的地"),
    "quantity": ("数量", "多屏、多套或租赁库存需要准确数量"),
    "project_timing": ("项目时间节点", "决定样品、生产、运输和跟进节奏"),
    "budget_range": ("预算背景", "预算有助于在满足需求的方案之间取舍"),
    "decision_process": ("决策流程", "知道谁参与、何时决定，才能安排下一步"),
}

# Establish the physical project first. Application-specific technical questions then
# come before logistics/commercial tail fields such as destination and timing.
COMMON = ("use_case", "indoor_outdoor", "width_m", "height_m")
TAIL = ("destination", "project_timing")

# Ordered by discovery value, not by database column order.
APPLICATION_FIELDS = {
    "Rental": (
        "viewing_distance_m", "pixel_pitch", "refresh_rate_hz", "cabinet_size",
        "maintenance_access", "control_system", "quantity", "installation_type",
        "budget_range", "decision_process",
    ),
    "Virtual Production": (
        "viewing_distance_m", "pixel_pitch", "refresh_rate_hz", "control_system",
        "cabinet_size", "maintenance_access", "installation_type", "brightness_nits",
        "decision_process",
    ),
    "DOOH": (
        "brightness_nits", "viewing_distance_m", "pixel_pitch", "maintenance_access",
        "installation_type", "control_system", "quantity", "decision_process",
    ),
    "Sports": (
        "brightness_nits", "viewing_distance_m", "pixel_pitch", "refresh_rate_hz",
        "maintenance_access", "installation_type", "control_system", "quantity",
        "decision_process",
    ),
    "Control Room": (
        "viewing_distance_m", "pixel_pitch", "control_system", "maintenance_access",
        "refresh_rate_hz", "installation_type", "decision_process", "budget_range",
    ),
    "Broadcast": (
        "viewing_distance_m", "pixel_pitch", "refresh_rate_hz", "control_system",
        "maintenance_access", "installation_type", "decision_process",
    ),
    "Retail": (
        "viewing_distance_m", "pixel_pitch", "maintenance_access", "installation_type",
        "brightness_nits", "control_system", "quantity", "decision_process",
    ),
    "Church": (
        "viewing_distance_m", "pixel_pitch", "maintenance_access", "installation_type",
        "control_system", "brightness_nits", "decision_process", "budget_range",
    ),
    "Fixed Installation": (
        "viewing_distance_m", "pixel_pitch", "maintenance_access", "installation_type",
        "brightness_nits", "control_system", "quantity", "decision_process",
    ),
}

ALIASES = {
    "rental": "Rental", "event": "Rental", "events": "Rental", "stage": "Rental",
    "xr": "Virtual Production", "virtual production": "Virtual Production",
    "virtualproduction": "Virtual Production", "studio": "Virtual Production",
    "dooh": "DOOH", "outdoor advertising": "DOOH", "billboard": "DOOH",
    "sports": "Sports", "stadium": "Sports", "arena": "Sports",
    "control room": "Control Room", "command center": "Control Room",
    "broadcast": "Broadcast", "tv studio": "Broadcast",
    "retail": "Retail", "mall": "Retail", "store": "Retail",
    "church": "Church", "worship": "Church",
    "fixed": "Fixed Installation", "fixed installation": "Fixed Installation",
    "installation": "Fixed Installation",
}


def normalize_use_case(value: str | None) -> str | None:
    raw = re.sub(r"\s+", " ", (value or "").strip().lower())
    if not raw:
        return None
    if raw in ALIASES:
        return ALIASES[raw]
    for alias, canonical in ALIASES.items():
        if alias in raw:
            return canonical
    for canonical in APPLICATION_FIELDS:
        if canonical.lower() == raw:
            return canonical
    return None


def _present(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (int, float)):
        return value > 0
    return bool(value)


def ordered_fields(opportunity: dict) -> list[str]:
    """Return unique discovery fields ordered for this application."""
    use_case = normalize_use_case(opportunity.get("use_case"))
    fields = list(COMMON)
    fields.extend(APPLICATION_FIELDS.get(use_case, APPLICATION_FIELDS["Fixed Installation"]))
    fields.extend(TAIL)
    # For outdoor work, preserve the four foundation facts first (application,
    # environment, width, height), then bring environment-sensitive risks forward in a
    # deliberate order. Removing them before one slice insertion avoids reversing the
    # intended priority with repeated insert(index, value) calls.
    environment = (opportunity.get("indoor_outdoor") or "").strip().lower()
    if "out" in environment or "户外" in environment:
        priority = ["brightness_nits", "maintenance_access", "installation_type"]
        fields = [field for field in fields if field not in priority]
        fields[len(COMMON):len(COMMON)] = priority
    seen = set()
    return [f for f in fields if not (f in seen or seen.add(f))]


def qualification(opportunity: dict) -> dict:
    fields = ordered_fields(opportunity)
    missing = []
    known = []
    for key in fields:
        label, why = FIELD_META[key]
        value = opportunity.get(key)
        item = {"key": key, "label": label, "why": why, "value": value}
        if _present(value):
            known.append(item)
        else:
            missing.append(item)
    total = len(fields)
    completeness = round((total - len(missing)) * 100 / total) if total else 100
    return {
        "application": normalize_use_case(opportunity.get("use_case")) or "Generic LED Project",
        "completeness": completeness,
        "known": known,
        "missing": missing,
        "next_question": next_question(opportunity, missing=missing),
    }


def next_question(opportunity: dict, *, missing: list[dict] | None = None) -> str | None:
    """Ask only the highest-value missing fact, in a natural sales order."""
    missing = missing if missing is not None else qualification(opportunity)["missing"]
    if not missing:
        return None
    key = missing[0]["key"]
    prompts = {
        "use_case": "这个屏主要会用在什么场景？比如固定安装、租赁活动、XR/拍摄或户外广告？",
        "indoor_outdoor": "这个项目是室内还是户外使用？如果是户外，现场日照情况大概怎样？",
        "width_m": "现场能确认一下屏幕的实际宽度吗？最好给我精确尺寸，而不是只给总面积。",
        "height_m": "屏幕的实际高度是多少？有宽×高后我才能按真实箱体尺寸核配置。",
        "viewing_distance_m": "观众最近大概会在多远的位置看屏？这个信息对点间距判断很关键。",
        "pixel_pitch": "你们已经指定点间距了吗？如果没有，我可以根据尺寸和观看距离来建议。",
        "brightness_nits": "现场对亮度有没有明确要求，或者能告诉我室内/户外以及环境光情况？",
        "refresh_rate_hz": "这个屏会不会被摄像机拍摄或用于 XR/直播？如果会，需要确认刷新率要求。",
        "maintenance_access": "安装后背面有没有检修空间，还是必须从正面维护？",
        "cabinet_size": "箱体尺寸或形式有没有指定，比如 500×500、500×1000，或者需要弧形/快速拼装？",
        "control_system": "信号源和控制方式有什么要求？比如同步播放、备份、4K 输入或需要二次系统联动？",
        "installation_type": "现场准备怎么安装：墙装、吊装、落地还是做弧形/异形结构？",
        "destination": "项目最终安装在哪个城市/国家？我需要据此考虑运输、认证和服务条件。",
        "quantity": "这是单块屏还是多套/多面屏？总数量能确认一下吗？",
        "project_timing": "项目希望什么时候安装或交付？我先按这个时间倒推后面的节点。",
        "budget_range": "如果方便的话，有没有目标预算区间？我可以避免给你不合适的配置方向。",
        "decision_process": "这个项目接下来由谁确认技术方案和采购？预计什么时候做最终决定？",
    }
    return prompts.get(key, f"还需要确认：{FIELD_META[key][0]}。")


def expected_roles(opportunity: dict) -> list[dict]:
    """Return the authority mix normally needed; this never mutates CRM roles."""
    application = normalize_use_case(opportunity.get("use_case"))
    roles = [
        {"kind": "commercial", "label": "Owner / Purchasing / Procurement / Buyer",
         "reason": "需要有人能推进采购、预算或最终商务决定"},
        {"kind": "project", "label": "Project Manager / AV Manager / Technical Director",
         "reason": "需要有人能确认尺寸、安装、控制和技术条件"},
    ]
    if application in ("Virtual Production", "Broadcast", "Control Room"):
        roles[1] = {"kind": "project", "label": "Technical Director / Engineer / AV System Owner",
                    "reason": "该应用对视频链路、刷新、控制和系统集成更敏感"}
    elif application == "Rental":
        roles[1] = {"kind": "project", "label": "Rental Manager / Technical Director / Project Manager",
                    "reason": "租赁项目需要确认库存组合、搭建方式和现场技术要求"}
    return roles
