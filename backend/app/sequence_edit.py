"""Change a sequence step's copy from the UI, and see what it will become (docs/86).

Until now nothing about the outbound copy could be changed from the product. Both APIs
were create-and-delete, so a single word — Allen deleted "we build the panels ourselves"
twice in one day — meant editing Python, re-seeding and restarting. Seven rounds of that
happened on 09-02, and every round went through an agent.

Two things make an editor safe here rather than merely possible.

An edited step must survive the seeder. `seed_sequences.seed()` deletes and rewrites
every step each time it runs, which is right for copy the repo owns and wrong the moment
a person has touched it. `edited` marks the ones that are now the user's, and the seeder
leaves those sequences alone and says so.

And a step must be judged before it is stored, not after it is sent. `preview` renders
the text against a real lead and runs the same `message_guard` the sender runs, so the
seven limits, the price rule and the exit-line rule are answered while the editor is
still open.
"""
from __future__ import annotations

from app import message_guard
from app.personalize import render


def ensure_schema(conn) -> None:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(sequence_steps)")}
    if "edited" not in cols:
        conn.execute("ALTER TABLE sequence_steps ADD COLUMN edited INTEGER NOT NULL DEFAULT 0")
        conn.commit()


def _sample_lead(conn, sequence_id: int) -> dict:
    """Someone actually enrolled in this sequence, so the preview is a real letter.

    Falls back to any lead with a hook, then to a made-up one — a preview that renders
    nothing because the book is empty is worse than a preview of a plausible company.
    """
    for sql, args in (
        ("SELECT l.* FROM leads l JOIN sequence_enrollments e ON e.lead_no = l.no"
         " WHERE e.sequence_id = ? AND COALESCE(l.hook, '') != '' LIMIT 1", (sequence_id,)),
        ("SELECT * FROM leads WHERE COALESCE(hook, '') != '' LIMIT 1", ()),
    ):
        row = conn.execute(sql, args).fetchone()
        if row:
            return dict(row)
    return {"no": 0, "company_en": "Verum AV", "contact_name": "Sam", "city": "Austin",
            "website": "verumav.com", "country": "USA",
            "hook": "Saw the rental work you do around Austin."}


def preview(conn, sequence_id: int, step_order: int, subject: str | None,
            body: str) -> dict:
    """What this step will look like sent, and whether the guard would let it out."""
    lead = _sample_lead(conn, sequence_id)
    row = conn.execute("SELECT channel FROM sequences WHERE id=?", (sequence_id,)).fetchone()
    channel = (row["channel"] if row else "email") or "email"
    rendered_subject = render(subject or "", lead)
    rendered_body = render(body, lead)
    verdict = message_guard.check(
        rendered_body, lead, subject=rendered_subject, channel=channel,
        step_order=step_order)
    return {
        "lead_no": lead.get("no"),
        "company": lead.get("company_en"),
        "subject": rendered_subject,
        "body": rendered_body,
        "blocked": verdict.blocked,
        "reason": verdict.reason,
        "detail": verdict.detail,
    }


def update_step(conn, sequence_id: int, step_order: int, *, subject: str | None,
                body: str, day_offset: int | None = None,
                change_kind: str = "edit", rollback_of_id: int | None = None) -> dict:
    """Store the edit and mark the step as the user's. Refuses what the guard refuses.

    Refusing here rather than at send time is the whole point: a step the guard would
    block does not sit in the book looking fine until the day it silently holds a batch.
    """
    ensure_schema(conn)
    if not body.strip():
        raise ValueError("正文不能为空")
    result = preview(conn, sequence_id, step_order, subject, body)
    if result["blocked"]:
        raise ValueError(f"{result['detail']}")
    from app import copy_versions
    current = conn.execute(
        "SELECT subject,body,day_offset FROM sequence_steps"
        " WHERE sequence_id=? AND step_order=?", (sequence_id, step_order),
    ).fetchone()
    if not current:
        raise LookupError("这一步不存在")
    copy_versions.ensure_sequence_baseline(conn, sequence_id, step_order, current)
    sets = ["subject=?", "body=?", "edited=1"]
    args: list = [subject, body]
    if day_offset is not None:
        sets.append("day_offset=?")
        args.append(day_offset)
    args += [sequence_id, step_order]
    cur = conn.execute(
        f"UPDATE sequence_steps SET {', '.join(sets)}"
        " WHERE sequence_id=? AND step_order=?", args)
    if not cur.rowcount:
        raise LookupError("这一步不存在")
    copy_versions.record_sequence_step(
        conn, sequence_id, step_order, change_kind=change_kind,
        rollback_of_id=rollback_of_id,
    )
    conn.commit()
    return result


def edited_sequences(conn) -> set[int]:
    """Sequence ids holding at least one step a person changed."""
    ensure_schema(conn)
    return {r[0] for r in conn.execute(
        "SELECT DISTINCT sequence_id FROM sequence_steps WHERE edited=1")}


def revert(conn, sequence_id: int) -> int:
    """Hand a sequence back to the repo's copy: clear the marks so the seeder rewrites."""
    ensure_schema(conn)
    n = conn.execute(
        "UPDATE sequence_steps SET edited=0 WHERE sequence_id=?", (sequence_id,)).rowcount
    conn.commit()
    return n
