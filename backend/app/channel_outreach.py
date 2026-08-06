import datetime
import random
import re
import time
from typing import Callable

from app import campaigns
from app.personalize import render

# per-channel: which lead column holds the contact target
_CONTACT_COL = {"whatsapp": "phone", "instagram": "instagram", "facebook": "facebook"}
# default rate limits (seconds) — browser channels must go slow to avoid bans.
# Facebook is the most aggressive at banning cold DMs, so it goes slowest.
DEFAULT_DELAY = {"whatsapp": (60, 90), "instagram": (120, 240), "facebook": (150, 300)}
# hard cap per run — exceeding ~20 got the WhatsApp account rate-limited (2026-05-15)
MAX_BATCH = 20
# per-channel daily cap (2 batches/day; FB lower — highest ban risk of the three)
DAILY_CAP = {"whatsapp": 40, "instagram": 40, "facebook": 20}


def sent_today(conn, channel: str) -> int:
    today = datetime.date.today().isoformat()
    return conn.execute(
        "SELECT COUNT(*) FROM outreach WHERE channel=? AND status='messaged' AND message_sent_date=?",
        (channel, today),
    ).fetchone()[0]


def _target(channel: str, lead: dict) -> str:
    raw = lead[_CONTACT_COL[channel]]
    if channel == "whatsapp":
        return re.sub(r"\D", "", raw or "")
    return (raw or "").lstrip("@")


def eligible(conn, lead_nos: list[int], channel: str) -> list[dict]:
    if not lead_nos:
        return []
    col = _CONTACT_COL[channel]
    placeholders = ",".join("?" * len(lead_nos))
    rows = conn.execute(
        f"""SELECT l.no, l.company_en, l.contact_name, l.country, l.city,
                   l.phone, l.instagram, l.facebook, l.hook, l.brief
            FROM leads l
            WHERE l.no IN ({placeholders})
              AND l.{col} IS NOT NULL AND l.{col} != ''
              AND COALESCE(l.do_not_contact, 0) = 0
              AND l.no NOT IN (
                  SELECT lead_no FROM send_log
                  WHERE date(sent_at, 'localtime')=date('now', 'localtime'))
              AND l.no NOT IN (
                  SELECT lead_no FROM outreach WHERE channel=? AND status IN ('messaged','replied'))
            ORDER BY l.no""",
        [*lead_nos, channel],
    ).fetchall()
    return [dict(r) for r in rows]


def _mark_messaged(conn, lead_no: int, channel: str, date: str) -> None:
    from app import recheck, repository
    conn.execute(
        "INSERT INTO outreach(lead_no, channel, status, touch_count, message_sent_date)"
        " VALUES (?, ?, 'messaged', 1, ?)"
        " ON CONFLICT(lead_no, channel) DO UPDATE SET"
        " status='messaged', touch_count=touch_count+1, message_sent_date=excluded.message_sent_date",
        (lead_no, channel, date),
    )
    conn.commit()
    repository.advance_stage(conn, lead_no, "contacted")
    recheck.schedule_after_send(conn, lead_no)


def send_channel_campaign(conn, lead_nos: list[int], channel: str, message: str,
                          engine, delay_range: tuple[int, int] | None = None,
                          image: str | None = None, campaign: str | None = None,
                          on_progress: Callable[[int, int], None] | None = None) -> dict:
    if delay_range is None:
        delay_range = DEFAULT_DELAY.get(channel, (60, 90))
    today = datetime.date.today().isoformat()
    label = campaign or campaigns.default_label(channel)
    all_targets = eligible(conn, lead_nos, channel)
    remaining_today = max(0, DAILY_CAP.get(channel, MAX_BATCH) - sent_today(conn, channel))
    targets = all_targets[:min(MAX_BATCH, remaining_today)]
    deferred = len(all_targets) - len(targets)
    sent = failed = 0
    errors: list[dict] = []
    for i, lead in enumerate(targets, 1):
        try:
            engine.send_message(channel, _target(channel, lead), render(message, lead), image)
            _mark_messaged(conn, lead["no"], channel, today)
            campaigns.log_send(conn, lead["no"], channel, label)
            sent += 1
        except Exception as exc:  # noqa: BLE001
            failed += 1
            errors.append({"no": lead["no"], "error": str(exc)})
        if on_progress:
            on_progress(i, len(targets))
        if i < len(targets):
            lo, hi = delay_range
            if hi > 0:
                time.sleep(random.randint(lo, hi))
    return {"sent": sent, "failed": failed, "deferred": deferred,
            "skipped": len(lead_nos) - len(all_targets), "errors": errors}
