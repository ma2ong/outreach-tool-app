"""Choose the outbound-copy family for one company (docs/127).

Specialist copy is useful only when the evidence is one-sided. Rental and Install are
therefore positive classifications, while General is the deliberate answer for mixed,
uncertain, reseller, outdoor-only, or otherwise unresolved companies.

Evidence precedence stays conservative: Allen's explicit customer-type tags first,
then `target_fit`, then words from the company's own business/hook/brief fields. At one
evidence level we collect the whole answer before deciding; seeing "rental" first in a
string must not hide "installation" later in the same string.
"""
from __future__ import annotations

import re

from app import customer_types as ct

SEGMENTS = ("rental", "install", "general")

LABEL = {
    "rental": "活动租赁",
    "install": "固定安装",
    "general": "中性版",
}

FROM_TYPE = {
    "租赁商": "rental",
    "工程商": "install",
    "批发商": "general",
}

_RENTAL_FIT_WORDS = re.compile(r"租赁|rental|staging|event production|렌탈|무대", re.I)
_INSTALL_FIT_WORDS = re.compile(
    r"集成|\bAV\b|安装|工程|integrat|install|시공|설치", re.I)

_RENTAL_WORDS = re.compile(
    r"\brental\b|\bstaging\b|concert|festival|touring|live event|event production"
    r"|舞台|演唱会|租赁|렌탈|무대", re.I)
_INSTALL_WORDS = re.compile(
    r"\bintegrat|\binstall(?:ation|er|ing|s|ed)?\b|\bfixed[- ]?install"
    r"|\bpermanent\s+(?:led|display|av|installation)\b|systems? integrator"
    r"|系统集成|固定安装|工程安装|시공|설치", re.I)


def _specialist(rental: bool, install: bool) -> str | None:
    """Return a specialist only when exactly one side is supported."""
    if rental == install:  # both true or both false
        return None
    return "rental" if rental else "install"


def _from_manual_tags(raw_tags) -> str | None:
    """Manual customer types are the strongest evidence.

    A General/reseller type is an explicit reason not to pretend we know a specialist
    workflow. Likewise, tags that name both Rental and Install are mixed by definition.
    """
    found: set[str] = set()
    for tag in ct.customer_types(raw_tags):
        segment = FROM_TYPE.get(ct.canonical_type(tag) or "")
        if segment:
            found.add(segment)
    if not found:
        return None
    if "general" in found or len(found) != 1:
        return "general"
    return next(iter(found))


def _from_text(text: str, rental_re: re.Pattern, install_re: re.Pattern) -> str | None:
    return _specialist(bool(rental_re.search(text)), bool(install_re.search(text)))


def segment_of(lead: dict) -> str:
    """Return exactly one of Rental / Install / General (docs/127 R1).

    Outdoor/signage/billboard evidence is intentionally absent here. It can describe a
    project, but it does not say whether the customer rents systems, installs them, does
    both, or simply operates one.
    """
    manual = _from_manual_tags(lead.get("tags"))
    if manual:
        return manual

    fit = str(lead.get("target_fit") or "")
    from_fit = _from_text(fit, _RENTAL_FIT_WORDS, _INSTALL_FIT_WORDS)
    if from_fit:
        return from_fit
    # Both Rental and Install at this level is knowingly mixed, not "no evidence". Do
    # not fall through to weaker website text and let it break the tie by accident.
    if _RENTAL_FIT_WORDS.search(fit) and _INSTALL_FIT_WORDS.search(fit):
        return "general"

    text = " ".join(str(lead.get(f) or "") for f in ("business", "hook", "brief"))
    from_company = _from_text(text, _RENTAL_WORDS, _INSTALL_WORDS)
    if from_company:
        return from_company
    return "general"


def counts(conn) -> dict[str, int]:
    """How the book divides up — used by the seeder preview and daily report."""
    out = {s: 0 for s in SEGMENTS}
    for row in conn.execute(
            "SELECT tags, target_fit, business, hook, brief FROM leads"):
        out[segment_of(dict(row))] += 1
    return out
