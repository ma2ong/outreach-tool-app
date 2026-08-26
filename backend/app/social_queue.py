"""Today's social DM queue: the Agent prepares it, Allen presses send.

`AGENTS.md` forbids auto-starting a WhatsApp/Instagram/Facebook conversation and that
does not change here. The reason is one line up in `channel_outreach.py`: exceeding ~20
in a run got the WhatsApp account rate-limited on 2026-05-15. An email that lands badly
costs a domain you can warm up again; an Instagram account that lands badly is gone, and
so is the +86 number that carries WeChat and every customer contact.

What this module does is split the work either side of that rule. Picking who to write
to out of nine hundred companies, deciding the channel, and writing a sentence about each
one is an hour a day that nobody does — which is why 518 Instagram and 373 Facebook
handles sat untouched for a month while email went out daily. That part is automated.
Pressing send stays a person.

Nothing in here sends. There is deliberately no path from this table to the browser
engine: `api/social_queue.py` hands the confirmed rows to the same
`channel_outreach.send_channel_campaign` the manual panel uses, and only on a request.
"""
from __future__ import annotations

import datetime as dt
import random
import re

from app import message_guard
from app.personalize import render

CHANNELS = ("whatsapp", "instagram", "facebook")

# Deliberately far below channel_outreach.DAILY_CAP (40/40/20). Platforms do not count
# messages, they look at whether you behave like a person, and a script that sends its
# full allowance every day at the same hour is the first pattern they recognise.
DAILY_RANGE = {"whatsapp": (8, 15), "instagram": (8, 15), "facebook": (5, 9)}
WEEKEND_FACTOR = 0.5

# The lead column holding each channel's address, and how much we trust it as a target.
_CONTACT_COL = {"whatsapp": "phone", "instagram": "instagram", "facebook": "facebook"}
# Instagram first: a handle read off the company's own site is a surer target than a
# phone number that may be a switchboard, and Facebook bans coldest so it goes last.
_CHANNEL_PREFERENCE = ("instagram", "whatsapp", "facebook")

SCHEMA = """
CREATE TABLE IF NOT EXISTS social_dm_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    queue_date TEXT NOT NULL,
    lead_no INTEGER NOT NULL,
    channel TEXT NOT NULL,
    target TEXT NOT NULL,
    body TEXT NOT NULL,
    rank_order INTEGER NOT NULL DEFAULT 0,
    reason TEXT,
    edited INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'ready',
    created_at TEXT NOT NULL,
    FOREIGN KEY(lead_no) REFERENCES leads(no) ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_social_queue_day_lead
    ON social_dm_queue(queue_date, lead_no);
CREATE INDEX IF NOT EXISTS idx_social_queue_day ON social_dm_queue(queue_date, rank_order);
"""

# What goes out. Short, because a DM is one sentence — there is no subject line to carry
# any of the weight, so the whole message has to be about them.
#
# Several shapes, not one. The first real run produced 31 messages whose wording differed
# only in the hook: same opening, same clause order, same closing. A platform reads the
# pattern, not the nouns, so the sentence structure varies too. Chosen by lead number so
# a company's message does not change under Allen every time he refreshes.
_TEMPLATES = (
    "Hi{contact_comma} {hook} We manufacture the LED panels behind that kind of work — "
    "happy to send specs if something is coming up.",
    "Hi{contact_comma} {hook} We supply the panels for exactly this — if you have a job "
    "coming up, tell me the pitch and size and I'll send specs.",
    "Hi{contact_comma} {hook} We're an LED display manufacturer and work with rental and "
    "AV companies directly. Worth a conversation if anything is in the pipeline?",
    "Hi{contact_comma} {hook} That's the sort of work our panels go into. Happy to be a "
    "spec-and-pricing contact whenever a project needs one.",
)


def ensure_schema(conn) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def _today(now: dt.datetime | None = None) -> str:
    return (now or dt.datetime.now()).date().isoformat()


def _allowance(channel: str, now: dt.datetime) -> int:
    """How many of this channel to prepare today — a range, never a constant.

    Seeded on the date so a day's number is stable if the queue is rebuilt, while still
    differing from one day to the next.
    """
    low, high = DAILY_RANGE[channel]
    rng = random.Random(f"{_today(now)}:{channel}")
    count = rng.randint(low, high)
    if now.weekday() >= 5:
        count = max(2, int(count * WEEKEND_FACTOR))
    return count


_FIT_RE = re.compile(r"\((\d+)\)")


def _fit_score(target_fit: str | None) -> int:
    match = _FIT_RE.search(str(target_fit or ""))
    return int(match.group(1)) if match else 0


def _candidates(conn, now: dt.datetime) -> list[dict]:
    """Leads worth a DM today, best first.

    Excluded: no hook (a DM that says nothing about the recipient is worse than a cold
    email — an email at least has a subject line), already reached on that channel,
    do-not-contact, and anyone the email sequence is touching today. We had just
    finished untangling leads enrolled in two sequences at once; putting a customer in
    an email and a DM on the same morning is the same mistake wearing a different hat.
    """
    from app import sales_intelligence

    sales_intelligence.ensure_schema(conn)
    rows = conn.execute(
        """
        SELECT l.no, l.company_en, l.contact_name, l.country, l.city, l.website,
               l.hook, l.brief, l.phone, l.instagram, l.facebook, l.target_fit,
               COALESCE(MAX(CASE WHEN b.status != 'dismissed' THEN b.confidence END), 0) signal,
               EXISTS(SELECT 1 FROM outreach o WHERE o.lead_no=l.no
                      AND o.status IN ('messaged','replied')) touched
        FROM leads l
        LEFT JOIN buying_signals b ON b.lead_no = l.no
        WHERE COALESCE(l.do_not_contact, 0) = 0
          AND COALESCE(l.hook, '') != ''
          AND l.no NOT IN (SELECT lead_no FROM send_log
                           WHERE date(sent_at, 'localtime') = date(?))
          AND l.no NOT IN (SELECT e.lead_no FROM sequence_enrollments e
                           JOIN sequences s ON s.id = e.sequence_id
                           WHERE e.status='active' AND s.channel='email'
                             AND e.next_due_date <= date(?))
        GROUP BY l.no
        """,
        (_today(now), _today(now)),
    ).fetchall()
    # The ICP score lives inside `target_fit` as "租赁公司 (98)", so ranking happens here
    # rather than in SQL.
    leads = [dict(r) for r in rows]
    leads.sort(key=lambda r: (-int(r["signal"] or 0), -_fit_score(r["target_fit"]),
                              int(r["touched"] or 0), r["no"]))
    return leads


def _channel_for(conn, lead: dict, taken: set[str]) -> tuple[str, str] | None:
    """The one channel to use for this company today, or None if none is usable."""
    from app import channel_outreach as co

    for channel in _CHANNEL_PREFERENCE:
        if channel in taken:
            continue
        if not str(lead.get(_CONTACT_COL[channel]) or "").strip():
            continue
        already = conn.execute(
            "SELECT 1 FROM outreach WHERE lead_no=? AND channel=?"
            " AND status IN ('messaged','replied')", (lead["no"], channel)).fetchone()
        if already:
            continue
        try:
            target = co._target(channel, lead)
        except Exception:  # noqa: BLE001 — an unusable handle is simply not a candidate
            continue
        if target:
            return channel, target
    return None


def _compose(lead: dict) -> str:
    contact = str(lead.get("contact_name") or "").strip()
    template = _TEMPLATES[int(lead.get("no") or 0) % len(_TEMPLATES)]
    # replace(), not format(): the template still carries {hook} for the renderer.
    text = template.replace("{contact_comma}", f" {contact}," if contact else ",")
    return render(text, lead).strip()


def build_today(conn, now: dt.datetime | None = None) -> dict:
    """Prepare today's queue. Sends nothing, and cannot: it only writes rows."""
    ensure_schema(conn)
    now = now or dt.datetime.now()
    today = _today(now)
    # Yesterday's queue is not carried over. A three-day-old DM list is stale, and stale
    # lists are how the 89-item task pile happened.
    conn.execute("DELETE FROM social_dm_queue WHERE queue_date != ? AND edited = 0", (today,))
    conn.execute("DELETE FROM social_dm_queue WHERE queue_date != ?", (today,))

    kept = {row["lead_no"]: dict(row) for row in conn.execute(
        "SELECT * FROM social_dm_queue WHERE queue_date=? AND edited=1", (today,))}
    conn.execute("DELETE FROM social_dm_queue WHERE queue_date=? AND edited=0", (today,))

    # A channel switched off (docs/53 R1) is not prepared at all: a queue nobody may
    # send is just a list to scroll past.
    from app import social_autonomy
    allowance = {c: (0 if social_autonomy.get(conn, c) == "off" else _allowance(c, now))
                 for c in CHANNELS}
    for row in kept.values():
        allowance[row["channel"]] = max(0, allowance[row["channel"]] - 1)

    holds: list[dict] = []
    rank = 0
    per_channel = {c: 0 for c in CHANNELS}
    # Two identical DMs going out the same morning is the plainest bot signature there
    # is — and it happens easily, because a hook is generated from website keywords and
    # several companies legitimately end up with the same sentence. The message has to
    # differ per company or it does not go.
    seen_bodies: set[str] = {row["body"].strip().lower() for row in kept.values()}
    for lead in _candidates(conn, now):
        if lead["no"] in kept:
            per_channel[kept[lead["no"]]["channel"]] += 1
            continue
        if all(allowance[c] <= 0 for c in CHANNELS):
            break
        full = {c for c in CHANNELS if allowance[c] <= 0}
        picked = _channel_for(conn, lead, full)
        if picked is None:
            continue
        channel, target = picked
        body = _compose(lead)
        verdict = message_guard.check(body, lead, channel="email")  # judge as a first touch
        if verdict.blocked:
            holds.append({"lead_no": lead["no"], "company": lead["company_en"],
                          "reason": verdict.reason, "detail": verdict.detail})
            continue
        if body.strip().lower() in seen_bodies:
            holds.append({"lead_no": lead["no"], "company": lead["company_en"],
                          "reason": "duplicate",
                          "detail": f"这条私信和今天另一条一字不差（{lead['company_en']} 的 hook 太通用），"
                                    "补一条更具体的开场白再发"})
            continue
        seen_bodies.add(body.strip().lower())
        rank += 1
        conn.execute(
            "INSERT INTO social_dm_queue(queue_date, lead_no, channel, target, body,"
            " rank_order, created_at) VALUES (?,?,?,?,?,?,?)",
            (today, lead["no"], channel, target, body, rank, now.isoformat()))
        allowance[channel] -= 1
        per_channel[channel] += 1
    conn.commit()
    return {"date": today, "queued": sum(per_channel.values()), "per_channel": per_channel,
            "held": len(holds), "holds": holds[:20]}


def today(conn, now: dt.datetime | None = None) -> list[dict]:
    ensure_schema(conn)
    return [dict(r) for r in conn.execute(
        "SELECT q.*, l.company_en, l.country, l.website FROM social_dm_queue q"
        " JOIN leads l ON l.no = q.lead_no"
        " WHERE q.queue_date=? ORDER BY q.rank_order", (_today(now),))]


def edit(conn, queue_id: int, body: str) -> bool:
    """Allen's wording wins: a rebuild never overwrites a message he touched."""
    text = str(body or "").strip()
    if not text:
        return False
    cur = conn.execute(
        "UPDATE social_dm_queue SET body=?, edited=1 WHERE id=? AND status='ready'",
        (text, queue_id))
    conn.commit()
    return cur.rowcount > 0


def drop(conn, queue_id: int) -> bool:
    cur = conn.execute("DELETE FROM social_dm_queue WHERE id=? AND status='ready'", (queue_id,))
    conn.commit()
    return cur.rowcount > 0
