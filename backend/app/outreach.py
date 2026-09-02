import datetime
import random
import time
from typing import Callable

from app import campaigns, message_guard, recontact
from app.personalize import render

# Email needs the same anti-ban discipline as WhatsApp/Instagram. A single mailbox that
# suddenly sends hundreds of cold emails in a day lands in spam and can get limited —
# which would waste every lead we found. Configure sender mailboxes to raise the daily
# ceiling (their daily_cap values sum up); DAILY_CAP applies to the fallback mailbox only.
DAILY_CAP = 40
# The per-run ceiling applies to every path, so it — not daily_cap — is what actually
# decided the day's volume: a 40-a-day mailbox was sending 30, because autosend makes one
# run. Raised to 60 on a company domain with real sending history behind it; at 16-28
# seconds a message that is a ~20 minute run, which is a person working through a list
# rather than a burst. Watch the bounce rate rather than this number: the readiness panel
# flags it, and the last domain was lost at 11.4%.
MAX_BATCH = 60

# At least a minute between letters. 16-28 seconds is a rate no one types at, and a
# receiving server that clocks a steady sub-minute cadence from one address has every
# reason to file the next one as bulk — which costs far more than the extra hour a
# 60-message run now takes.
EMAIL_DELAY = (60, 110)


def sent_today(conn) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM outreach WHERE channel='email' AND status='messaged'"
        " AND message_sent_date = date('now')").fetchone()[0]


def remaining_today(conn) -> int:
    """How many emails may still go out today: the mailboxes' remaining capacity if
    rotation is configured, otherwise the single fallback Gmail's daily budget."""
    from app import mailboxes
    if mailboxes.has_active(conn):
        return mailboxes.total_remaining(conn)
    return max(0, DAILY_CAP - sent_today(conn))


def never_touched(conn, channel: str = "email") -> list[int]:
    """Companies in the book that have never been written to on this channel (docs/81).

    The sibling of `recontact.reapproachable`, and the pool that had no way in at all:
    `_top_up` only ever drew from companies already messaged, so 69 real prospects — most
    of them carrying a hook — sat in the book without a single letter. They arrived
    before importing enrolled anything (docs/54, and the discovery batches that predate
    `_enroll_imported`), so nothing was ever going to pick them up.

    Excludes exactly what `reapproachable` excludes; a customer who has already bought
    never enters a cold sequence.
    """
    col = {"email": "email", "whatsapp": "phone",
           "instagram": "instagram", "facebook": "facebook"}[channel]
    rows = conn.execute(
        f"""SELECT l.no FROM leads l
             WHERE COALESCE(l.do_not_contact, 0) = 0
               AND (l.stage IS NULL OR l.stage NOT IN ('won', 'lost'))
               AND l.{col} IS NOT NULL AND l.{col} != ''
               {"AND (l.email_status IS NULL OR l.email_status NOT IN ('invalid','bounced'))"
                if channel == "email" else ""}
               AND NOT EXISTS (SELECT 1 FROM outreach o
                                WHERE o.lead_no = l.no AND o.channel = ?
                                  AND o.status IN ('messaged', 'replied'))
               AND NOT EXISTS (SELECT 1 FROM sequence_enrollments e WHERE e.lead_no = l.no)
               -- docs/89 R2. Enrolling a company whose address has no provenance only
               -- parks a row that due_queue will refuse every morning.
               {"AND COALESCE(l.email_source,'') <> ''" if channel == "email" else ""}
             -- docs/81 R2, same rule as docs/80 R3: something specific to say goes first.
             ORDER BY CASE WHEN COALESCE(l.hook, '') = '' THEN 1 ELSE 0 END, l.no""",
        (channel,)).fetchall()
    return [r["no"] for r in rows]


def eligible_leads(conn, lead_nos: list[int], channel: str) -> list[dict]:
    if not lead_nos:
        return []
    placeholders = ",".join("?" * len(lead_nos))
    rows = conn.execute(
        f"""SELECT l.no, l.company_en, l.contact_name, l.country, l.city, l.email,
                   l.website, l.hook, l.brief FROM leads l
            WHERE l.no IN ({placeholders})
              AND l.email IS NOT NULL AND l.email != ''
              AND (l.email_status IS NULL OR l.email_status != 'invalid')
              AND COALESCE(l.do_not_contact, 0) = 0
              AND l.no NOT IN (
                  SELECT lead_no FROM send_log
                  WHERE date(sent_at, 'localtime')=date('now', 'localtime'))
              AND l.no NOT IN ({recontact.BLOCKED_SQL})
            ORDER BY l.no""",
        [*lead_nos, *recontact.blocked_params(channel)],
    ).fetchall()
    return [dict(r) for r in rows]


def _mark_messaged(conn, lead_no: int, date: str) -> None:
    from app import recheck, repository
    conn.execute(
        "INSERT INTO outreach(lead_no, channel, status, touch_count, message_sent_date)"
        " VALUES (?, 'email', 'messaged', 1, ?)"
        " ON CONFLICT(lead_no, channel) DO UPDATE SET"
        " status='messaged', touch_count=touch_count+1, message_sent_date=excluded.message_sent_date",
        (lead_no, date),
    )
    conn.commit()
    repository.advance_stage(conn, lead_no, "contacted")
    recheck.schedule_after_send(conn, lead_no)


def send_campaign(conn, lead_nos: list[int], subject: str, body: str,
                  attachment: str | None, sender: Callable[[str, str, str, str | None], None],
                  delay_range: tuple[int, int] = (16, 28), max_send: int | None = None,
                  campaign: str | None = None,
                  on_progress: Callable[[int, int], None] | None = None) -> dict:
    today = datetime.date.today().isoformat()
    label = campaign or campaigns.default_label("email")
    all_targets = eligible_leads(conn, lead_nos, "email")
    total_selected = len(lead_nos)
    # Cap the run by today's remaining budget AND the per-run batch limit; the rest is
    # deferred (still eligible tomorrow), never dropped.
    budget = remaining_today(conn) if max_send is None else max_send
    targets = all_targets[:min(budget, MAX_BATCH)]
    deferred = len(all_targets) - len(targets)
    sent = failed = held = 0
    errors: list[dict] = []
    holds: list[dict] = []
    for i, lead in enumerate(targets, 1):
        attempted_send = False
        try:
            rendered_subject = render(subject, lead)
            rendered_body = render(body, lead)
            verdict = message_guard.check(rendered_body, lead, subject=rendered_subject)
            if verdict.blocked:
                held += 1
                holds.append({"no": lead["no"], "reason": verdict.reason,
                              "detail": verdict.detail})
            else:
                attempted_send = True
                # Send the exact strings that passed the guard; never render a second time.
                sender(lead["email"], rendered_subject, rendered_body, attachment)
                _mark_messaged(conn, lead["no"], today)
                campaigns.log_send(conn, lead["no"], "email", label,
                                   subject=rendered_subject, body=rendered_body)
                sent += 1
        except Exception as exc:  # noqa: BLE001
            failed += 1
            errors.append({"no": lead["no"], "error": str(exc)})
        if on_progress:
            on_progress(i, len(targets))
        if attempted_send and i < len(targets):
            lo, hi = delay_range
            if hi > 0:
                time.sleep(random.randint(lo, hi))
    return {"sent": sent, "failed": failed, "deferred": deferred,
            "skipped": total_selected - len(all_targets), "errors": errors,
            "held": held, "holds": holds}