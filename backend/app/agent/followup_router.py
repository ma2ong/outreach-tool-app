"""Reconnect contacted no-reply leads to the approved email follow-up sequence.

This module does not send. It only restores ownership by the existing sequence engine.
The existing autosend gate, bounce protection, daily budget, batch cap and reply/do-not-
contact checks remain the only path that can actually deliver the next email.
"""
from __future__ import annotations

import datetime as dt

from app import recheck, seeds, sequences

STANDARD_SEQUENCE = {
    "en": "冷邮件 3 步跟进（英语）",
    "ko": "冷邮件 3 步跟进（韩语）",
}
MAX_COLD_EMAIL_TOUCHES = 3


def _language(country: str | None) -> str:
    return "ko" if str(country or "").strip().lower() in {
        "south korea", "korea", "republic of korea", "대한민국",
    } else "en"


def _standard_sequence(conn, lang: str) -> dict | None:
    name = STANDARD_SEQUENCE[lang]
    row = conn.execute(
        "SELECT id,name,channel,active FROM sequences WHERE name=?", (name,)
    ).fetchone()
    if row is None:
        # The copy is source-controlled and already used by the product's one-click
        # starter setup. Creating the missing standard sequence does not enable sending;
        # autosend keeps its separate human-controlled gate.
        seeds.seed_sequences(conn)
        row = conn.execute(
            "SELECT id,name,channel,active FROM sequences WHERE name=?", (name,)
        ).fetchone()
    return dict(row) if row else None


def _email_touch_state(conn, lead_no: int) -> dict:
    row = conn.execute(
        "SELECT COALESCE(SUM(COALESCE(touch_count,0)),0) touches,"
        " MAX(message_sent_date) last_touch"
        " FROM outreach WHERE lead_no=? AND channel='email'"
        " AND status IN ('messaged','replied')",
        (lead_no,),
    ).fetchone()
    return {"touches": int(row["touches"] or 0), "last_touch": row["last_touch"]}


def _retire_to_recheck(conn, lead_no: int, reason: str) -> dict:
    due = recheck.schedule_after_send(conn, lead_no)
    return {"status": "retired", "reason": reason, "recheck_due": due}


def continue_no_reply(conn, lead_no: int) -> dict:
    """Arrange the next approved email step, or deliberately stop cold follow-up.

    One prior email -> step 2. Two prior emails -> final step 3. Three or more -> no
    further cold email. Social-only contact is not silently converted into an email
    campaign because that would be a new channel initiation, not a follow-up.
    """
    lead = conn.execute(
        "SELECT no,country,website,email,email_status,do_not_contact FROM leads WHERE no=?",
        (lead_no,),
    ).fetchone()
    if not lead:
        return {"status": "retired", "reason": "lead_missing"}
    if lead["do_not_contact"]:
        return {"status": "retired", "reason": "do_not_contact"}
    if conn.execute(
        "SELECT 1 FROM outreach WHERE lead_no=? AND channel='email'"
        " AND (status='replied' OR reply_received=1) LIMIT 1", (lead_no,),
    ).fetchone():
        return {"status": "retired", "reason": "already_replied"}

    state = _email_touch_state(conn, lead_no)
    touches = state["touches"]
    if touches <= 0:
        return _retire_to_recheck(conn, lead_no, "no_prior_email")
    if touches >= MAX_COLD_EMAIL_TOUCHES:
        return _retire_to_recheck(conn, lead_no, "cold_email_cap_reached")
    if not lead["email"] or lead["email_status"] == "invalid":
        return {"status": "blocked", "reason": "no_sendable_email"}

    seq = _standard_sequence(conn, _language(lead["country"]))
    if not seq:
        return {"status": "blocked", "reason": "standard_sequence_missing"}
    if not seq["active"]:
        # Respect an explicit user decision to disable this sequence.
        return {"status": "blocked", "reason": "standard_sequence_disabled"}

    sid = seq["id"]
    target_step = touches  # touch 1 -> step_order 1; touch 2 -> step_order 2
    step = conn.execute(
        "SELECT step_order,day_offset FROM sequence_steps"
        " WHERE sequence_id=? AND step_order=?",
        (sid, target_step),
    ).fetchone()
    if not step:
        return _retire_to_recheck(conn, lead_no, "no_matching_followup_step")

    existing = conn.execute(
        "SELECT id,status,current_step,next_due_date FROM sequence_enrollments"
        " WHERE lead_no=? AND sequence_id=?", (lead_no, sid),
    ).fetchone()
    if existing:
        existing = dict(existing)
        if existing["status"] == "active":
            return {"status": "owned", "reason": "already_active", "enrollment_id": existing["id"]}
        if existing["status"] == "blocked":
            sequences.reopen_sendable(conn)
            refreshed = conn.execute(
                "SELECT id,status FROM sequence_enrollments WHERE id=?", (existing["id"],)
            ).fetchone()
            if refreshed and refreshed["status"] == "active":
                return {"status": "owned", "reason": "reopened", "enrollment_id": existing["id"]}
            return {"status": "blocked", "reason": "existing_enrollment_blocked"}
        # Never resurrect completed/replied/manual-stopped history. A completed standard
        # sequence means the cold-email budget was already spent.
        return _retire_to_recheck(conn, lead_no, f"existing_enrollment_{existing['status']}")

    today = dt.date.today()
    enrolled_at = (today - dt.timedelta(days=int(step["day_offset"] or 0))).isoformat()
    cur = conn.execute(
        "INSERT INTO sequence_enrollments"
        "(lead_no,sequence_id,current_step,status,enrolled_at,next_due_date)"
        " VALUES (?,?,?,'active',?,?)",
        (lead_no, sid, target_step, enrolled_at, today.isoformat()),
    )
    conn.commit()
    return {
        "status": "owned",
        "reason": "followup_enrolled",
        "enrollment_id": cur.lastrowid,
        "sequence_id": sid,
        "step_order": target_step,
        "touches": touches,
    }
