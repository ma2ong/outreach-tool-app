"""What time it is where the customer is (docs/65).

Social DMs went out at one moment each day, chosen in Shenzhen time. For the 432
American companies in the book that moment was 05:07 their time — a phone lighting up
on a bedside table, which settles the first impression before anyone reads a word.

The table is deliberately small and deliberately conservative. No timezone library, no
daylight saving: an hour of drift inside a twelve-hour window changes nothing, while a
DST table has to be maintained every year and is wrong the moment it is not.
"""
from __future__ import annotations

import datetime as dt
import random

# Hours offset from UTC. Countries that span several zones take a representative one,
# chosen to err early rather than late — better a little early on the west coast than
# after dark on the east.
UTC_OFFSET = {
    "usa": -6, "united states": -6, "us": -6,       # Central: 08:00 CT is 06:00 PT / 09:00 ET
    "canada": -6, "ca": -6,
    "mexico": -6, "mx": -6,
    "brazil": -3, "br": -3,
    "argentina": -3, "ar": -3,
    "chile": -4, "cl": -4,
    "colombia": -5, "co": -5,
    "peru": -5, "pe": -5,
    "venezuela": -4, "ve": -4,
    "south korea": 9, "korea": 9, "kr": 9,
    "japan": 9, "jp": 9,
    "china": 8, "cn": 8,
    "australia": 10, "au": 10,
    "new zealand": 12, "nz": 12,
    "india": 5, "in": 5,               # +5:30 rounded down; the window absorbs it
    "indonesia": 7, "id": 7,
    "malaysia": 8, "my": 8,
    "philippines": 8, "ph": 8,
    "vietnam": 7, "vn": 7,
    "thailand": 7, "th": 7,
    "singapore": 8, "sg": 8,
    "uk": 1, "united kingdom": 1, "gb": 1,
    "ireland": 1, "ie": 1,
    "portugal": 1, "pt": 1,
    "spain": 2, "es": 2,
    "france": 2, "fr": 2,
    "germany": 2, "de": 2,
    "italy": 2, "it": 2,
    "netherlands": 2, "nl": 2,
    "belgium": 2, "be": 2,
    "austria": 2, "at": 2,
    "poland": 2, "pl": 2,
    "sweden": 2, "se": 2,
    "norway": 2, "no": 2,
    "denmark": 2, "dk": 2,
    "finland": 3, "fi": 3,
    "greece": 3, "gr": 3,
    "turkey": 3, "tr": 3,
    "russia": 3, "ru": 3,
    "ukraine": 3, "ua": 3,
    "israel": 3, "il": 3,
    "uae": 4, "united arab emirates": 4, "ae": 4,
    "saudi arabia": 3, "sa": 3,
    "qatar": 3, "qa": 3,
    "south africa": 2, "za": 2,
    "egypt": 3, "eg": 3,
    "nigeria": 1, "ng": 1,
    "kenya": 3, "ke": 3,
    "georgia": 4, "ge": 4,
    "kazakhstan": 5, "kz": 5,
}

# The decent hours to reach someone, in their own time.
WINDOW = (8, 20)
# Email is wider on purpose: it waits in an inbox instead of lighting up a phone, so a
# letter arriving at 22:00 is at the top of the pile next morning while a DM at 22:00 is
# an interruption (docs/66 R2).
EMAIL_WINDOW = (6, 23)
# Never, under any relaxation. A push notification at 03:00 does not read as diligence.
NIGHT = (0, 6)


def offset_for(country: str | None) -> int | None:
    """Hours from UTC, or None when we cannot tell — which means we do not send."""
    return UTC_OFFSET.get(str(country or "").strip().lower())


def local_now(country: str | None, now: dt.datetime | None = None) -> dt.datetime | None:
    offset = offset_for(country)
    if offset is None:
        return None
    utc = (now or dt.datetime.now(dt.UTC))
    if utc.tzinfo is None:
        utc = utc.replace(tzinfo=dt.UTC)
    return (utc + dt.timedelta(hours=offset)).replace(tzinfo=None)


def is_weekend(local: dt.datetime) -> bool:
    """Their Saturday or Sunday — not ours. Shenzhen Sunday morning is New York
    Saturday evening, and neither end of that is a working hour."""
    return local.weekday() >= 5


def in_window(local: dt.datetime) -> bool:
    return WINDOW[0] <= local.hour < WINDOW[1]


def is_night(local: dt.datetime) -> bool:
    return NIGHT[0] <= local.hour < NIGHT[1]


def may_email(country: str | None, now: dt.datetime | None = None) -> tuple[bool, str]:
    """(allowed, why not) for email — wider than a DM, and forgiving of an unknown country.

    Guessing wrong about a DM costs a 3am interruption. Guessing wrong about an email
    costs "it arrived after they left", which is email's normal condition. Different
    cost, different rule — matching the two for the sake of symmetry would be worse
    (docs/66 R3).
    """
    local = local_now(country, now)
    if local is None:
        return True, ""
    if is_night(local):
        return False, f"对方当地凌晨 {local:%H:%M}"
    if not (EMAIL_WINDOW[0] <= local.hour < EMAIL_WINDOW[1]):
        return False, f"不在对方当地 {EMAIL_WINDOW[0]}–{EMAIL_WINDOW[1]} 点（现在 {local:%H:%M}）"
    return True, ""


def may_send(country: str | None, now: dt.datetime | None = None) -> tuple[bool, str]:
    """(allowed, why not). The reason is for the daily report, not for a retry."""
    local = local_now(country, now)
    if local is None:
        return False, "国家未知，不自动发"
    if is_weekend(local):
        return False, f"对方当地是周末（{local:%m-%d %H:%M}）"
    if is_night(local):
        return False, f"对方当地凌晨 {local:%H:%M}"
    if not in_window(local):
        return False, f"不在对方当地 {WINDOW[0]}–{WINDOW[1]} 点（现在 {local:%H:%M}）"
    return True, ""


def send_minute(lead_no: int, day: dt.date, country: str | None) -> dt.datetime | None:
    """The UTC moment to send this one message, spread across their working day.

    Per message rather than per batch: one moment cannot serve a list spanning twelve
    time zones, and 23 messages leaving in the same minute is also the least human thing
    the sender does (docs/65 R3).
    """
    offset = offset_for(country)
    if offset is None:
        return None
    rng = random.Random(f"dm:{day.isoformat()}:{lead_no}")
    hour = rng.randint(WINDOW[0], WINDOW[1] - 1)
    local = dt.datetime.combine(day, dt.time(hour, rng.randint(0, 59)))
    return local - dt.timedelta(hours=offset)
