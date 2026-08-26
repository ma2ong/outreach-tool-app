"""The customer types Allen files companies under (docs/60).

The list is his, not ours: these are the tags he has been using in Xiaoman for years,
with the counts he built up. Inventing a tidier taxonomy would mean asking him to
re-learn his own vocabulary.

`tags` also carries machine output — `icp:signage` comes from the classifier, not from
him — so the two have to be told apart before either is shown as a customer type.
"""
from __future__ import annotations

# Ordered by how much of his book each one covers.
KNOWN = ("工程商", "租赁客户", "批发商", "广告商", "透明屏")

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
