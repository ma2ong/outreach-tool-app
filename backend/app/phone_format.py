"""What a phone number in the lead book means, and how it becomes dialable (docs/83).

Two rules, and the second is the reason this file exists rather than a helper inside the
sender. R1: a field that labels one number `WA:` is telling us which one WhatsApp is on,
and dialing the other burns the lead permanently — docs/59 writes the failure down as
"this company has no WhatsApp" and the due queue never offers them again. R2: the book
stores what we would actually dial, so what Allen reads is what leaves.

Filling in a calling code is only allowed where it can be shown, never guessed. The
cautionary tale is `fix_invented_country_codes`: `extract_phones` used to prefix every
number it found with '+', turning a Houston switchboard into what reads as Bangladesh.
So a number whose national part is the wrong length for its country, or whose country we
do not know, is reported and left exactly as it was.
"""
from __future__ import annotations

import re

# Country (lowercased, as the book writes it) -> calling code.
CALLING_CODES = {
    "usa": "1", "united states": "1", "us": "1", "canada": "1", "ca": "1",
    "south korea": "82", "korea": "82", "kr": "82",
    "brazil": "55", "br": "55", "mexico": "52", "mx": "52",
    "argentina": "54", "ar": "54", "colombia": "57", "co": "57",
    "chile": "56", "cl": "56", "peru": "51", "pe": "51", "venezuela": "58", "ve": "58",
    "spain": "34", "es": "34", "uk": "44", "united kingdom": "44", "gb": "44",
    "france": "33", "fr": "33", "italy": "39", "it": "39", "germany": "49", "de": "49",
    "austria": "43", "at": "43", "greece": "30", "gr": "30", "poland": "48", "pl": "48",
    "sweden": "46", "se": "46", "finland": "358", "fi": "358",
    "russia": "7", "ru": "7", "turkey": "90", "tr": "90",
    "australia": "61", "au": "61", "new zealand": "64", "nz": "64",
    "india": "91", "in": "91", "indonesia": "62", "id": "62", "malaysia": "60", "my": "60",
}

# US/Canada switchboard ranges. These never have a WhatsApp account, and finding that
# out costs a browser round trip every single day.
TOLL_FREE = ("800", "833", "844", "855", "866", "877", "888")

# How long the national part is, once any trunk '0' is gone. A number outside its
# country's range is data we misread, not a number — it is left alone and reported.
_NATIONAL_LEN = {
    "1": (10, 10), "82": (8, 10), "55": (10, 11), "52": (10, 10),
    "54": (10, 10), "57": (10, 10), "56": (8, 9), "51": (9, 9), "58": (10, 10),
    "34": (9, 9), "44": (9, 10), "33": (9, 9), "39": (9, 11), "49": (9, 11),
    "43": (9, 11), "30": (10, 10), "48": (9, 9), "46": (7, 9), "358": (7, 10),
    "7": (10, 10), "90": (10, 10), "61": (9, 9), "64": (8, 9),
    "91": (10, 10), "62": (9, 12), "60": (9, 10),
}

# Countries that dial long distance through a leading '0'. Korea's 02, Britain's 0161
# and Australia's 04 all drop it once the calling code is in front.
_TRUNK_ZERO = {"82", "44", "33", "39", "49", "43", "30", "48", "46", "358",
               "7", "90", "61", "64", "62", "60", "58"}

# Ranges that do not route from abroad, so a '+' in front of them invents a number that
# cannot be dialed. Korea's 15xx/16xx/18xx, Australia's 13/1300/1800, freephone 0800.
_UNROUTABLE = {
    "82": re.compile(r"^1[3-9]\d{2}"),
    "61": re.compile(r"^1(3|80)"),
    "64": re.compile(r"^800"),
    "54": re.compile(r"^800"),
    # Brazilian area codes run 11-99, so a national part starting with 0 is a 0800 or
    # 0300 service number rather than a real line.
    "55": re.compile(r"^0"),
}


def _parts(field: str) -> list[str]:
    """Split on the separator a human wrote, which is always a spaced slash.

    A bare slash is not a separator: `wa.link/7jz8hw` is one link, and cutting it in
    half turns a working WhatsApp shortlink into two fragments.
    """
    return [p.strip() for p in re.split(r"\s+/\s+", field.strip()) if p.strip()]


def is_toll_free(digits: str) -> bool:
    """North American switchboard ranges, with or without the leading 1."""
    national = digits[1:] if len(digits) == 11 and digits.startswith("1") else digits
    return len(national) == 10 and national[:3] in TOLL_FREE


def split_numbers(field: str | None) -> tuple[str, str]:
    """(voice, whatsapp) as written. The `WA:` label decides, not the order (R1).

    Returns the same string twice when the field holds one number, and an empty
    WhatsApp half when the label points at something undialable like a wa.link.
    """
    raw = str(field or "").strip()
    if not raw:
        return "", ""
    parts = _parts(raw)
    labelled = ""
    plain = []
    for part in parts:
        m = re.match(r"^WA\s*:\s*(.+)$", part, re.I)
        if m:
            # "WA: wa.link/7jz8hw" names a link, not a number. Seven digits is the
            # shortest thing anyone could dial, so anything below that is not a number
            # we can prefer over the voice line.
            candidate = m.group(1).strip()
            labelled = candidate if len(re.sub(r"\D", "", candidate)) >= 7 else ""
        elif not labelled or re.search(r"\d", part):
            plain.append(part)
    voice = plain[0] if plain else labelled
    return voice, (labelled or voice)


def international(number: str | None, country: str | None) -> str | None:
    """Digits of the full international number, or None when we cannot show one.

    None is a real answer: no country, a national part of the wrong length, or a range
    that does not route from abroad. Those are reported for a person to look at, never
    rewritten (docs/45).
    """
    raw = str(number or "").strip()
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None
    if raw.startswith("+"):
        return digits if 8 <= len(digits) <= 15 else None
    # '00' is the international prefix — the number after it is already international.
    if digits.startswith("00") and len(digits) > 9:
        digits = digits[2:]
        return digits if 8 <= len(digits) <= 15 else None

    code = CALLING_CODES.get(str(country or "").strip().lower())
    if not code:
        return None
    national = digits
    if national.startswith(code) and len(national) > _NATIONAL_LEN.get(code, (0, 99))[1]:
        national = national[len(code):]
    if code in _TRUNK_ZERO:
        national = national.lstrip("0") or national
    unroutable = _UNROUTABLE.get(code)
    if unroutable and unroutable.match(national):
        return None
    low, high = _NATIONAL_LEN.get(code, (7, 14))
    if not low <= len(national) <= high:
        return None
    return code + national


def _pretty(digits: str) -> str:
    return "+" + digits


def book_form(field: str | None, country: str | None) -> str | None:
    """The field rewritten in international form, or None when nothing changes.

    Every slash-separated part is converted on its own and the parts are put back in the
    order they were written, `WA:` labels included — that label is the only record of
    which number WhatsApp is on. A part we cannot show internationally is kept exactly as
    the human wrote it: a second mobile that our length table does not recognise is still
    a number Allen has, and dropping it to make the row tidy would lose it.
    """
    raw = str(field or "").strip()
    if not raw:
        return None
    out, seen = [], set()
    for part in _parts(raw):
        m = re.match(r"^(WA\s*:\s*)(.+)$", part, re.I)
        label, number = (m.group(1), m.group(2).strip()) if m else ("", part)
        digits = international(number, country)
        if digits is None:
            out.append(part)
            continue
        if digits in seen:
            continue
        seen.add(digits)
        out.append(f"{'WA: ' if label else ''}{_pretty(digits)}")
    result = " / ".join(out)
    return result if result != raw else None
