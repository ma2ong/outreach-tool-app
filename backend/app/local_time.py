"""Two clocks: ours, which decides, and theirs, which only sorts (docs/92).

`docs/65` put the send window on the customer's clock and left the queue's lifetime on
Shenzhen's. Two calendars, neither aware of the other: the queue was deleted at Shenzhen
midnight while an American message was still waiting for its 09:00 Chicago moment, so 24
of 31 messages could never go out at all, and did not, for six days, silently.

The fix is not to align them, it is to keep one. Shenzhen decides *whether* to send —
that is the machine that is switched on. The customer's clock decides *who goes first*
and nothing else: it may reorder the day, never cancel a line of it.

The table stays deliberately small and conservative. No timezone library, no daylight
saving: an hour of drift matters even less now that it only affects sort order, while a
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

# The decent hours to reach someone, in their own time. Since docs/92 this is a
# preference, not a gate: a recipient inside it goes ahead of one outside it, and a
# recipient outside it still goes.
PREFERRED = (7, 22)
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


def suits_recipient(country: str | None, now: dt.datetime | None = None) -> bool:
    """Is it a civil hour for this company right now?

    The whole of what the recipient's timezone still decides (docs/92 R3). A False here
    costs a place in the queue order, never the send: an unplaceable country and a
    customer at 03:00 both still get their message, they just go after everyone we can
    reach politely. The alternative was tried — docs/65 made both of them a veto, and a
    veto that meets a Shenzhen-dated queue is how a message waits forever.
    """
    local = local_now(country, now)
    if local is None:
        return False
    if is_weekend(local):
        return False
    return PREFERRED[0] <= local.hour < PREFERRED[1]


# ---------------------------------------------------------------- our own clock

# Everything below is Shenzhen wall-clock. It is the machine that is switched on, so it
# is the machine that decides whether anything goes out at all (docs/92 R1).
SHENZHEN_OFFSET = 8
# The normal working window, and the pause that ends it.
CORE = (dt.time(9, 0), dt.time(18, 20))
# After this, sending continues for as long as the process is alive — which is what "the
# computer is still on" means, so there is no switch to forget to press. It exists for
# the American half of the book: Shenzhen 22:00–02:00 is their morning, the best two
# hours of the day, and the old Shenzhen-midnight delete threw exactly those away.
EXTENDED_FROM = dt.time(18, 30)
# A day runs 09:00 → 09:00, not midnight → midnight. The extended window crosses Shenzhen
# midnight; a date that rolled there would delete the queue in the middle of it, which is
# the 09-03 bug wearing a different hour (docs/92 R2).
DAY_STARTS = CORE[0]


def shenzhen(now: dt.datetime | None = None) -> dt.datetime:
    """The Shenzhen wall clock. A naive time is already it; an aware one is converted.

    Both shapes arrive here — the operating loop carries aware UTC, the queue builder a
    naive local time — and answering one of them wrong is how this started.
    """
    if now is None:
        return dt.datetime.now()
    if now.tzinfo is None:
        return now
    return (now.astimezone(dt.UTC) + dt.timedelta(hours=SHENZHEN_OFFSET)).replace(tzinfo=None)


def sales_day(now: dt.datetime | None = None) -> dt.date:
    """Which day's queue is in play — one boundary for the queue, the window and the caps."""
    local = shenzhen(now)
    return local.date() if local.time() >= DAY_STARTS else local.date() - dt.timedelta(days=1)


def phase(now: dt.datetime | None = None) -> str:
    """"core" (09:00–18:20), "paused" (until 18:30), or "extended" (until 09:00)."""
    clock = shenzhen(now).time()
    if CORE[0] <= clock < CORE[1]:
        return "core"
    if CORE[1] <= clock < EXTENDED_FROM:
        return "paused"
    return "extended"


def day_ends(day: dt.date) -> dt.datetime:
    """When this sales day stops being able to send anything — 09:00 the next morning."""
    end = dt.datetime.combine(day + dt.timedelta(days=1), DAY_STARTS)
    return (end - dt.timedelta(hours=SHENZHEN_OFFSET)).replace(tzinfo=dt.UTC)


def day_starts(day: dt.date) -> dt.datetime:
    return (dt.datetime.combine(day, DAY_STARTS)
            - dt.timedelta(hours=SHENZHEN_OFFSET)).replace(tzinfo=dt.UTC)


_SLOT_MINUTES = 5
_slots_cache: dict[tuple[dt.date, str], list[dt.datetime]] = {}


def civil_slots(country: str | None, day: dt.date) -> list[dt.datetime]:
    """Every moment in this sales day at which we could reach them at a civil hour.

    Usually two stretches, because a sales day is 24 hours and their 07:00–22:00 is 15:
    for the American half of the book, sales day D covers their 19:00–22:00 the evening
    before and 07:00–19:00 the day itself. Empty when there is no such moment at all —
    a country we cannot place, or a recipient whose whole sales day is their weekend.
    """
    key = (day, str(country or "").strip().lower())
    if key not in _slots_cache:
        start, end = day_starts(day), day_ends(day)
        step = dt.timedelta(minutes=_SLOT_MINUTES)
        slots, probe = [], start
        while probe < end:
            if suits_recipient(country, probe):
                slots.append(probe)
            probe += step
        _slots_cache[key] = slots
    return _slots_cache[key]


def moment_for(lead_no: int, day: dt.date, country: str | None) -> dt.datetime:
    """When this one message goes out — inside their working hours where that is
    reachable today, and inside our own window where it is not.

    One concept rather than two, and the second version of this. The first spread every
    message across the Shenzhen core window and then let the recipient's clock hold the
    unreachable ones back. That put all thirteen American messages at the first civil
    minute their morning offered — twelve in one hour, four per channel, four times the
    density docs/52 built the whole feature around. Choosing the moment from the civil
    stretch itself spreads them over its full fifteen hours instead, which is also what
    docs/65 R3 was for: a batch leaving together is the least human thing this does.

    Where no civil moment exists the message still goes (docs/92 R3) — it just takes a
    moment from our own window, which is what "实在达不到就按计划发" means.
    """
    rng = random.Random(f"dm:{day.isoformat()}:{lead_no}")
    slots = civil_slots(country, day)
    if slots:
        return rng.choice(slots)
    start = dt.datetime.combine(day, CORE[0])
    span = int((dt.datetime.combine(day, CORE[1]) - start).total_seconds() // 60)
    return (start + dt.timedelta(minutes=rng.randrange(span))
            - dt.timedelta(hours=SHENZHEN_OFFSET)).replace(tzinfo=dt.UTC)
