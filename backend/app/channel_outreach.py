import datetime
import random
import re
import time
from typing import Callable

from app import campaigns, recontact
from app.personalize import render
# One calling-code table, in app/phone_format.py, because the book and the sender
# must agree about what a number is. A number we cannot make international is a
# number we do not dial (docs/62 R3).
from app.phone_format import CALLING_CODES as _CALLING_CODES
from app.phone_format import is_toll_free as _is_toll_free
from app.phone_format import split_numbers

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


# WhatsApp says this when the number has no account. Anything else — a timeout, a dead
# browser — is a fact about our run, not about the number (docs/59 R1).
_NOT_ON_WHATSAPP = re.compile(r"not on whatsapp|number not on|invalid|不存在|无效", re.I)


def _note_whatsapp_result(conn, lead_no: int, channel: str, error: str | None) -> None:
    """Keep what the send just proved about this number, so it is not rediscovered daily."""
    if channel != "whatsapp":
        return
    if error is None:
        status = "active"      # it went through, so the number is on WhatsApp
    elif _NOT_ON_WHATSAPP.search(error):
        status = "none"
    else:
        return                 # our problem, not the number's
    conn.execute("UPDATE leads SET whatsapp_status=? WHERE no=?", (status, lead_no))
    conn.commit()


def dialable_whatsapp(phone: str | None, country: str | None) -> str:
    """A full international number, or "" when we cannot build one.

    A bare national number is not a lesser attempt, it is a guaranteed failure — and
    docs/59 would record that failure as "this number has no WhatsApp", burning a good
    number permanently. So the two specs only work together (docs/62 R1).
    """
    # The `WA:` label says which number WhatsApp is on. Taking the first half instead
    # dialed six companies' landlines, and docs/59 would write each failure down as
    # "no WhatsApp" and drop them from the queue for good (docs/83 R1).
    _voice, raw = split_numbers(phone)
    if not raw:
        return ""
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return ""
    if raw.lstrip().startswith("+"):
        # A written +1 does not exempt a switchboard from being a switchboard.
        if _is_toll_free(digits):
            return ""
        return digits if 8 <= len(digits) <= 15 else ""
    code = _CALLING_CODES.get(str(country or "").strip().lower())
    if not code:
        return ""
    if code == "1":
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        if len(digits) != 10:
            return ""
    national = digits[len(code):] if digits.startswith(code) and len(digits) > 10 else digits
    full = code + national
    if _is_toll_free(full):
        return ""
    return full if 8 <= len(full) <= 15 else ""


def _target(channel: str, lead: dict) -> str:
    raw = lead[_CONTACT_COL[channel]]
    if channel == "whatsapp":
        return dialable_whatsapp(raw, lead.get("country"))
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
              AND NOT (? = 'whatsapp' AND COALESCE(l.whatsapp_status, '') = 'none')
              AND l.no NOT IN (
                  SELECT lead_no FROM send_log
                  WHERE date(sent_at, 'localtime')=date('now', 'localtime'))
              AND l.no NOT IN ({recontact.BLOCKED_SQL})
            ORDER BY l.no""",
        [*lead_nos, channel, *recontact.blocked_params(channel)],
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


def send_prepared(conn, items: list[dict], engine, image: str | None = None,
                  campaign: str | None = None,
                  on_progress: Callable[[int, int], None] | None = None) -> dict:
    """Send messages that were written one per company, on the same rails as a campaign.

    `send_channel_campaign` sends one template to many leads. The daily social queue is
    the other shape — a different sentence for each company — but it must keep the same
    daily cap, the same pacing, the same bookkeeping and the same case image, so this
    reuses all of it rather than opening a second way to reach a customer.

    Items: {lead_no, channel, target, body, variant?}. Order is preserved, and the
    pacing delay is taken per item's own channel, because a mixed batch alternates
    between them. `variant` rides along so a DM can name its copy version (docs/90 R2).

    Returns `sent_ids` — which items actually went — because a count cannot answer a
    question about identity. Callers used to slice `items[:sent]`, which silently
    assumes the successes are the ones at the front; on 09-04 the first item failed and
    the second succeeded, so a message that never went out was marked sent and the one
    that did stayed queued (docs/102 R1).
    """
    today = datetime.date.today().isoformat()
    sent_ids: list = []
    sent = failed = deferred = 0
    errors: list[dict] = []
    used = {c: sent_today(conn, c) for c in DAILY_CAP}
    total = len(items)
    for i, item in enumerate(items, 1):
        channel = item["channel"]
        if used.get(channel, 0) >= DAILY_CAP.get(channel, MAX_BATCH):
            deferred += 1
            continue
        try:
            engine.send_message(channel, item["target"], item["body"], image)
            _mark_messaged(conn, item["lead_no"], channel, today)
            campaigns.log_send(conn, item["lead_no"], channel,
                               campaign or campaigns.default_label(channel),
                               body=item["body"], variant=item.get("variant"))
            used[channel] = used.get(channel, 0) + 1
            _note_whatsapp_result(conn, item["lead_no"], channel, None)
            sent += 1
            if item.get("id") is not None:
                sent_ids.append(item["id"])
        except Exception as exc:  # noqa: BLE001
            failed += 1
            _note_whatsapp_result(conn, item["lead_no"], channel, str(exc))
            errors.append({"no": item["lead_no"], "channel": channel, "error": str(exc)})
        if on_progress:
            on_progress(i, total)
        if i < total:
            lo, hi = DEFAULT_DELAY.get(channel, (60, 90))
            if hi > 0:
                time.sleep(random.randint(lo, hi))
    return {"sent": sent, "failed": failed, "deferred": deferred, "errors": errors,
            "sent_ids": sent_ids}


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
            rendered = render(message, lead)
            engine.send_message(channel, _target(channel, lead), rendered, image)
            _mark_messaged(conn, lead["no"], channel, today)
            campaigns.log_send(conn, lead["no"], channel, label, body=rendered)
            _note_whatsapp_result(conn, lead["no"], channel, None)
            sent += 1
        except Exception as exc:  # noqa: BLE001
            failed += 1
            _note_whatsapp_result(conn, lead["no"], channel, str(exc))
            errors.append({"no": lead["no"], "error": str(exc)})
        if on_progress:
            on_progress(i, len(targets))
        if i < len(targets):
            lo, hi = delay_range
            if hi > 0:
                time.sleep(random.randint(lo, hi))
    return {"sent": sent, "failed": failed, "deferred": deferred,
            "skipped": len(lead_nos) - len(all_targets), "errors": errors}
