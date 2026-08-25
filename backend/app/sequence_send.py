"""Send the due step of sequence enrollments, then advance them.

Unlike the one-off blast paths, this deliberately reaches leads that were already
messaged (that is the whole point of a follow-up step), so it does NOT use the
'messaged' exclusion. It still honours the browser-channel rate limits and daily
caps, and each item carries its own step message. After a successful send the
enrollment advances to its next step (or completes).
"""
import datetime
import random
import time

from app import campaigns
from app import channel_outreach as co
from app import message_guard
from app import outreach as email_outreach
from app import sequences
from app.personalize import render


def _contact(conn, lead_no: int) -> dict:
    r = conn.execute(
        "SELECT no, company_en, contact_name, country, city, email, email_status,"
        " phone, instagram, website, hook, brief"
        " FROM leads WHERE no=?", (lead_no,)).fetchone()
    return dict(r) if r else {}


def send_due(conn, enrollment_ids, *, sender=None, engine=None,
             email_delay=(16, 28), channel_delay=None, image_default=None,
             on_progress=None) -> dict:
    """Send the current step for the given enrollments (must be in today's due queue)."""
    due = {d["enrollment_id"]: d for d in sequences.due_queue(conn)}
    items = [due[i] for i in enrollment_ids if i in due]
    today = datetime.date.today().isoformat()
    sent = failed = deferred = held = 0
    errors: list[dict] = []
    holds: list[dict] = []

    # Every channel is capped per day and per batch — email included (a 266-lead due
    # queue sent in one go from one Gmail is a spam-folder event).
    remaining = {ch: max(0, co.DAILY_CAP[ch] - co.sent_today(conn, ch)) for ch in co.DAILY_CAP}
    remaining["email"] = email_outreach.remaining_today(conn)
    batch_used = {ch: 0 for ch in remaining}
    max_batch = dict.fromkeys(co.DAILY_CAP, co.MAX_BATCH)
    max_batch["email"] = email_outreach.MAX_BATCH

    total = len(items)
    for idx, d in enumerate(items, 1):
        ch, no = d["channel"], d["lead_no"]
        lead = _contact(conn, no)
        if remaining.get(ch, 0) <= 0 or batch_used.get(ch, 0) >= max_batch.get(ch, 0):
            deferred += 1
            continue
        attempted_send = False
        sent_this_item = False
        try:
            if ch == "email":
                to = lead.get("email")
                if not to or lead.get("email_status") == "invalid":
                    deferred += 1
                    continue
                subject_text = render(d.get("subject"), lead)
                body_text = render(d["body"], lead)
                verdict = message_guard.check(
                    body_text, lead, subject=subject_text,
                    step_order=d.get("step_order", 0),
                )
                if verdict.blocked:
                    held += 1
                    holds.append({"no": no, "reason": verdict.reason,
                                  "detail": verdict.detail,
                                  "enrollment_id": d["enrollment_id"]})
                else:
                    attempted_send = True
                    sender(to, subject_text, body_text, d.get("image") or image_default)
                    email_outreach._mark_messaged(conn, no, today)
                    remaining["email"] -= 1
                    batch_used["email"] += 1
                    sent_this_item = True
            else:
                target = co._target(ch, lead)
                if not target:
                    deferred += 1
                    continue
                attempted_send = True
                engine.send_message(ch, target, render(d["body"], lead),
                                    d.get("image") or image_default)
                co._mark_messaged(conn, no, ch, today)
                remaining[ch] -= 1
                batch_used[ch] += 1
                sent_this_item = True
            if sent_this_item:
                campaigns.log_send(conn, no, ch, f"序列:{d['sequence_name']}")
                sequences.advance_enrollment(conn, d["enrollment_id"])
                sent += 1
        except Exception as exc:  # noqa: BLE001
            failed += 1
            errors.append({"no": no, "error": str(exc)})
        if on_progress:
            on_progress(idx, total)
        if attempted_send and idx < total:
            lo, hi = channel_delay or (co.DEFAULT_DELAY.get(ch, (0, 0)) if ch != "email" else email_delay)
            if hi > 0:
                time.sleep(random.randint(lo, hi))
    return {"sent": sent, "failed": failed, "deferred": deferred,
            "errors": errors, "held": held, "holds": holds}
