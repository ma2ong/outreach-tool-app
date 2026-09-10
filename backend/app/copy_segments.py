"""Route outbound copy to Rental, Install, or General only.

This is a copy decision, not the CRM customer taxonomy.  Outdoor/indoor describes the
project environment; it does not tell us whether the company mainly rents LED equipment
or delivers fixed-install projects.  Copy therefore stays conservative: only clear
Rental or Install evidence earns a specialised message.  Mixed or uncertain evidence is
General.

Evidence order is intentional: a human-set customer-type tag is strongest, then
``target_fit``, then the company's own business description.  At every layer, evidence
for both Rental and Install resolves to General instead of whichever word happened to be
seen first.
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

# Only tags that actually describe the commercial relationship belong here.  In
# particular, 广告商 / 户外 / outdoor are deliberately absent: an outdoor project can be
# sold by a rental company, an installer, or a company that does both.
_FROM_TAG = {
    "租赁商": "rental",
    "租赁客户": "rental",
    "rental": "rental",
    "rental company": "rental",
    "工程商": "install",
    "系统集成商": "install",
    "install": "install",
    "installer": "install",
    "integrator": "install",
    "批发商": "general",
    "代理商": "general",
    "general": "general",
    "wholesale": "general",
    "reseller": "general",
}

_RENTAL_WORDS = re.compile(
    r"\brental\b|\brental company\b|\bhire company\b|\bequipment hire\b|"
    r"\bstage rental\b|租赁(?:公司|商|客户)?|렌탈",
    re.I,
)
_INSTALL_WORDS = re.compile(
    r"\bsystems? integrator\b|\bav integrator\b|\bintegration company\b|"
    r"\binstaller\b|\binstallation contractor\b|\bfixed[- ]installation\b|"
    r"\bcommercial av integration\b|系统集成(?:商)?|工程商|安装商|固定安装|"
    r"고정 설치|시스템 통합|시공 전문|설치 전문",
    re.I,
)


def _segment_from_text(text: str | None) -> str | None:
    """Return a clear specialised segment, General for mixed evidence, or None for none."""
    value = str(text or "").strip()
    if not value:
        return None
    hits = set()
    if _RENTAL_WORDS.search(value):
        hits.add("rental")
    if _INSTALL_WORDS.search(value):
        hits.add("install")
    if len(hits) == 1:
        return hits.pop()
    if len(hits) > 1:
        return "general"
    return None


def _segment_from_tags(raw: str | None) -> str | None:
    """Interpret only explicit customer-type tags; machine and environment tags do not vote."""
    hits = set()
    for tag in ct.split_tags(raw):
        lowered = tag.strip().lower()
        if lowered.startswith(ct.MACHINE_PREFIXES):
            continue
        segment = _FROM_TAG.get(lowered)
        if segment:
            hits.add(segment)
    if hits == {"rental"}:
        return "rental"
    if hits == {"install"}:
        return "install"
    if hits:
        return "general"
    return None


def segment_of(lead: dict) -> str:
    """One of ``SEGMENTS`` using conservative, evidence-first routing.

    Clear Rental -> Rental.  Clear Install -> Install.  Both or uncertain -> General.
    Outdoor-only evidence never creates a specialised copy segment.
    """
    tagged = _segment_from_tags(lead.get("tags"))
    if tagged:
        return tagged

    fit = _segment_from_text(lead.get("target_fit"))
    if fit:
        return fit

    # Their own description is the weakest source and is consulted last.  Do not use
    # application words such as concert, church, billboard, stadium or outdoor here:
    # those describe where a screen is used, not how this company makes money.
    text = " ".join(str(lead.get(f) or "") for f in ("business", "hook", "brief"))
    return _segment_from_text(text) or "general"


def counts(conn) -> dict[str, int]:
    """How the lead book divides across the three outbound-copy segments."""
    out = {s: 0 for s in SEGMENTS}
    for row in conn.execute(
            "SELECT tags, target_fit, business, hook, brief FROM leads"):
        out[segment_of(dict(row))] += 1
    return out
