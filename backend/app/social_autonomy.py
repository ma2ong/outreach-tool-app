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

# A person pressing send never lands on the same minute two days running; a scheduler
# does unless it is told not to.
SEND_WINDOW = (9, 18)

# How late a message may still go out after its own moment. Falling behind is fine;
# catching up in one burst is how an account gets rate-limited (docs/53).
MISSED_AFTER = dt.timedelta(hours=2)

# Spreading by timezone still leaves two messages able to land in the same minute by
# chance. One per channel per cycle, and never closer than a minute or two apart.
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


def last_run(conn) -> dict | None:
    raw = settings.get(conn, _K_LAST_RUN)
    try:
        return json.loads(raw) if raw else None
    except json.JSONDecodeError:
        return None


def run_due(conn, now: dt.datetime | None = None) -> dict:
    """Send whichever queued messages are due right now in the recipient's own timezone.

    Not one batch at one moment: a single moment cannot serve a list spanning twelve
    time zones, and the Shenzhen afternoon it used to pick was 05:07 in New York. Each
    message now has its own due time inside the customer's working day, and each cycle
    sends only the ones whose moment has arrived (docs/65 R3).
    """
    now = now or dt.datetime.now(dt.UTC)
    if now.tzinfo is None:
        now = now.astimezone(dt.UTC)
    today = now.date().isoformat()
    result = {"sent_batches": 0, "channels": {}, "held": {}}
    auto = [c for c in social_queue.CHANNELS if get(conn, c) == "auto"]
    if not auto:
        return result

    social_queue.ensure_schema(conn)
    placeholders = ",".join("?" * len(auto))
    # Yesterday's queue is still in play: a customer's Thursday afternoon in Chicago is
    # Friday morning in UTC, so a row dated Thursday has its moment after UTC midnight.
    # Matching only today's date made those messages unreachable and silently unsent.
    yesterday = (now.date() - dt.timedelta(days=1)).isoformat()
    rows = conn.execute(
        f"SELECT q.id, q.lead_no, q.channel, q.target, q.body, q.queue_date, l.country"
        f" FROM social_dm_queue q JOIN leads l ON l.no = q.lead_no"
        f" WHERE q.queue_date IN (?, ?) AND q.status='ready'"
        f" AND q.channel IN ({placeholders})"
        f" ORDER BY q.rank_order", [today, yesterday, *auto]).fetchall()
    items, held = [], {}
    taken: set[str] = set()
    for row in rows:
        country = row["country"]
        # A country set to manual stays in the queue and waits for Allen; it is held
        # back here rather than filtered out of the list he sees (docs/63).
        if effective_mode("auto", country) != "auto":
            held["韩国等你确认"] = held.get("韩国等你确认", 0) + 1
            continue
        allowed, why = local_time.may_send(country, now)
        if not allowed:
            held[why] = held.get(why, 0) + 1
            continue
        # The moment belongs to the day the message was queued for, in their timezone.
        queued_on = dt.date.fromisoformat(row["queue_date"])
        due = local_time.send_minute(row["lead_no"], queued_on, country)
        if due is None:
            held["国家未知，不自动发"] = held.get("国家未知，不自动发", 0) + 1
            continue
        due = due.replace(tzinfo=dt.UTC)
        if now < due:
            held["还没到这条的时刻"] = held.get("还没到这条的时刻", 0) + 1
            continue
        # A moment long past is a moment missed, not a moment owed. Without this, a
        # service restart would fire every message whose time passed while it was down,
        # all at once — the burst docs/53 refuses to allow.
        if now - due > MISSED_AFTER:
            held["错过了今天的时刻"] = held.get("错过了今天的时刻", 0) + 1
            continue
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
        items.append({k: v for k, v in dict(row).items()
                      if k not in ("country", "queue_date")})
    result["held"] = held
    if not items:
        return result

    outcome = _deliver(conn, items) or {}
    sent = int(outcome.get("sent") or 0)
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
              "failed": int(outcome.get("failed") or 0)}
    # Quiet when there is nothing to say (docs/48 R3) — but a send spent account risk,
    # and that is never nothing.
    if sent:
        settings.set_value(conn, _K_LAST_RUN, json.dumps(
            {"at": now.isoformat(), "channels": per_channel,
             "failed": result["failed"]}, ensure_ascii=False))
    return result
