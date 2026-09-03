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

from app import local_time, message_guard
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
    variant TEXT,
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
# The wording is the 08-31 13:41 version, restored: 文案怎么全是后面 codex 改了之后的文案.
# It asks for the pitch and the size, which is a thing a person can answer in one line.
#
# One family per customer type, and nothing else (docs/84 R2). There used to be a second
# family for leads that had a hook, and it did not vary by type — so the 467 companies we
# knew the most about got the vaguest sentence, and the 161 we knew nothing about got the
# targeted one. The hook now sits in front as its own sentence instead of inside the
# template, which is what let the two families collapse into one: no clause depends on it
# any more, so its absence costs a sentence rather than breaking the one that follows.
#
# Four shapes per type, not one. The first real run produced 31 messages differing only
# in the hook: same opening, same clause order, same closing. A platform reads the
# pattern, not the nouns. Chosen by lead number so a company's message does not change
# under Allen every time he refreshes.
#
# Nothing here states a fact about the recipient — every sentence is about us — so
# docs/45 holds even when the type is wrong. A wrong type costs a sentence that misses;
# it cannot cost a false claim.
_FAMILIES: dict[str, tuple[str, ...]] = {
    "rental": (
        "we manufacture LED panels for event and rental work — stage, touring, "
        "festivals. If you have a job coming up, tell me the pitch and size and "
        "I'll send specs.",
        "we build the LED panels rental and staging companies put on the road. "
        "Happy to send specs and pricing if something is in the calendar.",
        "we're an LED manufacturer working with event and rental companies direct — "
        "no distributor in between. Worth a conversation?",
        "stage and touring LED is what we build. Happy to be the spec-and-pricing "
        "contact next time a show needs panels.",
    ),
    "install": (
        "we manufacture LED display panels and work with AV integrators and "
        "installers directly. Happy to be a spec-and-pricing contact whenever a "
        "project needs one.",
        "we're an LED display manufacturer supplying integrators direct. If you "
        "have a fixed install coming up, send me the pitch and size and I'll come "
        "back with specs.",
        "fixed-install LED is what we make — indoor and outdoor, direct from the "
        "factory. Worth a conversation if anything is in the pipeline?",
        "we build LED panels for integrators and installation companies. Send me a "
        "pitch and a size and I'll come back with specs and pricing.",
    ),
    "outdoor": (
        "we manufacture outdoor LED displays — billboards, facades, roadside. Happy "
        "to send specs and pricing if something is coming up.",
        "we build the outdoor LED panels behind billboards and building facades. "
        "Worth a conversation if you have a site in planning?",
        "outdoor LED is what we manufacture, direct from the factory. Tell me the "
        "pitch and the size and I'll send specs.",
        "we're an LED manufacturer working with outdoor advertising companies "
        "direct. Happy to be a spec-and-pricing contact when a site comes up.",
    ),
    "general": (
        "we're an LED display manufacturer and work with rental, AV and signage "
        "companies directly. Worth a conversation if anything is in the pipeline?",
        "we manufacture LED display panels and sell to the trade direct. If you "
        "have a project coming up, tell me the pitch and size and I'll send specs.",
        "lED display panels are what we build — direct from the factory, no "
        "distributor in between. Happy to send specs whenever something comes up.",
        "we're an LED panel manufacturer. Happy to be a spec-and-pricing contact "
        "whenever a project needs one — tell me the pitch and the size.",
    ),
}


def sentence_for(segment: str, nth: int) -> str:
    """The one sentence this customer type gets, picked by lead number."""
    family = _FAMILIES[segment]
    return family[nth % len(family)]


def variant_of(lead: dict) -> str:
    """这条 DM 用的是哪一版文案（docs/90 R2）。

    社媒文案不是随手写的：家族由客户类型决定，家族内哪一句由客户编号轮换。
    这两个数合起来就是变体身份，只是一直没被记下来 —— 46 条社媒发送至今
    在 `send_log.variant` 上全是空的，等于每天都在发不可测的信。
    """
    from app import copy_segments

    segment = copy_segments.segment_of(lead)
    nth = int(lead.get("no") or 0) % len(_FAMILIES[segment])
    return f"social:{segment}#{nth}"



def ensure_schema(conn) -> None:
    conn.executescript(SCHEMA)
    # docs/90 R2 —— 队列建好之后才加的列，老库要补上。
    have = {r["name"] for r in conn.execute("PRAGMA table_info(social_dm_queue)")}
    if "variant" not in have:
        conn.execute("ALTER TABLE social_dm_queue ADD COLUMN variant TEXT")
    conn.commit()


def sales_day(now: dt.datetime | None = None) -> str:
    """今天是哪一天 —— 深圳上午 9 点换日，不是零点（docs/92 R2）。

    队列的日期、删除的边界、发送窗口用的必须是同一条日界线。原来这里用日历日期，而发送
    时刻按收件人时区算，两个日历互不知情：美国客户的时刻还没到，队列已经在深圳零点被删了。
    """
    return local_time.sales_day(now).isoformat()


def _allowance(channel: str, now: dt.datetime) -> int:
    """How many of this channel to prepare today — a range, never a constant.

    Seeded on the date so a day's number is stable if the queue is rebuilt, while still
    differing from one day to the next.
    """
    low, high = DAILY_RANGE[channel]
    day = local_time.sales_day(now)
    rng = random.Random(f"{day.isoformat()}:{channel}")
    count = rng.randint(low, high)
    if day.weekday() >= 5:
        count = max(2, int(count * WEEKEND_FACTOR))
    return count


def _day_started(now: dt.datetime | None = None) -> str:
    """销售日开始的那一刻，深圳墙上时钟 —— send_log 的 'localtime' 就是这个钟。"""
    return dt.datetime.combine(
        local_time.sales_day(now), local_time.DAY_STARTS).strftime("%Y-%m-%d %H:%M:%S")


_FIT_RE = re.compile(r"\((\d+)\)")


def _fit_score(target_fit: str | None) -> int:
    match = _FIT_RE.search(str(target_fit or ""))
    return int(match.group(1)) if match else 0


def _candidates(conn, now: dt.datetime) -> list[dict]:
    """Leads worth a DM today, best first.

    Excluded: already reached on that channel, do-not-contact, and anyone the email
    sequence is touching today. We had just finished untangling leads enrolled in two
    sequences at once; putting a customer in an email and a DM on the same morning is
    the same mistake wearing a different hat.

    A missing hook is no longer an exclusion (docs/80 R1). It used to be, on the
    reasoning that a DM saying nothing about the recipient is worse than a cold email.
    That reasoning confused "nothing to say about them" with "nothing to say" — and it
    only ever bound here: email has always sent to these companies, because
    `personalize.render` simply drops the token. They still rank below companies we can
    open with something specific; the ordering below does that on its own.
    """
    from app import sales_intelligence

    sales_intelligence.ensure_schema(conn)
    rows = conn.execute(
        """
        SELECT l.no, l.company_en, l.contact_name, l.country, l.city, l.website,
               l.hook, l.brief, l.phone, l.instagram, l.facebook, l.target_fit,
               l.whatsapp_status, l.tags, l.business,
               COALESCE(MAX(CASE WHEN b.status != 'dismissed' THEN b.confidence END), 0) signal,
               EXISTS(SELECT 1 FROM outreach o WHERE o.lead_no=l.no
                      AND o.status IN ('messaged','replied')) touched
        FROM leads l
        LEFT JOIN buying_signals b ON b.lead_no = l.no
        WHERE COALESCE(l.do_not_contact, 0) = 0
          AND l.no NOT IN (SELECT lead_no FROM send_log
                           WHERE datetime(sent_at, 'localtime') >= ?)
          AND l.no NOT IN (SELECT e.lead_no FROM sequence_enrollments e
                           JOIN sequences s ON s.id = e.sequence_id
                           WHERE e.status='active' AND s.channel='email'
                             AND e.next_due_date <= date(?))
        GROUP BY l.no
        """,
        (_day_started(now), sales_day(now)),
    ).fetchall()
    # The ICP score lives inside `target_fit` as "租赁公司 (98)", so ranking happens here
    # rather than in SQL.
    leads = [dict(r) for r in rows]
    # docs/80 R3. A hook ranks above a generic opener, but below a buying signal and
    # below ICP fit: a company that is buying right now is worth the slot even if all
    # we can say is what we make. There are 8-15 slots a day, so this is the whole of
    # "generic messages are allowed, and they go last".
    leads.sort(key=lambda r: (-int(r["signal"] or 0), -_fit_score(r["target_fit"]),
                              0 if str(r["hook"] or "").strip() else 1,
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
        # WhatsApp already told us this number has no account; queueing it again spends
        # a browser trip to rediscover the same thing (docs/59 R2).
        if channel == "whatsapp" and (lead.get("whatsapp_status") or "") == "none":
            continue
        # docs/75 R1. This used to exclude anyone ever messaged on this channel, for good.
        # The rule now is the same two weeks that governs email: silence buys a cooldown,
        # not a permanent no. A reply still ends cold outreach here entirely.
        from app import recontact
        blocked = conn.execute(
            f"SELECT 1 FROM ({recontact.BLOCKED_SQL}) WHERE lead_no=?",
            [*recontact.blocked_params(channel), lead["no"]]).fetchone()
        if blocked:
            continue
        try:
            target = co._target(channel, lead)
        except Exception:  # noqa: BLE001 — an unusable handle is simply not a candidate
            continue
        if target:
            return channel, target
    return None


def _compose(lead: dict) -> str:
    from app import copy_segments

    contact = str(lead.get("contact_name") or "").strip()
    hook = str(lead.get("hook") or "").strip()
    no = int(lead.get("no") or 0)
    sentence = sentence_for(copy_segments.segment_of(lead), no)
    greeting = f"Hi {contact}," if contact else "Hi,"
    if hook:
        # Every hook ends in a full stop, so what follows starts a sentence of its own.
        # Directly after the greeting's comma it does not, which is why the families are
        # written lowercase and capitalised here rather than the other way round.
        parts = [greeting, "{hook}", sentence[0].upper() + sentence[1:]]
    else:
        parts = [greeting, sentence]
    # render(), not format(): {hook} is the renderer's placeholder, not ours.
    return render(" ".join(parts), lead).strip()


def build_today(conn, now: dt.datetime | None = None) -> dict:
    """Prepare today's queue. Sends nothing, and cannot: it only writes rows."""
    ensure_schema(conn)
    now = now or dt.datetime.now()
    today = sales_day(now)
    # Yesterday's queue is not carried over. A three-day-old DM list is stale, and stale
    # lists are how the 89-item task pile happened.
    #
    # `today` is the sales day now, and that is the whole of the 09-03 fix: this delete
    # used to fire at Shenzhen midnight against rows whose send moment was still hours
    # away in Chicago, so 24 of 31 messages were rebuilt and re-deleted every night
    # without ever being reachable. The boundary moved to 09:00, where the extended
    # window has already ended and nothing is waiting on the other side of it.
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
        # The personalization rule is an email rule — `GUARDED_CHANNELS` says so — and
        # this queue used to opt into it by claiming the channel was email. Keep that
        # opt-in where there is a hook: there it catches a render that silently dropped
        # the one sentence about the recipient, and sends "…behind that kind of work"
        # pointing at nothing. Drop it where there never was one, which is the case
        # docs/80 is about. The price check runs either way, on every channel.
        guarded_as = "email" if str(lead.get("hook") or "").strip() else channel
        verdict = message_guard.check(body, lead, channel=guarded_as)
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
        # 记的是排队这一刻用的那一版（docs/90 R2）。发送时不重算：标签改过之后
        # 重算会给一封已经发出去的信贴上它没用过的版本。
        conn.execute(
            "INSERT INTO social_dm_queue(queue_date, lead_no, channel, target, body,"
            " rank_order, created_at, variant) VALUES (?,?,?,?,?,?,?,?)",
            (today, lead["no"], channel, target, body, rank, now.isoformat(),
             variant_of(lead)))
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
        " WHERE q.queue_date=? ORDER BY q.rank_order", (sales_day(now),))]


def awaiting_you(conn, now: dt.datetime | None = None) -> int:
    """How many of today's rows are actually waiting for Allen (docs/92 R6).

    Not the same as "how many are queued". Three channels sat on `auto` for six days
    while the dashboard said "31 条备好了，等你按发送" — the system thought the job was
    its, Allen thought it was his, and both waited. A row belongs on his list only if
    nothing will send it on its own: the channel is not `auto`, or the country holds it
    back to manual anyway (docs/63).
    """
    from app import social_autonomy

    return sum(1 for row in today(conn, now)
               if row["status"] == "ready"
               and social_autonomy.effective_mode(
                   social_autonomy.get(conn, row["channel"]), row["country"]) != "auto")


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
