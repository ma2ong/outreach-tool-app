"""The customer types Allen files companies under (docs/60).

The list is his, not ours: these are the tags he has been using in Xiaoman for years,
with the counts he built up. Inventing a tidier taxonomy would mean asking him to
re-learn his own vocabulary.

`tags` also carries machine output — `icp:signage` comes from the classifier, not from
him — so the two have to be told apart before either is shown as a customer type.
"""
from __future__ import annotations

# Ordered by how much of his book each one covers. 租赁客户 and 租赁商 named the same
# thing, so the picker offers one of them — Allen picked 租赁商 — and the records
# carrying the other were renamed rather than losing their tag.
KNOWN = ("工程商", "租赁商", "批发商", "广告商", "透明屏",
         "系统集成商", "代理商", "终端用户")

# The classifier writes its own tags into the same column; they are working notes.
MACHINE_PREFIXES = ("icp:", "auto:", "sys:")


# The Xiaoman import joined a company's tags with 、 while the tag box uses commas, so a
# reader that knows only one of them turns "工程商、租赁客户" into a single made-up type.
_SEPARATORS = ("，", "、", ";", "；")


def split_tags(raw: str | None) -> list[str]:
    text = str(raw or "")
    for sep in _SEPARATORS:
        text = text.replace(sep, ",")
    return [t.strip() for t in text.split(",") if t.strip()]


def customer_types(raw: str | None) -> list[str]:
    """Only the tags that name a kind of customer — never the classifier's notes."""
    return [t for t in split_tags(raw)
            if not t.lower().startswith(MACHINE_PREFIXES)]


# The classifier has its own vocabulary; Allen has his. Translate once, then only ever
# speak his (docs/64 R1). `unknown` is deliberately absent: a type we cannot tell is a
# blank, not a category, and giving it a name only adds a useless filter option.
FROM_ICP = {
    "rental": "租赁商",
    "integrator": "系统集成商",
    "signage": "广告商",
    "reseller": "代理商",
    "end-user": "终端用户",
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
    """The customer type to add, or None to leave the field as it is (docs/64 R2).

    Nothing is derived when he already chose a type, and nothing once he has edited the
    field: a type he deleted is a judgement, and re-deriving it would quietly overrule
    him every time the site is read again.
    """
    if edited_at or customer_types(raw):
        return None
    return from_icp(icp_type_of(raw))


def options(conn) -> list[str]:
    """The picker's choices: the known list, plus anything he has added himself.

    Locking the list to KNOWN would push a type he needs into some other field, which is
    worse than an untidy list.
    """
    seen = list(KNOWN)
    for row in conn.execute("SELECT DISTINCT tags FROM leads WHERE COALESCE(tags,'') <> ''"):
        for tag in customer_types(row[0]):
            if tag not in seen:
                seen.append(tag)
    return seen
