"""Today's social DM queue: the Agent prepares it, Allen presses send.

Nothing in this module sends. The queue keeps the existing pacing, channel controls,
Message Guard, deduplication, and human-send boundary. docs/127 changes only the sales
copy contract: Rental / Install / General, a short capability statement, and one useful
question. Outdoor is an application fact, never a DM family.
"""
from __future__ import annotations

import datetime as dt
import random
import re

from app import local_time, message_guard
from app.personalize import render

CHANNELS = ("whatsapp", "instagram", "facebook")
DAILY_RANGE = {"whatsapp": (8, 15), "instagram": (8, 15), "facebook": (5, 9)}
WEEKEND_FACTOR = 0.5

_CONTACT_COL = {"whatsapp": "phone", "instagram": "instagram", "facebook": "facebook"}
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

# Four sentence shapes per segment, selected deterministically by lead number. All claims
# are about us, never invented facts about the recipient. The General family uses its
# question to learn the missing segmentation fact instead of pretending the company is
# Rental, Install, signage, or anything else.
_FAMILIES: dict[str, tuple[str, ...]] = {
    "rental": (
        "we supply LED panels for rental and staging work. What pitch do you use most often on your shows?",
        "we work with event and rental teams on LED display panels. Which pitch is most common in your rental inventory?",
        "rental and staging LED is a core part of what we supply. Do you have a rental project coming up that needs another factory option?",
        "we supply LED panels for stage and touring work. Which pitch do you run most often?",
    ),
    "install": (
        "we supply LED display panels for AV integrators and fixed-install projects. What pitch are you working around on your next job?",
        "we work with installers on fixed LED projects. Do you have a screen specification in progress right now?",
        "fixed-install LED is a core part of our work with integrators. What application are you specifying next?",
        "we supply LED panels for commercial installation projects. What screen size are you working around?",
    ),
    "general": (
        "we supply LED display panels to rental companies and AV installers. Do you mainly handle rental work, fixed install, or both?",
        "we work with LED rental and installation companies. Which side is more relevant for you: rental, install, or both?",
        "we supply LED panels for both event and fixed-project work. Is rental, fixed install, or both closer to what you do?",
        "we supply LED display panels to the trade. Are your LED projects mostly rental, fixed install, or a mix?",
    ),
}


def sentence_for(segment: str, nth: int) -> str:
    family = _FAMILIES[segment]
    return family[nth % len(family)]


def variant_of(lead: dict) -> str:
    """Stable copy-variant identity for experiment reporting (docs/90 R2)."""
    from app import copy_segments

    segment = copy_segments.segment_of(lead)
    nth = int(lead.get("no") or 0) % len(_FAMILIES[segment])
    return f"social:{segment}#{nth}"


def ensure_schema(conn) -> None:
    conn.executescript(SCHEMA)
    have = {r["name"] for r in conn.execute("PRAGMA table_info(social_dm_queue)")}
    if "variant" not in have:
        conn.execute("ALTER TABLE social_dm_queue ADD COLUMN variant TEXT")
    conn.commit()


def sales_day(now: dt.datetime | None = None) -> str:
    """Sales day changes at the configured Shenzhen 09:00 boundary (docs/92 R2)."""
    return local_time.sales_day(now).isoformat()


def _allowance(channel: str, now: dt.datetime) -> int:
    low, high = DAILY_RANGE[channel]
    day = local_time.sales_day(now)
    rng = random.Random(f"{day.isoformat()}:{channel}")
    count = rng.randint(low, high)
    if day.weekday() >= 5:
        count = max(2, int(count * WEEKEND_FACTOR))
    return count


def _day_started(now: dt.datetime | None = None) -> str:
    return dt.datetime.combine(
        local_time.sales_day(now), local_time.DAY_STARTS).strftime("%Y-%m-%d %H:%M:%S")


_FIT_RE = re.compile(r"\((\d+)\)")


def _fit_score(target_fit: str | None) -> int:
    match = _FIT_RE.search(str(target_fit or ""))
    return int(match.group(1)) if match else 0


def _candidates(conn, now: dt.datetime) -> list[dict]:
    """Eligible leads, with buying signal / ICP / specific hook ranked first."""
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

    from app import icp

    leads = [dict(r) for r in rows if not icp.is_off_trade(r)]
    leads.sort(key=lambda r: (-int(r["signal"] or 0), -_fit_score(r["target_fit"]),
                              0 if str(r["hook"] or "").strip() else 1,
                              int(r["touched"] or 0), r["no"]))
    return leads


def _channel_for(conn, lead: dict, taken: set[str]) -> tuple[str, str] | None:
    """Choose at most one usable social channel for this company today."""
    from app import channel_outreach as co

    for channel in _CHANNEL_PREFERENCE:
        if channel in taken:
            continue
        if not str(lead.get(_CONTACT_COL[channel]) or "").strip():
            continue
        if channel == "whatsapp" and (lead.get("whatsapp_status") or "") == "none":
            continue
        from app import recontact
        blocked = conn.execute(
            f"SELECT 1 FROM ({recontact.BLOCKED_SQL}) WHERE lead_no=?",
            [*recontact.blocked_params(channel), lead["no"]]).fetchone()
        if blocked:
            continue
        try:
            target = co._target(channel, lead)
        except Exception:  # noqa: BLE001 — unusable handle means not a candidate
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
        parts = [greeting, "{hook}", sentence[0].upper() + sentence[1:]]
    else:
        parts = [greeting, sentence]
    return render(" ".join(parts), lead).strip()


def build_today(conn, now: dt.datetime | None = None) -> dict:
    """Prepare today's queue. Sends nothing; it only writes reviewable rows."""
    ensure_schema(conn)
    now = now or dt.datetime.now()
    today = sales_day(now)
    conn.execute("DELETE FROM social_dm_queue WHERE queue_date != ? AND edited = 0", (today,))
    conn.execute("DELETE FROM social_dm_queue WHERE queue_date != ?", (today,))

    kept = {row["lead_no"]: dict(row) for row in conn.execute(
        "SELECT * FROM social_dm_queue WHERE queue_date=? AND edited=1", (today,))}
    conn.execute("DELETE FROM social_dm_queue WHERE queue_date=? AND edited=0", (today,))

    from app import social_autonomy
    allowance = {c: (0 if social_autonomy.get(conn, c) == "off" else _allowance(c, now))
                 for c in CHANNELS}
    for row in kept.values():
        allowance[row["channel"]] = max(0, allowance[row["channel"]] - 1)

    holds: list[dict] = []
    rank = 0
    per_channel = {c: 0 for c in CHANNELS}
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
    """Rows that will not auto-send and therefore genuinely wait for Allen."""
    from app import social_autonomy

    return sum(1 for row in today(conn, now)
               if row["status"] == "ready"
               and social_autonomy.effective_mode(
                   social_autonomy.get(conn, row["channel"]), row["country"]) != "auto")


def edit(conn, queue_id: int, body: str) -> bool:
    """A human-edited message is never overwritten by a queue rebuild."""
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


def mark_no_whatsapp(conn, queue_id: int) -> bool:
    """Persist the human-observed fact that this number has no WhatsApp account."""
    row = conn.execute(
        "SELECT lead_no FROM social_dm_queue"
        " WHERE id=? AND status='ready' AND channel='whatsapp'", (queue_id,)).fetchone()
    if row is None:
        return False
    conn.execute("UPDATE leads SET whatsapp_status='none' WHERE no=?", (row["lead_no"],))
    conn.execute("DELETE FROM social_dm_queue WHERE id=?", (queue_id,))
    conn.commit()
    return True
