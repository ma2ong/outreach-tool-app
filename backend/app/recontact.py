"""When a company we already wrote to becomes a cold prospect again (docs/73).

`eligible_leads` used to read `status IN ('messaged','replied')` and exclude those leads
forever. That is right for a reply and wrong for everything else: 329 of the companies it
was holding back were last written to more than a year ago — the oldest 1421 days, nearly
four years, imported from the Xiaoman CRM. A company that has not heard from us since
2022 is not an existing contact, it is a fresh lead, and the pool looked empty because of
bookkeeping rather than because it was.

This module owns one decision and nothing else: *may a cold approach go to this lead on
this channel again?* It is deliberately a SQL fragment rather than a Python predicate, so
the callers keep filtering in one query instead of loading the whole book into memory.
"""
from __future__ import annotations

COOLDOWN_DAYS = 180

# The lead numbers a cold approach on `channel` must skip.
#
# The base set is the same one the callers excluded before (`messaged`/`replied`), so
# nothing that was previously sendable becomes blocked. Only the way out is new.
#
#   replied            a reply is a relationship, not a lead; never cold-pitch it again
#   stage won/lost     someone who has paid must never receive an introduction (docs/54
#                      R1), and someone Allen has written off should not be revived by a
#                      calendar. One `won` lead really is in the re-approachable set.
#   no send date       we do not know when it went out, so we do not gamble
#   within cooldown    a conversation that may still be live
#
# `do_not_contact` and `email_status='invalid'` — which is where all 36 bounced addresses
# already sit — are enforced by the callers' own WHERE clauses and stay enforced.
BLOCKED_SQL = """
    SELECT o.lead_no FROM outreach o JOIN leads l ON l.no = o.lead_no
     WHERE o.channel = ?
       AND o.status IN ('messaged', 'replied')
       AND (o.status = 'replied'
            OR l.stage IN ('won', 'lost')
            OR o.message_sent_date IS NULL
            OR o.message_sent_date > date('now', ?))
"""

# Bind after the channel, wherever BLOCKED_SQL is inlined.
CUTOFF = f"-{COOLDOWN_DAYS} days"


def blocked_params(channel: str) -> list:
    return [channel, CUTOFF]


def reapproachable(conn, channel: str = "email") -> list[int]:
    """Leads that were written to long enough ago to be worth approaching again.

    Used to top up the day's sending when the follow-up queue is thinner than the budget
    (docs/73 R3); relaxing eligibility alone changes nothing, because autosend only ever
    sends due sequence steps.
    """
    col = {"email": "email", "whatsapp": "phone",
           "instagram": "instagram", "facebook": "facebook"}[channel]
    rows = conn.execute(
        f"""SELECT o.lead_no FROM outreach o JOIN leads l ON l.no = o.lead_no
             WHERE o.channel = ?
               AND o.status = 'messaged'
               AND o.message_sent_date IS NOT NULL
               AND o.message_sent_date <= date('now', ?)
               AND (l.stage IS NULL OR l.stage NOT IN ('won', 'lost'))
               AND COALESCE(l.do_not_contact, 0) = 0
               AND l.{col} IS NOT NULL AND l.{col} != ''
               {"AND (l.email_status IS NULL OR l.email_status != 'invalid')"
                if channel == "email" else ""}
             ORDER BY o.message_sent_date, o.lead_no""",
        [channel, CUTOFF]).fetchall()
    return [r["lead_no"] for r in rows]
