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
    "south africa": "27", "za": "27",
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
    "91": (10, 10), "62": (9, 12), "60": (9, 10), "27": (9, 9),
}

# Countries that dial long distance through a leading '0'. Korea's 02, Britain's 0161
# and Australia's 04 all drop it once the calling code is in front.
_TRUNK_ZERO = {"82", "44", "33", "39", "49", "43", "30", "48", "46", "358",
               "7", "90", "61", "64", "62", "60", "58", "27"}

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


# Fixed-line ranges, by calling code, matched against the national part. Only a positive
# match here excludes a number from WhatsApp (docs/108 R2): the question this table
# answers is "can we show this is a landline", never "does it look like a mobile".
# A country that is not here keeps its WhatsApp channel, and North America can never be
# here — NANP does not split by use, so `404-835-2230` carries no answer to read.
_FIXED_LINE = {
    "82": re.compile(r"^[2-6]"),       # 02 Seoul, 031-064; mobile is 010/011/016-019
    "55": re.compile(r"^\d{2}[2-5]"),  # area + 8 digits; a mobile is area + 9 + 8
    "56": re.compile(r"^[2-8]"),       # mobile is 9
    "57": re.compile(r"^[124-8]"),     # 60x and the old area codes; mobile is 3
    "51": re.compile(r"^[1-8]"),       # mobile is 9
    "27": re.compile(r"^[1-5]"),       # mobile is 6/7/8
    "34": re.compile(r"^[89]"),        # mobile is 6/7
    "44": re.compile(r"^[12]"),        # mobile is 7
    "61": re.compile(r"^[2378]"),      # mobile is 4
    "7": re.compile(r"^[3-8]"),        # mobile is 9
    "64": re.compile(r"^[34679]"),     # mobile is 2
    "358": re.compile(r"^[1239]"),     # mobile is 4/5
}

# Longest first, so 358 is read as Finland rather than 3 + something.
_CODES_LONGEST_FIRST = sorted(set(CALLING_CODES.values()), key=len, reverse=True)


def is_fixed_line(digits: str) -> bool:
    """True only when this number's own country says the range is a landline.

    False is the answer for everything we cannot show, unknown countries included.
    Excluding a mobile by mistake costs a company its channel, which is exactly the harm
    docs/62 exists to prevent; dialling a landline costs one dialog.
    """
    code = next((c for c in _CODES_LONGEST_FIRST if digits.startswith(c)), None)
    pattern = _FIXED_LINE.get(code or "")
    if pattern is None:
        return False
    national = digits[len(code):]
    if code in _TRUNK_ZERO:
        national = national.lstrip("0") or national
    return bool(pattern.match(national))


def parts(field: str) -> list[str]:
    """Split on the separator a human wrote, which is always a spaced slash.

    A bare slash is not a separator: `wa.link/7jz8hw` is one link, and cutting it in
    half turns a working WhatsApp shortlink into two fragments.
    """
    return [p.strip() for p in re.split(r"\s+/\s+", field.strip()) if p.strip()]


_LABEL_RE = re.compile(r"^WA\s*:\s*", re.I)


def without_label(part: str) -> str:
    """The number inside a part, with any `WA:` label taken off the front."""
    return _LABEL_RE.sub("", part.strip())


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
    labelled = ""
    plain = []
    for part in parts(raw):
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
    for part in parts(raw):
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
