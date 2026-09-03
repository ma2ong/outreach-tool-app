"""Who presses send on a social DM — per channel, and only ever what Allen chose.

`AGENTS.md` used to forbid auto-starting a WhatsApp/Instagram/Facebook conversation
outright. `docs/53` changes that in the open rather than routing around it, and changes
exactly one thing: who decides to spend the risk. The risk itself is where it was — a
banned Instagram account does not come back, and the WhatsApp number carries WeChat and
every customer contact — so `auto` costs a typed confirmation, is set per channel, and
never rises on its own.

Turning it on does not turn the volume up. The pacing from `docs/52` applies unchanged
and two constraints are added that only matter without a person in the loop: the send
time moves every day, and the day gets one run rather than a catch-up.
"""
from __future__ import annotations

import datetime as dt
import json
import random

from app import local_time, settings, social_queue

MODES = ("off", "manual", "auto")
DEFAULT_MODE = "manual"

# How much autonomy each mode carries. A send takes the more conservative of the channel
# setting and the country setting, so a country can hold back but never push forward
# (docs/63 R1).
_LEVEL = {"off": 0, "manual": 1, "auto": 2}

# Korea is most of his existing book — 176 of those companies carry tags he wrote
# himself, and some are marked 成交客户. An automatic opener to a stranger costs nothing
# when ignored; the same opener to a customer of several years reads as bulk mail.
MANUAL_COUNTRIES = {"south korea", "korea", "kr", "republic of korea"}

_K_MODE = "social_autonomy_%s"
_K_LAST_RUN_DATE = "social_autonomy_last_run_date"
_K_LAST_RUN = "social_autonomy_last_run"

# What the panel shows as "today's send time". The window itself lives in
# `local_time.CORE`; this is one representative minute inside it, moved daily so the
# screen never suggests a scheduler that fires at the same moment every day.
SEND_WINDOW = (9, 18)

# One per channel per cycle, and never closer than a minute or two apart.
#
# This is now the only thing throttling a catch-up, and it is enough. A message used to
# be discarded if its moment was more than two hours old, on the reasoning that a
# restart must not fire a whole day at once — but with 85 cycles a day, one per channel
# each, the burst it feared cannot form, and discarding was doing real harm: a message
# that missed its slot was gone for the day (docs/92 R4).
#
# The natural spacing is already an hour or so — 8-15 messages across a 12-hour window —
# so this only bites when two scheduled moments happen to collide. Guarding that edge
# with six to ten minutes was more caution than the case needs. The range is drawn
# fresh each time rather than fixed: a sender that always waits exactly 90 seconds is
# its own kind of signature.
MIN_GAP_SECONDS = (60, 120)
_K_LAST_SEND = "social_last_send_at_%s"


class ConfirmationRequired(ValueError):
    """Raised when `auto` was requested without typing the channel's name."""


def get(conn, channel: str) -> str:
    return settings.get(conn, _K_MODE % channel, DEFAULT_MODE) or DEFAULT_MODE


def all_modes(conn) -> dict[str, str]:
    return {channel: get(conn, channel) for channel in social_queue.CHANNELS}


def set_mode(conn, channel: str, mode: str, confirm: str = "") -> str:
    """Change one channel's mode. Raising the mode to `auto` requires typing its name.

    Not a yes/no dialog: this spends an account that cannot be recovered, and a dialog
    is answered reflexively. Going back down is free — stopping is never the risky
    direction.
    """
    if channel not in social_queue.CHANNELS:
        raise ValueError(f"未知渠道 {channel}")
    if mode not in MODES:
        raise ValueError(f"未知模式 {mode}")
    if mode == "auto" and confirm.strip().lower() != channel:
        raise ConfirmationRequired(
            f"打开自动发送要照抄一遍渠道名「{channel}」。这个账号被封是不可恢复的。")
    settings.set_value(conn, _K_MODE % channel, mode)
    return mode


def country_mode(country: str | None) -> str | None:
    """The ceiling this country puts on autonomy, or None when it sets none.

    A missing country follows the channel rather than defaulting to manual: blanks in
    his book are mostly unread pages, not Korea, and making him confirm a pile of
    American leads turns the confirmation into reflex clicking — which stops nothing.
    """
    key = str(country or "").strip().lower()
    return "manual" if key in MANUAL_COUNTRIES else None


def effective_mode(channel_mode: str, country: str | None) -> str:
    ceiling = country_mode(country)
    if ceiling is None:
        return channel_mode
    return channel_mode if _LEVEL[channel_mode] <= _LEVEL[ceiling] else ceiling


def send_at(day: dt.date) -> dt.datetime:
    """The moment today's automatic send is due — a different one each day."""
    rng = random.Random(f"social-send:{day.isoformat()}")
    hour = rng.randint(SEND_WINDOW[0], SEND_WINDOW[1] - 1)
    return dt.datetime.combine(day, dt.time(hour, rng.randint(0, 59)))


def _deliver(conn, items: list[dict]) -> dict:
    """Hand the confirmed rows to the same path the manual panel uses."""
    from app import channel_outreach
    from app.api import channels as channels_api
    from app.api import send as send_api

    return channel_outreach.send_prepared(
        conn, items, channels_api.ENGINE, image=send_api.DEFAULT_ATTACHMENT,
        campaign="每日社媒队列（自动）")


def last_send_at(conn, channel: str) -> str | None:
    """When a DM last actually went out on this channel — the moment, not the intent."""
    return settings.get(conn, _K_LAST_SEND % channel)


def last_run(conn) -> dict | None:
    raw = settings.get(conn, _K_LAST_RUN)
    try:
        return json.loads(raw) if raw else None
    except json.JSONDecodeError:
        return None


def run_due(conn, now: dt.datetime | None = None) -> dict:
    """Send whatever the Shenzhen clock allows right now, best recipient first.

    The window is ours (docs/92 R1): 09:00–18:20 normally, and after 18:30 for as long
    as this process is alive, which is what "the computer is still on" means. Inside it,
    the customer's clock picks each message's moment — from their own 07:00–22:00 where
    today offers one, from our window where it does not — and, among messages whose
    moment has come, puts whoever is awake first. It never cancels one.

    `docs/65` had this the other way round and it cost six silent days: their clock was
    a veto, the queue's lifetime was Shenzhen's, and 24 of 31 messages were deleted
    every night before their moment arrived.
    """
    now = now or dt.datetime.now(dt.UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.UTC)
    result = {"sent_batches": 0, "channels": {}, "held": {}}
    auto = [c for c in social_queue.CHANNELS if get(conn, c) == "auto"]
    if not auto:
        return result

    stage = local_time.phase(now)
    if stage == "paused":
        result["held"] = {"晚上 18:20–18:30 之间不发": 1}
        return result

    social_queue.ensure_schema(conn)
    day = local_time.sales_day(now)
    placeholders = ",".join("?" * len(auto))
    rows = conn.execute(
        f"SELECT q.id, q.lead_no, q.channel, q.target, q.body, q.variant, l.country"
        f" FROM social_dm_queue q JOIN leads l ON l.no = q.lead_no"
        f" WHERE q.queue_date=? AND q.status='ready' AND q.channel IN ({placeholders})"
        f" ORDER BY q.rank_order", [day.isoformat(), *auto]).fetchall()

    due, held = [], {}
    for row in rows:
        # A country set to manual stays in the queue and waits for Allen; it is held
        # back here rather than filtered out of the list he sees (docs/63).
        if effective_mode("auto", row["country"]) != "auto":
            held["韩国等你确认"] = held.get("韩国等你确认", 0) + 1
            continue
        # Its own moment, chosen inside their working hours where today offers any and
        # inside our window where it does not (docs/92 R3). A moment already past is a
        # turn that has come, never a forfeit (docs/92 R4).
        if now < local_time.moment_for(row["lead_no"], day, row["country"]):
            held["还没到这条的时刻"] = held.get("还没到这条的时刻", 0) + 1
            continue
        due.append(dict(row))
    result["held"] = held
    if not due:
        return result

    # Whoever is already awake goes first; the rest still go (docs/92 R3). Stable inside
    # each group, so rank order — signal, ICP fit, then hook — still runs the day.
    due.sort(key=lambda r: 0 if local_time.suits_recipient(r["country"], now) else 1)

    items: list[dict] = []
    taken: set[str] = set()
    for row in due:
        channel = row["channel"]
        if channel in taken:
            held["同一渠道本轮已发过一条"] = held.get("同一渠道本轮已发过一条", 0) + 1
            continue
        gap = dt.timedelta(seconds=random.randint(*MIN_GAP_SECONDS))
        last = settings.get(conn, _K_LAST_SEND % channel)
        if last:
            try:
                if now - dt.datetime.fromisoformat(last) < gap:
                    held["离上一条不够间隔"] = held.get("离上一条不够间隔", 0) + 1
                    continue
            except ValueError:  # a malformed stamp must not block sending forever
                pass
        taken.add(channel)
        items.append({k: v for k, v in row.items() if k != "country"})
    if not items:
        return result

    outcome = _deliver(conn, items) or {}
    sent = int(outcome.get("sent") or 0)
    failed = int(outcome.get("failed") or 0)
    errors = outcome.get("errors") or []
    for item in items[:sent]:
        settings.set_value(conn, _K_LAST_SEND % item["channel"], now.isoformat())
    if sent:
        sent_ids = [item["id"] for item in items[:sent]]
        placeholders = ",".join("?" * len(sent_ids))
        conn.execute(
            f"UPDATE social_dm_queue SET status='sent' WHERE id IN ({placeholders})", sent_ids)
        conn.commit()
    per_channel: dict[str, int] = {}
    for item in items[:sent]:
        per_channel[item["channel"]] = per_channel.get(item["channel"], 0) + 1
    result = {"sent_batches": 1 if sent else 0, "channels": per_channel,
              "failed": failed, "attempted": len(items)}
    # Quiet when there is nothing to say (docs/48 R3) — but reaching the send path is
    # never nothing, and "tried three, none went" is the loudest thing this feature can
    # report. It spent six days indistinguishable from a quiet day because only a
    # success was written down (docs/92 R5).
    record = {"at": now.isoformat(), "channels": per_channel,
              "failed": failed, "attempted": len(items)}
    if errors:
        record["error"] = str(errors[0].get("error"))[:200]
    settings.set_value(conn, _K_LAST_RUN, json.dumps(record, ensure_ascii=False))
    return result
