"""Safe template personalization for outreach messages.

Replaces only the known tokens below; anything else in braces is left intact,
so a stray '{price}' in a template can never crash a send (str.format raised
KeyError). {contact} falls back to 'there' so 'Hi {contact}' always reads fine.

{hook} comes from app.brief and is often empty — plenty of sites publish nothing specific
enough to quote back. It is a whole sentence for exactly that reason: dropping it leaves
the message intact, where a half sentence would go out reading "Saw  on your site."

The brief itself is deliberately not a token. It is written in the third person for Allen
to read ("The site mentions ..."), and a template that sent it would be quoting the
customer's own website back at them.
"""
import re

_TOKEN_RE = re.compile(r"\{(name|company|contact|country|city|hook)\}")
# Closes the gap an empty token leaves behind. Only applied when something did render
# empty, so a template that spaces itself deliberately is left alone.
_GAP_RE = re.compile(r"[^\S\n]{2,}")


def render(text: str | None, lead: dict) -> str:
    if not text:
        return ""
    company = lead.get("company_en") or ""
    contact = (lead.get("contact_name") or "").strip()
    values = {
        "name": company,
        "company": company,
        "contact": contact.split()[0] if contact else "there",
        "country": lead.get("country") or "",
        "city": lead.get("city") or "",
        "hook": (lead.get("hook") or "").strip(),
    }
    dropped = False

    def _sub(m: re.Match) -> str:
        nonlocal dropped
        value = values[m.group(1)]
        dropped = dropped or not value
        return value

    out = _TOKEN_RE.sub(_sub, text)
    return _GAP_RE.sub(" ", out) if dropped else out
