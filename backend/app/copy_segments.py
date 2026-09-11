"""Choose one outbound-copy segment from the evidence already stored on a lead.

There are intentionally only three segments:

- rental: clear evidence the company mainly does rental/event work.
- install: clear evidence the company mainly does fixed-install/integration work.
- general: mixed business, another buyer type, outdoor/signage only, or insufficient proof.

The rule is conservative on purpose. A wrong specialised opener is worse than a neutral
one, so Rental/Install require a clear one-sided signal. Outdoor remains a product/use
case, not a customer segment.
"""
from __future__ import annotations

import re

from app import customer_types as ct

SEGMENTS = ("rental", "install", "general")

LABEL = {
    "rental": "Rental",
    "install": "Install",
    "general": "General",
}

FROM_TYPE = {
    "Rental": "rental",
    "Install": "install",
    "General": "general",
}

# The richer ICP taxonomy is still useful for fit scoring, but outbound routing only uses
# clear rental/integrator verdicts. Signage, reseller, end-user and unknown are General.
FROM_FIT = (
    ("租赁", "rental"),
    ("Rental", "rental"),
    ("集成", "install"),
    ("AV", "install"),
    ("Install", "install"),
)

_RENTAL_WORDS = re.compile(
    r"\brental\b|\bstaging\b|concert|festival|touring|live event|event production|"
    r"舞台|演唱会|租赁|렌탈|대여|임대", re.I)
_INSTALL_WORDS = re.compile(
    r"\bintegrat|\binstallation\b|\bfixed install|systems? integrator|av solutions?|"
    r"시공|설치|통합제어|통합배선", re.I)


def _manual_segment(types: list[str]) -> str | None:
    """Human tags win, but mixed Rental + Install is General by definition."""
    values = {FROM_TYPE[t] for t in types if t in FROM_TYPE}
    if "general" in values or {"rental", "install"} <= values:
        return "general"
    if "rental" in values:
        return "rental"
    if "install" in values:
        return "install"
    return None


def segment_of(lead: dict) -> str:
    """Return rental/install only on clear evidence; otherwise return general."""
    manual = _manual_segment(ct.customer_types(lead.get("tags")))
    if manual:
        return manual

    fit = str(lead.get("target_fit") or "")
    fit_hits = {segment for needle, segment in FROM_FIT if needle.lower() in fit.lower()}
    if {"rental", "install"} <= fit_hits:
        return "general"
    if len(fit_hits) == 1:
        return next(iter(fit_hits))

    # Business text is the weakest signal. Only use a specialised variant when one side
    # clearly appears without the other. If both appear, the company gets General.
    text = " ".join(str(lead.get(f) or "") for f in ("business", "hook", "brief"))
    rental = bool(_RENTAL_WORDS.search(text))
    install = bool(_INSTALL_WORDS.search(text))
    if rental and not install:
        return "rental"
    if install and not rental:
        return "install"
    return "general"


def counts(conn) -> dict[str, int]:
    """How the book divides up — used by the seeder preview and daily report."""
    out = {s: 0 for s in SEGMENTS}
    for row in conn.execute(
            "SELECT tags, target_fit, business, hook, brief FROM leads"):
        out[segment_of(dict(row))] += 1
    return out
