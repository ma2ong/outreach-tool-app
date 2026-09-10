"""Customer type vocabulary used by routing and outbound copy.

There are intentionally only three values:

- Rental: we clearly know the company mainly does rental/event work.
- Install: we clearly know the company mainly does fixed-install/integration work.
- General: the company does both, belongs to another buyer type, or we cannot tell.

Legacy Xiaoman tags and classifier tags are translated at this boundary so old records
keep working without leaking old categories back into the UI.
"""
from __future__ import annotations

KNOWN = ("Rental", "Install", "General")

# Old/manual vocabulary is compatibility data, not additional customer types.
# Outdoor/signage/reseller/end-user are deliberately General: they do not prove that the
# customer's main business is rental or installation.
_ALIASES = {
    "rental": "Rental",
    "租赁商": "Rental",
    "租赁客户": "Rental",
    "install": "Install",
    "工程商": "Install",
    "系统集成商": "Install",
    "general": "General",
    "批发商": "General",
    "代理商": "General",
    "广告商": "General",
    "outdoor": "General",
    "户外": "General",
    "户外为主": "General",
}

_DROPPED = {"透明屏", "终端用户"}
MACHINE_PREFIXES = ("icp:", "auto:", "sys:")
_SEPARATORS = ("，", "、", ";", "；")


def split_tags(raw: str | None) -> list[str]:
    text = str(raw or "")
    for sep in _SEPARATORS:
        text = text.replace(sep, ",")
    return [t.strip() for t in text.split(",") if t.strip()]


def canonical_type(tag: str) -> str | None:
    """Return one of KNOWN for a recognised customer-type tag."""
    value = str(tag or "").strip()
    if not value or value in _DROPPED:
        return None
    return _ALIASES.get(value) or _ALIASES.get(value.lower())


def customer_types(raw: str | None) -> list[str]:
    """Return only the three routing types, canonicalised and de-duplicated."""
    out: list[str] = []
    for tag in split_tags(raw):
        if tag.lower().startswith(MACHINE_PREFIXES):
            continue
        canonical = canonical_type(tag)
        if canonical and canonical not in out:
            out.append(canonical)
    return out


# The ICP classifier may stay richer internally; outbound only sees the three commercial
# routing types. Anything other than a clear rental/integrator signal is General.
FROM_ICP = {
    "rental": "Rental",
    "integrator": "Install",
    "general": "General",
    "signage": "General",
    "reseller": "General",
    "end-user": "General",
    "unknown": "General",
}


def from_icp(icp_type: str | None) -> str | None:
    return FROM_ICP.get(str(icp_type or "").strip().lower())


def icp_type_of(raw: str | None) -> str | None:
    """The classifier's own verdict carried in the tags column, if any."""
    for tag in split_tags(raw):
        if tag.lower().startswith("icp:"):
            return tag[4:].lower()
    return None


def derive(raw: str | None, edited_at: str | None = None) -> str | None:
    """Customer type to add from ICP, without overwriting a human edit."""
    if edited_at or customer_types(raw):
        return None
    return from_icp(icp_type_of(raw))


def options(conn) -> list[str]:
    """The picker is intentionally closed: Rental / Install / General only."""
    return list(KNOWN)
