"""Company brief and opening line, built from what the company's own site prints.

Nothing here is inferred and nothing is paraphrased by a model, because the failure mode
that matters is a confident invention ("a leader in the Latin American market") going out
in a cold message: the customer knows it is not true about them, and the whole message
reads as machine-written from that sentence on.

## The two outputs have different readers, and different rules

`brief` is for Allen, sitting in the drawer next to the company name, the ICP grade and
the city. So it never restates those — no "Acme is an event rental company in São Paulo".
An early draft wrote exactly that and, because the name it had came from the title of a
/contact page, produced "Contact is a signage company" and "Página não encontrada is an
event rental company". Restating visible fields costs attention; restating them wrongly
costs more.

`hook` is for the customer, who has never seen our record. The no-restating rule does not
apply to it at all — what is redundant on our screen is news on theirs.

## Language

`app.icp` matches in whatever language the site is written in, so a Korean signage
company matches 전광판 and a Mexican one matches "publicidad exterior". Dropping those
would blank out Korea, which is a primary market. Instead every term carries an English
gloss: the brief quotes the site's own word and glosses it, and the hook uses the gloss
alone, because a message that goes out in English has to read as English.
"""
import re

_PITCH = re.compile(r"\bP\s?(\d{1,2}(?:\.\d)?)\b", re.I)
_PITCH_MIN, _PITCH_MAX = 0.5, 20.0
# A bare "P3" is a heading, a page number or a product code on most of the web. On these
# sites it is written "painel de LED P3" or "pantalla-led-p8-smd", so the token only
# counts when the page put it next to the thing it is a spec of. Verified against live
# customer pages; without this, worshipproductions.org reported a product line it has not
# got anywhere on the site.
_ANCHORS = ("led", "pitch", "pixel")
_ANCHOR_WINDOW = 40
# Four or more reads as a product range rather than a list — P1–P10 is shorter than
# naming the first three of ten, and truer.
_RANGE_FROM = 4
_MAX_TERMS = 3

# Every keyword app.icp can match, in English. The value is the noun the hook uses;
# None means the term is worth quoting to Allen but not worth sending (a self-reference
# like "our church" says nothing to the person receiving the message).
_TERM: dict[str, str | None] = {
    # rental
    "rental": "rental", "staging": "staging", "event production": "event production",
    "stage rental": "stage rental", "av rental": "AV rental", "concert": "concert",
    "festival": "festival", "touring": "touring",
    "alquiler": "rental", "renta de pantallas": "screen rental", "arriendo": "rental",
    "locação": "rental", "locacao": "rental", "eventos": "events",
    "렌탈": "rental", "대여": "rental", "임대": "leasing",
    # integrator
    "av integrat": "AV integration", "system integrat": "systems integration",
    "audiovisual integrat": "audiovisual integration",
    "integration services": "integration", "installation services": "installation",
    "audio visual solutions": "AV solutions", "av solutions": "AV solutions",
    "integrador": "integration",
    "instalación de pantallas": "screen installation",
    "instalacion de pantallas": "screen installation",
    "instalação de painéis": "panel installation",
    # reseller
    "distributor": "distribution", "wholesale": "wholesale", "reseller": "resale",
    "supplier of led": "LED supply", "led screen supplier": "LED screen supply",
    "we supply": None, "dealer": "dealership",
    "distribuidor": "distribution", "mayorista": "wholesale", "atacado": "wholesale",
    "venta de pantallas": "screen sales", "venda de painéis": "panel sales",
    "venda de paineis": "panel sales",
    "대리점": "dealership", "유통": "distribution",
    # signage
    "signage": "signage", "sign company": "signage", "sign shop": "signage",
    "billboard": "billboard", "custom signs": "custom signs",
    "digital sign": "digital signage", "led sign": "LED signage",
    "letreros": "signage", "rotulos": "signage",
    "comunicação visual": "visual communication",
    "publicidad exterior": "outdoor advertising",
    "painel de led": "LED panels", "painéis de led": "LED panels",
    "전광판": "LED signage", "사이니지": "signage",
    # end-user — all self-references, readable here, unsendable
    "our venue": None, "our church": None, "our stadium": None, "our store": None,
    "retail chain": None, "shopping mall": None, "casino": None,
    "house of worship": None,
}


def _pitches(text: str) -> list[str]:
    """Pitch tokens the page prints next to an LED context word, smallest first."""
    low = (text or "").lower()
    found: dict[float, str] = {}
    for m in _PITCH.finditer(text or ""):
        try:
            value = float(m.group(1))
        except ValueError:
            continue
        if not _PITCH_MIN <= value <= _PITCH_MAX or value in found:
            continue
        before = low[max(0, m.start() - _ANCHOR_WINDOW):m.start()]
        if not any(a in before for a in _ANCHORS):
            continue
        found[value] = "P" + m.group(1)
    return [found[v] for v in sorted(found)]


def _terms(hits: list[str]) -> list[tuple[str, str | None]]:
    """Matched keywords as (what the site wrote, English noun). Order is preserved so
    the first one — the strongest signal for its category — is the one the hook uses.

    Deduped by meaning, not by spelling: app.icp carries "locação" and "locacao" so it
    matches Brazilian sites either way, and a page with both spellings was producing
    `mentions "locação" (rental) and "locacao" (rental)`."""
    out, seen, glossed = [], set(), set()
    for h in hits or []:
        key = h.strip().lower()
        if key in seen or key not in _TERM:
            continue
        gloss = _TERM[key]
        if gloss and gloss in glossed:
            continue
        seen.add(key)
        if gloss:
            glossed.add(gloss)
        out.append((h.strip(), gloss))
        if len(out) == _MAX_TERMS:
            break
    return out


def _join(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def _quote(term: str, gloss: str | None) -> str:
    """The site's own word, glossed when it is not already English."""
    if gloss and gloss.lower() != term.lower():
        return f'"{term}" ({gloss})'
    return f'"{term}"'


def _pitch_phrase(pitches: list[str]) -> str:
    return f"{pitches[0]}–{pitches[-1]}" if len(pitches) >= _RANGE_FROM else _join(pitches)


def build(text: str, icp: dict | None = None) -> dict:
    """Return {"brief", "hook"} for a fetched site. Either may be "" on its own terms —
    they answer to different readers and are gated separately."""
    pitches = _pitches(text or "")
    terms = _terms((icp or {}).get("hits", []))

    # The brief's floor: a category on its own is already a visible field, so one
    # published spec or two things the site says about its work is where it starts
    # earning space.
    brief = ""
    if pitches or len(terms) >= 2:
        clauses = []
        if terms:
            clauses.append("mentions " + _join([_quote(t, g) for t, g in terms]))
        if pitches:
            clauses.append(f"lists {_pitch_phrase(pitches)} panels")
        brief = "The site " + ", and ".join(clauses) + "."

    # The hook has no such floor: the customer has not seen our record, so the thing
    # that is redundant on our screen is the thing worth opening with on theirs.
    if pitches:
        hook = f"Saw {_pitch_phrase(pitches)} panels listed on your site."
    else:
        sendable = next((g for _, g in terms if g), None)
        hook = f"Saw the {sendable} work on your site." if sendable else ""
    return {"brief": brief, "hook": hook}
