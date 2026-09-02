"""Has each pipeline actually produced anything lately (docs/86 R2).

Every check that existed before this one asks whether something is *connected* — the
mailbox, the browser, the model, the day's quota. None of them asks whether the work
came out the other end, and that is the shape of every failure this book has produced:

  * 关注队列 was gated on a condition that never became true. It ran zero times from the
    day it shipped, and nothing said so.
  * The discovery page dropped `hook` on import for months. 645 companies were silently
    excluded from the DM queue.
  * 99 enrollments sat past the end of a shortened sequence, reading "active" forever.
  * `browser_installed` matched any chromium revision, so the check passed while the
    browser it checked was unusable.

On 09-02 Instagram had sent nothing for seven days and Facebook and WhatsApp for five,
while the dashboard showed a green 自主销售正常. One sentence would have caught all of
it: what did this channel produce, and when did it last produce anything.

A channel switched off is not a failure — silence is what "off" means. Only a channel
that is on and has gone quiet is worth a word.
"""
from __future__ import annotations

import datetime as dt

# How long a live channel may produce nothing before it is worth saying out loud.
# Email runs daily; the social channels run in batches and go quiet over a weekend.
QUIET_DAYS = {"email": 2, "whatsapp": 5, "instagram": 5, "facebook": 5}

LABEL = {"email": "邮件", "whatsapp": "WhatsApp", "instagram": "Instagram",
         "facebook": "Facebook"}


def _enabled(conn, channel: str) -> bool:
    """Whether this channel is meant to be producing at all (docs/53 R1)."""
    row = conn.execute(
        "SELECT value FROM settings WHERE key=?", (f"channel_autonomy_{channel}",)
    ).fetchone()
    if row is not None and str(row["value"]).strip().lower() in ("off", "0", "false"):
        return False
    return True


def channel_output(conn, today: dt.date | None = None) -> list[dict]:
    """Per channel: how much it produced today, and when it last produced anything."""
    today = today or dt.date.today()
    out = []
    for channel in ("email", "whatsapp", "instagram", "facebook"):
        row = conn.execute(
            "SELECT COUNT(*) n, MAX(sent_at) last FROM send_log WHERE channel=?",
            (channel,)).fetchone()
        last_raw = row["last"]
        last_date = None
        if last_raw:
            try:
                last_date = dt.datetime.fromisoformat(str(last_raw)).date()
            except ValueError:
                last_date = None
        sent_today = conn.execute(
            "SELECT COUNT(*) n FROM send_log WHERE channel=? AND substr(sent_at,1,10)=?",
            (channel, today.isoformat())).fetchone()["n"]
        quiet = (today - last_date).days if last_date else None
        out.append({
            "channel": channel, "label": LABEL[channel],
            "enabled": _enabled(conn, channel),
            "total": row["n"], "sent_today": sent_today,
            "last_date": last_date.isoformat() if last_date else None,
            "quiet_days": quiet,
            "stalled": (
                _enabled(conn, channel)
                and row["n"] > 0
                and quiet is not None
                and quiet >= QUIET_DAYS[channel]
            ),
        })
    return out


def stalled(conn, today: dt.date | None = None) -> list[dict]:
    """Only the live channels that have gone quiet. A channel that never ran is not
    stalled — it has not started, which is a different sentence and a different fix."""
    return [c for c in channel_output(conn, today) if c["stalled"]]


def summary(conn, today: dt.date | None = None) -> str:
    """One line naming what went quiet and since when — the sentence that was missing."""
    rows = stalled(conn, today)
    if not rows:
        return ""
    parts = [f"{c['label']} 已 {c['quiet_days']} 天没有发出任何东西"
             f"（上次 {c['last_date']}）" for c in rows]
    return "；".join(parts)
