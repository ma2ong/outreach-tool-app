"""The last check a cold email passes before it leaves.

The guard judges the rendered text, not the stored template. It never rewrites copy to
make it pass: a hold is visible and the caller decides what to change.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

GUARDED_CHANNELS = ("email",)

# Narrow on purpose. Technical outreach is full of legitimate numbers (P2.5, 200 sqm,
# years and phone numbers). Currency beside a number is an actual commercial number and
# belongs to Allen, not a cold-email automation.
_PRICE = re.compile(
    r"(?:[$€£¥₩]\s?\d[\d,.]*)"
    r"|(?:\b(?:usd|eur|gbp|rmb|cny|jpy|krw|brl|mxn|clp|cop|pen)\s?\d[\d,.]*)"
    r"|(?:\b\d[\d,.]*\s?(?:usd|eur|gbp|rmb|cny|jpy|krw|brl|mxn|clp|cop|pen)\b)"
    r"|(?:\d[\d,.]*\s?(?:元|美金|美元|块))",
    re.I,
)

_WORD = re.compile(r"[a-z0-9]+")
_GENERIC_NAME_WORDS = {
    "led", "display", "displays", "screen", "screens", "visual", "video", "wall",
    "walls", "av", "audio", "media", "systems", "system", "group", "inc", "llc",
    "ltd", "co", "company", "solutions", "productions", "rentals", "rental", "the",
    "and",
}


@dataclass(frozen=True)
class Verdict:
    blocked: bool
    reason: str = ""
    detail: str = ""


def _distinctive_terms(lead: dict) -> list[str]:
    """Words that plausibly tie the rendered opening to this particular lead."""
    terms: list[str] = []
    terms.extend(
        word
        for word in _WORD.findall(str(lead.get("company_en") or "").lower())
        if word not in _GENERIC_NAME_WORDS
    )
    host = str(lead.get("website") or "").lower()
    host = re.sub(r"^https?://|^www\.", "", host).split("/")[0].split(".")[0]
    if len(host) > 2 and host not in _GENERIC_NAME_WORDS:
        terms.append(host)
    for field in ("city", "hook"):
        value = str(lead.get(field) or "").strip()
        if not value:
            continue
        terms.extend(
            word for word in _WORD.findall(value.lower())
            if len(word) > 3 and word not in _GENERIC_NAME_WORDS
        )
    # Preserve order for useful error messages while deduping.
    return list(dict.fromkeys(terms))


def can_be_addressed(lead: dict) -> bool:
    """Whether a first cold letter to this lead could pass `check` at all.

    Callers that build a queue use this to leave out records the guard would refuse
    anyway. Enrolling them regardless does not send more mail — it parks them in
    `quality_hold` and quietly shortens the day, which is the failure seed_angle2 found
    110 follow-ups sitting in.
    """
    name = str(lead.get("company_en") or "").strip()
    # A row whose company name is somebody's mailbox cannot be written to by name.
    if not name or "@" in name:
        return False
    return bool(_distinctive_terms(lead))


def check(body: str, lead: dict, *, subject: str = "", channel: str = "email",
          step_order: int = 0) -> Verdict:
    """Judge exactly the subject/body that would be handed to the sender."""
    text = f"{subject}\n{body}"
    price = _PRICE.search(text)
    if price:
        return Verdict(
            True,
            "pricing",
            f"最终文本里出现价格「{price.group(0).strip()}」——冷邮件自动化不能代替 Allen 定价",
        )
    if channel not in GUARDED_CHANNELS or step_order > 0:
        return Verdict(False)

    written = set(_WORD.findall(text.lower()))
    terms = _distinctive_terms(lead)
    if written.intersection(terms):
        return Verdict(False)

    company = lead.get("company_en") or f"#{lead.get('no')}"
    if terms:
        return Verdict(
            True,
            "impersonal",
            f"首封最终文本没有可识别的 {company} 个性化信息（可用线索：{terms[0]}）",
        )
    return Verdict(
        True,
        "impersonal",
        f"{company} 没有可验证的个性化线索；先补公司/官网 hook/城市信息再发",
    )
