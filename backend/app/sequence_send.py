"""Send the due step of sequence enrollments, then advance them.

Unlike the one-off blast paths, this deliberately reaches leads that were already
messaged (that is the whole point of a follow-up step), so it does NOT use the
'messaged' exclusion. It still honours the browser-channel rate limits and daily
caps, and each item carries its own step message. After a successful send the
enrollment advances to its next step (or completes).

Automatic email sends additionally pass the autonomous follow-up decision layer. Manual
sequence sends keep human timing judgment and therefore do not silently inherit this
worth-now policy; both paths still pass all original delivery and message guards.
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
        # tags carries the customer type, which {fit} renders from. Without it the
        # type-aware sentence silently rendered empty in every real send while the
        # preview showed it — docs/67 R4.
        "SELECT no, company_en, contact_name, country, city, email, email_status,"
        " phone, instagram, website, hook, brief, tags"
        " FROM leads WHERE no=?", (lead_no,)).fetchone()
    return dict(r) if r else {}


def send_due(conn, enrollment_ids, *, sender=None, engine=None,
             email_delay=email_outreach.EMAIL_DELAY, channel_delay=None, image_default=None,
             on_progress=None, autonomous_quality: bool = False) -> dict:
    """Send current steps that are in today's safe due queue.

    `autonomous_quality=True` is reserved for the automatic email scheduler. It may
    delay/park/stop machine-owned enrollment state before anything reaches the sender.
    """
    due = {d["enrollment_id"]: d for d in sequences.due_queue(conn)}
    items = [due[i] for i in enrollment_ids if i in due]
    today = datetime.date.today().isoformat()
    sent = failed = deferred = held = delayed = stopped = 0
    errors: list[dict] = []
    holds: list[dict] = []
    decisions: list[dict] = []

    # Prepare optional evidence modules once per batch. This matters on SQLite: schema
    # migration checks and weak-campaign aggregation repeated 30 times add lock pressure
    # without changing any decision.
    followup_decision = None
    weak_sequence_ids: set[int] = set()
    if autonomous_quality and any(d["channel"] == "email" for d in items):
        from app.agent import followup_decision as _followup_decision
        from app.agent import oversight
        followup_decision = _followup_decision
        followup_decision.ensure_schema(conn)
        weak_sequence_ids = oversight.weak_sequence_ids(conn)

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

        if autonomous_quality and ch == "email" and followup_decision is not None:
            decision = followup_decision.evaluate(
                conn, d["enrollment_id"], _ensure=False,
                weak_sequence_ids=weak_sequence_ids,
            )
            decision = followup_decision.apply(conn, decision, _ensure=False)
            decisions.append({
                "enrollment_id": d["enrollment_id"], "lead_no": no,
                "action": decision["action"], "reason": decision["reason"],
                "next_due_date": decision.get("next_due_date"),
            })
            if decision["action"] == "delay":
                delayed += 1
                if on_progress:
                    on_progress(idx, total)
                continue
            if decision["action"] == "stop":
                stopped += 1
                if on_progress:
                    on_progress(idx, total)
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
                social_body = render(d["body"], lead)
                engine.send_message(ch, target, social_body,
                                    d.get("image") or image_default)
                co._mark_messaged(conn, no, ch, today)
                remaining[ch] -= 1
                batch_used[ch] += 1
                sent_this_item = True
            if sent_this_item:
                # Which experiment this letter belonged to (docs/69). Everything here
                # is already in hand; it was simply being discarded.
                from app.customer_types import customer_types
                types = customer_types(lead["tags"] if "tags" in lead.keys() else None)
                campaigns.log_send(
                    conn, no, ch, f"序列:{d['sequence_name']}",
                    subject=subject_text if ch == "email" else None,
                    body=body_text if ch == "email" else social_body,
                    variant=d["sequence_name"], step=int(d.get("step_order") or 0),
                    audience=types[0] if types else None,
                    market=lead["country"] if "country" in lead.keys() else None)
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
            "errors": errors, "held": held, "holds": holds,
            "delayed": delayed, "stopped": stopped,
            "followup_decisions": decisions}
