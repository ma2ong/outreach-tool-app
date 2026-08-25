"""Preview-first repair for historical email autoresponders misfiled as human replies.

PR #13 prevents new misclassification. This module repairs old rows conservatively:
only current autoresponder candidates with strong evidence (noreply sender or an already
stored duplicate `kind='auto'`) are eligible for --apply. It is intentionally not wired
into startup or the Sales Worker.

Run:
    python -m app.fix_historical_auto_replies
    python -m app.fix_historical_auto_replies --apply
"""
from __future__ import annotations

import datetime as dt
import sys

from app import replies
from app.db import connect
from app.main_deps import DB_PATH


def _norm(value) -> str:
    return str(value or "").strip().lower()


def _duplicate_auto_id(conn, row) -> int | None:
    duplicate = conn.execute(
        "SELECT id FROM inbox_messages"
        " WHERE lead_no=? AND channel=? AND kind='auto' AND id!=?"
        " AND lower(COALESCE(from_addr,''))=?"
        " AND COALESCE(subject,'')=? AND COALESCE(received_at,'')=?"
        " ORDER BY id LIMIT 1",
        (row["lead_no"], row["channel"], row["id"], _norm(row["from_addr"]),
         row["subject"] or "", row["received_at"] or ""),
    ).fetchone()
    return int(duplicate["id"]) if duplicate else None


def _scan(conn) -> list[dict]:
    items: list[dict] = []
    rows = conn.execute(
        "SELECT id,lead_no,channel,kind,from_addr,subject,body,received_at"
        " FROM inbox_messages WHERE channel='email' AND kind='reply' ORDER BY id"
    ).fetchall()
    for row in rows:
        message = dict(row)
        if not replies.is_auto_reply_message(message):
            continue
        duplicate_auto_id = _duplicate_auto_id(conn, row)
        noreply = replies.is_no_reply_address(row["from_addr"])
        strong = bool(noreply or duplicate_auto_id)
        reasons = []
        if noreply:
            reasons.append("noreply_sender")
        if duplicate_auto_id:
            reasons.append("duplicate_auto")
        if not reasons:
            reasons.append("text_pattern_only")
        lead = conn.execute(
            "SELECT company_en,stage FROM leads WHERE no=?", (row["lead_no"],)
        ).fetchone()
        items.append({
            "inbox_id": int(row["id"]),
            "lead_no": int(row["lead_no"]),
            "company_en": lead["company_en"] if lead else None,
            "stage": lead["stage"] if lead else None,
            "channel": row["channel"],
            "from_addr": row["from_addr"],
            "subject": row["subject"],
            "received_at": row["received_at"],
            "duplicate_auto_id": duplicate_auto_id,
            "strong": strong,
            "evidence": reasons,
        })
    return items


def _merge_message_to_auto(conn, item: dict) -> None:
    """Keep the historical reply id so its audit references stay traceable.

    If PR #13 already stored the same message as auto, merge its read/handled state into
    the old row, delete the duplicate, then reclassify the old row. Delete-before-update
    is required because the inbox unique index includes `kind`.
    """
    inbox_id = item["inbox_id"]
    duplicate_id = item.get("duplicate_auto_id")
    if duplicate_id:
        duplicate = conn.execute(
            "SELECT is_read,handled_at FROM inbox_messages WHERE id=?", (duplicate_id,)
        ).fetchone()
        current = conn.execute(
            "SELECT is_read,handled_at FROM inbox_messages WHERE id=?", (inbox_id,)
        ).fetchone()
        if duplicate and current:
            conn.execute(
                "UPDATE inbox_messages SET is_read=?, handled_at=? WHERE id=?",
                (max(int(current["is_read"] or 0), int(duplicate["is_read"] or 0)),
                 current["handled_at"] or duplicate["handled_at"], inbox_id),
            )
        conn.execute("DELETE FROM inbox_messages WHERE id=?", (duplicate_id,))
    conn.execute(
        "UPDATE inbox_messages SET kind='auto', contact_id=NULL WHERE id=? AND kind='reply'",
        (inbox_id,),
    )


def _cancel_reply_task(conn, inbox_id: int, now: str) -> int:
    row = conn.execute(
        "SELECT id,note FROM activities WHERE source='reply' AND source_ref=?",
        (f"inbox:{inbox_id}",),
    ).fetchone()
    if not row:
        return 0
    reason = "Historical autoresponder repair: this inbox message is machine-generated."
    note = (row["note"] or "").strip()
    if reason not in note:
        note = f"{note}\n{reason}".strip()
    cur = conn.execute(
        "UPDATE activities SET status='cancelled',completed_at=NULL,note=?,updated_at=? WHERE id=?",
        (note, now, row["id"]),
    )
    return cur.rowcount


def _remove_machine_contacts(conn, item: dict) -> int:
    sender = _norm(item.get("from_addr"))
    if not sender or not replies.is_no_reply_address(sender):
        return 0
    rows = conn.execute(
        "SELECT id FROM contacts WHERE lead_no=? AND lower(COALESCE(email,''))=?"
        " AND source='reply' AND is_primary=0",
        (item["lead_no"], sender),
    ).fetchall()
    removed = 0
    for row in rows:
        conn.execute("UPDATE inbox_messages SET contact_id=NULL WHERE contact_id=?", (row["id"],))
        removed += conn.execute("DELETE FROM contacts WHERE id=?", (row["id"],)).rowcount
    return removed


def _has_real_email_reply(conn, lead_no: int) -> bool:
    return conn.execute(
        "SELECT 1 FROM inbox_messages WHERE lead_no=? AND channel='email'"
        " AND kind IN ('reply','unsubscribe') LIMIT 1", (lead_no,)
    ).fetchone() is not None


def _has_send_evidence(conn, lead_no: int, outreach_row) -> bool:
    if int(outreach_row["touch_count"] or 0) > 0 or outreach_row["message_sent_date"]:
        return True
    return conn.execute(
        "SELECT 1 FROM send_log WHERE lead_no=? AND channel='email' LIMIT 1", (lead_no,)
    ).fetchone() is not None


def _revert_false_reply_state(conn, lead_no: int, tomorrow: str) -> tuple[int, int, str | None]:
    """Return (outreach_reverted, sequence_reopened, retained_reason)."""
    if _has_real_email_reply(conn, lead_no):
        return 0, 0, "other_human_reply_exists"
    outreach = conn.execute(
        "SELECT status,touch_count,message_sent_date,reply_received FROM outreach"
        " WHERE lead_no=? AND channel='email'", (lead_no,)
    ).fetchone()
    if not outreach or outreach["status"] != "replied":
        return 0, 0, "outreach_not_replied"
    if int(outreach["reply_received"] or 0) != 0:
        return 0, 0, "reply_received_flag_set"
    if not _has_send_evidence(conn, lead_no, outreach):
        return 0, 0, "no_outbound_send_evidence"

    reverted = conn.execute(
        "UPDATE outreach SET status='messaged',reply_received=0"
        " WHERE lead_no=? AND channel='email' AND status='replied'",
        (lead_no,),
    ).rowcount
    reopened = conn.execute(
        "UPDATE sequence_enrollments SET status='active',"
        " next_due_date=CASE WHEN COALESCE(next_due_date,'') < ? THEN ? ELSE next_due_date END"
        " WHERE lead_no=? AND status='replied'"
        " AND sequence_id IN (SELECT id FROM sequences WHERE channel='email')",
        (tomorrow, tomorrow, lead_no),
    ).rowcount
    return reverted, reopened, None


def _sync_activity_lead(conn, lead_no: int) -> None:
    """Keep legacy next_action/follow_up_date aligned after cancelling a false reply task."""
    row = conn.execute(
        "SELECT title,due_at FROM activities WHERE lead_no=? AND status='open'"
        " ORDER BY due_at IS NULL,due_at,"
        " CASE priority WHEN 'high' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END,id LIMIT 1",
        (lead_no,),
    ).fetchone()
    conn.execute(
        "UPDATE leads SET next_action=?,follow_up_date=? WHERE no=?",
        (row["title"] if row else None, row["due_at"] if row else None, lead_no),
    )


def run(conn, *, apply: bool = False, today: dt.date | None = None) -> dict:
    """Preview candidates or conservatively repair the strong-evidence subset."""
    items = _scan(conn)
    strong_items = [item for item in items if item["strong"]]
    result = {
        "candidates": len(items),
        "strong": len(strong_items),
        "manual_review": len(items) - len(strong_items),
        "applied": 0,
        "outreach_reverted": 0,
        "sequences_reopened": 0,
        "reply_tasks_cancelled": 0,
        "machine_contacts_removed": 0,
        "items": items,
        "state_retained": [],
    }
    if not apply or not strong_items:
        return result

    day = today or dt.date.today()
    tomorrow = (day + dt.timedelta(days=1)).isoformat()
    now = dt.datetime.now(dt.UTC).isoformat()
    affected_leads: set[int] = set()

    with conn:
        for item in strong_items:
            _merge_message_to_auto(conn, item)
            result["reply_tasks_cancelled"] += _cancel_reply_task(conn, item["inbox_id"], now)
            result["machine_contacts_removed"] += _remove_machine_contacts(conn, item)
            affected_leads.add(item["lead_no"])
            result["applied"] += 1

        for lead_no in sorted(affected_leads):
            reverted, reopened, retained = _revert_false_reply_state(conn, lead_no, tomorrow)
            result["outreach_reverted"] += reverted
            result["sequences_reopened"] += reopened
            if retained:
                result["state_retained"].append({"lead_no": lead_no, "reason": retained})
            message = "历史自动回复误判已修复：机器邮件已从真人 reply 更正为 auto。"
            if reverted:
                message += " Email outreach 已恢复为 messaged；被误停的邮件序列已安全恢复。"
            else:
                message += " 因存在其他回复/证据不足，replied 状态与序列未自动回退。"
            message += " leads.stage 保留原值，避免覆盖可能的人工判断。"
            conn.execute(
                "INSERT INTO notes(lead_no,created_at,text) VALUES (?,?,?)",
                (lead_no, now, message),
            )
            _sync_activity_lead(conn, lead_no)
    return result


def _print(result: dict, *, applied: bool) -> None:
    print(f"candidates={result['candidates']} strong={result['strong']} manual_review={result['manual_review']}")
    for item in result["items"]:
        mode = "AUTO-FIX" if item["strong"] else "REVIEW"
        print(
            f"[{mode}] inbox#{item['inbox_id']} lead#{item['lead_no']} "
            f"{item.get('company_en') or ''} <{item.get('from_addr') or ''}> "
            f"evidence={','.join(item['evidence'])}"
        )
    if not applied:
        print("Preview only. No data changed. Add --apply to repair strong-evidence rows.")
        return
    print(
        "applied={applied} outreach_reverted={outreach_reverted} "
        "sequences_reopened={sequences_reopened} reply_tasks_cancelled={reply_tasks_cancelled} "
        "machine_contacts_removed={machine_contacts_removed}".format(**result)
    )
    for row in result["state_retained"]:
        print(f"[STATE RETAINED] lead#{row['lead_no']} reason={row['reason']}")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    apply = "--apply" in sys.argv
    conn = connect(DB_PATH)
    try:
        result = run(conn, apply=apply)
    finally:
        conn.close()
    _print(result, applied=apply)


if __name__ == "__main__":
    main()
