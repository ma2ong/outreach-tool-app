"""One spelling per country, applied at the moment a lead is written.

The book had 130 leads in "Korea", 14 in "South Korea" and 1 in "韩国" — three bars on
the dashboard for one market, and three different filter results for the same question.
Nothing was wrong with any of the writers; they simply never agreed, because the
collector, the discovery import and the quick-add box each set the field themselves.

So the agreement lives here, at the single point every one of them passes through
(`repository.insert_lead` / `update_lead`) rather than in each of their heads.

The canonical spellings deliberately match whatever the book already uses most — "USA",
not "United States" — so adding this rule needed no migration of the existing rows and
cannot silently re-label them later.

Anything not in the table passes through unchanged apart from trimming. A country we
have never seen is not a mistake, and guessing at its canonical form (title-casing
"UAE" into "Uae") would be one.
"""

# alias (lowercased, trimmed) -> canonical spelling
_ALIASES = {
    "korea": "South Korea", "kr": "South Korea", "kor": "South Korea",
    "korea, south": "South Korea", "republic of korea": "South Korea",
    "south korea": "South Korea", "韩国": "South Korea", "대한민국": "South Korea",
    "한국": "South Korea",

    "us": "USA", "u.s.": "USA", "u.s.a.": "USA", "usa": "USA",
    "united states": "USA", "united states of america": "USA", "america": "USA",
    "美国": "USA",

    "uk": "UK", "gb": "UK", "united kingdom": "UK", "great britain": "UK",
    "england": "UK", "英国": "UK",

    "brazil": "Brazil", "brasil": "Brazil", "br": "Brazil", "巴西": "Brazil",
    "mexico": "Mexico", "méxico": "Mexico", "mx": "Mexico", "墨西哥": "Mexico",
    "chile": "Chile", "cl": "Chile", "智利": "Chile",
    "argentina": "Argentina", "ar": "Argentina", "阿根廷": "Argentina",
    "colombia": "Colombia", "co": "Colombia", "哥伦比亚": "Colombia",
    "peru": "Peru", "perú": "Peru", "pe": "Peru", "秘鲁": "Peru",
    "canada": "Canada", "ca": "Canada", "加拿大": "Canada",
}


def normalize(value: str | None) -> str | None:
    """Canonical spelling for a country as written by any of the capture paths."""
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return cleaned
    return _ALIASES.get(cleaned.lower(), cleaned)
