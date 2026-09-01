"""Would this copy actually go out? (docs/82)

Every template and every sequence step is judged by `message_guard` at send time, and a
refusal there is invisible until Allen picks that template and gets a block he cannot
explain. On 2026-08-31 twelve of the fourteen templates in the table were in that state:
three carried the exit lines docs/82 bans, the rest have no {company} anywhere and read
as impersonal. Nothing said so.

The test is deliberately the most favourable one: every piece of copy is rendered against
a lead with every field filled in. A refusal under those conditions is not "this lead is
thin", it is **this copy can never be sent to anyone**.
"""
from __future__ import annotations

import re

from app import message_guard
from app.personalize import render

# Everything a token could want. Anything refused against this lead is refused always.
_IDEAL_LEAD = {
    "no": 0,
    "company_en": "Verum Staging",
    "contact_name": "Sam Rivera",
    "country": "USA",
    "city": "Austin",
    "website": "verumstaging.com",
    "email": "sam@verumstaging.com",
    "hook": "Saw the rental and touring work you do around Austin.",
    "brief": 'The site mentions "rental" and "touring".',
    "tags": "租赁商,icp:rental",
}


def _judge(subject: str | None, body: str | None, channel: str,
           step_order: int = 0) -> dict | None:
    verdict = message_guard.check(
        render(body, _IDEAL_LEAD), _IDEAL_LEAD,
        subject=render(subject or "", _IDEAL_LEAD), channel=channel,
        step_order=step_order)
    if not verdict.blocked:
        return None
    return {"reason": verdict.reason, "detail": verdict.detail}


_STEP_IN_NAME = re.compile(r"第\s*(\d+)\s*封")


def _step_from_name(name: str | None) -> int:
    """0 unless the name says which letter it is. The templates are generated from the
    sequence and carry its numbering (docs/84 R1)."""
    m = _STEP_IN_NAME.search(str(name or ""))
    return max(int(m.group(1)) - 1, 0) if m else 0


def scan(conn) -> dict:
    """Which stored copy the guard would refuse, and why."""
    refused: list[dict] = []
    checked = 0

    for row in conn.execute("SELECT id, name, channel, subject, body FROM templates"):
        checked += 1
        # A template named 第2封 is a follow-up, and the personalisation rule is for the
        # first letter only. Scanning them all as openers reported four perfectly good
        # follow-ups as impersonal — they do not repeat the hook, and are not meant to.
        step = _step_from_name(row["name"])
        bad = _judge(row["subject"], row["body"], row["channel"] or "email", step)
        if bad:
            refused.append({"kind": "template", "id": row["id"], "name": row["name"],
                            "channel": row["channel"], **bad})

    for row in conn.execute(
            "SELECT st.id, s.name, s.channel, st.step_order, st.subject, st.body"
            " FROM sequence_steps st JOIN sequences s ON s.id = st.sequence_id"
            " WHERE s.active = 1"):
        checked += 1
        bad = _judge(
            row["subject"], row["body"], row["channel"] or "email", row["step_order"])
        if bad:
            refused.append({"kind": "sequence_step", "id": row["id"],
                            "name": f"{row['name']} 第 {row['step_order'] + 1} 步",
                            "channel": row["channel"], **bad})

    by_reason: dict[str, int] = {}
    for item in refused:
        by_reason[item["reason"]] = by_reason.get(item["reason"], 0) + 1
    return {"checked": checked, "refused": refused, "by_reason": by_reason}
