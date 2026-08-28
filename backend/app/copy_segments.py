"""Which kind of customer a company is, so the letter can be written to them (docs/76).

This reads fields the book already has — Allen's own tags, `target_fit`, the business
line — and never invents a new classifier. Change a customer's type in the lead book and
the next letter changes with it, which is the point: the segment is his judgement, stored
where he already keeps it.

`general` is not a leftover bin. It is the largest segment (789 companies), and it exists
because guessing wrongly is worse than writing neutrally: a letter that opens by telling
a signage company how their rental business works has already lost. docs/45 applies to
copy as much as to CRM fields — not knowing what they do means not pretending to.
"""
from __future__ import annotations

import re

from app import customer_types as ct

SEGMENTS = ("rental", "install", "outdoor", "indoor", "reseller", "general")

LABEL = {
    "rental": "活动租赁", "install": "固定安装", "outdoor": "户外为主",
    "indoor": "室内为主", "reseller": "代理批发", "general": "类型未知",
}

# Allen's tags come first: they are the only signal he set by hand.
FROM_TYPE = {
    "租赁商": "rental",
    "工程商": "install", "系统集成商": "install",
    "广告商": "outdoor",
    "透明屏": "indoor",
    "代理商": "reseller", "批发商": "reseller",
    # 终端用户 buys for itself, which says nothing about indoor vs outdoor — it falls
    # through to the business text rather than being forced into a segment.
}

# `target_fit` is the classifier's, and only consulted when Allen set no type.
FROM_FIT = (
    ("租赁", "rental"),
    ("集成", "install"), ("AV", "install"),
    ("标识", "outdoor"), ("广告牌", "outdoor"),
    ("经销", "reseller"),
)

_OUTDOOR_WORDS = re.compile(
    r"billboard|out-?of-?home|\bDOOH\b|facade|fa[çc]ade|stadium|highway|roadside"
    r"|户外|广告牌|楼体|led 옥외|옥외", re.I)
_INDOOR_WORDS = re.compile(
    r"retail store|showroom|broadcast studio|tv studio|control room|boardroom"
    r"|conference room|室内|演播|控制室|会议室|실내", re.I)
_RENTAL_WORDS = re.compile(
    r"\brental\b|\bstaging\b|concert|festival|touring|live event|舞台|演唱会|租赁"
    r"|렌탈|무대", re.I)
_INSTALL_WORDS = re.compile(
    r"\bintegrat|\binstallation\b|\bfixed install|systems? integrator|시공|설치", re.I)


def segment_of(lead: dict) -> str:
    """One of SEGMENTS. Allen's tag wins; then the classifier's fit; then the words the
    company uses about itself; then `general`."""
    for tag in ct.customer_types(lead.get("tags")):
        if tag in FROM_TYPE:
            return FROM_TYPE[tag]

    fit = str(lead.get("target_fit") or "")
    for needle, segment in FROM_FIT:
        if needle in fit:
            return segment

    # Their own description, last: it is the least reliable and the easiest to misread.
    text = " ".join(str(lead.get(f) or "") for f in ("business", "hook", "brief"))
    if _RENTAL_WORDS.search(text):
        return "rental"
    if _INSTALL_WORDS.search(text):
        return "install"
    if _OUTDOOR_WORDS.search(text):
        return "outdoor"
    if _INDOOR_WORDS.search(text):
        return "indoor"
    return "general"


def counts(conn) -> dict[str, int]:
    """How the book divides up — used by the seeder's preview and the daily report."""
    out = {s: 0 for s in SEGMENTS}
    for row in conn.execute(
            "SELECT tags, target_fit, business, hook, brief FROM leads"):
        out[segment_of(dict(row))] += 1
    return out
