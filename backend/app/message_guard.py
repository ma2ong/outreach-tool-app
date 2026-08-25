"""The last check a message passes before it leaves.

Two rules that used to live only in prompts and in the hope that whoever wrote the
template remembered them. Both are checked on the *rendered* text — after `{hook}` and
`{company}` have been substituted — because that is the only string that actually
reaches a customer, and it is not the string anybody reviewed.

1. Pricing. `AGENTS.md` rule one is that Allen owns every number: the Agent may
   summarise a quote request and open a task, never answer it. A hand-written template
   and a model draft can both carry a price, and neither is read again before send.

2. Personalisation, on the opening touch only. 544 cold emails went out and came back
   with zero human replies. The first template names no one and says nothing about the
   company it is addressed to, while 69% of those leads carry a hook read off their own
   website that no template ever used. A mail that could have been sent to anyone is
   not outreach, it is postage — and it spends sender reputation to say nothing.

A block is a stop, not a filter: the caller reports it and the message stays unsent.
Nothing here rewrites a message to make it pass, because a message quietly edited on its
way out is one nobody has actually reviewed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Cold openings are the only thing this guards. A reply inside a live conversation, or a
# social DM that a human already approved, has its own review path.
GUARDED_CHANNELS = ("email",)

# A currency next to a number, either order, plus the Chinese way of writing it. Kept
# deliberately narrow: "P2.5", "200 sqm" and "+86 135..." are the numbers an ordinary
# cold email is full of, and blocking those would make the guard something people
# switch off.
_PRICE = re.compile(
    r"(?:[$€£¥₩]\s?\d[\d,.]*)"
    r"|(?:\b(?:usd|eur|gbp|rmb|cny|jpy|krw|brl|mxn|clp|cop|pen)\s?\d[\d,.]*)"
    r"|(?:\b\d[\d,.]*\s?(?:usd|eur|gbp|rmb|cny|jpy|krw|brl|mxn|clp|cop|pen)\b)"
    r"|(?:\d[\d,.]*\s?(?:元|美金|美元|块))",
    re.I)

_WORD = re.compile(r"[a-z0-9]+")
# Words that name no company in particular. A "display" or "led" in the body says
# nothing about who it was written for.
_GENERIC_NAME_WORDS = {"led", "display", "displays", "screen", "screens", "visual",
                       "video", "wall", "walls", "av", "audio", "media", "systems",
                       "system", "group", "inc", "llc", "ltd", "co", "company",
                       "solutions", "productions", "rentals", "rental", "the", "and"}


@dataclass(frozen=True)
class Verdict:
    blocked: bool
    reason: str = ""
    detail: str = ""


def _distinctive_terms(lead: dict) -> list[str]:
    """The words that would only appear in a mail written for this company.

    A company's own name has no length floor — "3M" and "LG" are the whole name — while
    a hook or a city contributes only its longer content words, so that "the" and "on"
    do not turn every message into a personalised one.
    """
    terms: list[str] = []
    terms.extend(word for word in _WORD.findall(str(lead.get("company_en") or "").lower())
                 if word not in _GENERIC_NAME_WORDS)
    host = str(lead.get("website") or "").lower()
    host = re.sub(r"^https?://|^www\.", "", host).split("/")[0].split(".")[0]
    if len(host) > 2 and host not in _GENERIC_NAME_WORDS:
        terms.append(host)
    for field in ("city", "hook"):
        value = str(lead.get(field) or "").strip()
        if not value:
            continue
        # A hook is a sentence; match on its content words so a lightly reworded
        # rendering still counts as having used it.
        terms.extend(word for word in _WORD.findall(value.lower())
                     if len(word) > 3 and word not in _GENERIC_NAME_WORDS)
    return terms


def check(body: str, lead: dict, *, subject: str = "", channel: str = "email",
          step_order: int = 0) -> Verdict:
    """Judge the rendered text of one outgoing message."""
    text = f"{subject}\n{body}"
    price = _PRICE.search(text)
    if price:
        return Verdict(True, "pricing",
                       f"正文里出现价格「{price.group(0).strip()}」——报价只能由 Allen 发出")
    if channel not in GUARDED_CHANNELS or step_order > 0:
        return Verdict(False)
    # Whole words, never substrings: a one-letter company name would otherwise match the
    # letter "a" anywhere in the text, the same way "Indiana" once read as India.
    written = set(_WORD.findall(text.lower()))
    terms = _distinctive_terms(lead)
    if written.intersection(terms):
        return Verdict(False)
    company = lead.get("company_en") or f"#{lead.get('no')}"
    if terms:
        return Verdict(True, "impersonal",
                       f"这封信里没有一句是关于 {company} 的（可用线索：{terms[0]}）")
    return Verdict(True, "impersonal",
                   f"{company} 没有可用的个性化线索，先补 hook 或城市再发")
