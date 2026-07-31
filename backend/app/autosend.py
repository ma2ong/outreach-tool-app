"""Automatic daily sending of EMAIL sequence follow-ups.

Why: 266 leads sat enrolled for three days with zero sends — the tool was ready but
the daily 'log in, tick, click send' never happened. Automation is the fix, and for
email it is safe: the anti-ban line ('manual send only') exists for WhatsApp/Instagram
platform ToS, not email. Cold-email risk is deliverability, controlled by the daily
cap / batch size / random pacing that the send path enforces regardless of who
triggers it. WA/IG/FB stay strictly manual.

Mechanics: a background thread wakes every few minutes; the first wake-up inside the
send window (09:00–20:00 local) on a day that hasn't run yet sends the due email
steps within today's budget. PC off all day -> it simply runs on next boot.
"""
import datetime as _dt
import threading
import time

from app import settings

WINDOW = (9, 20)          # local hours within which the daily run may fire
CHECK_SECONDS = 300       # scheduler wake-up interval

_K_ENABLED = "autosend_enabled"
_K_LAST_DATE = "autosend_last_date"
_K_LAST_RESULT = "autosend_last_result"


def enabled(conn) -> bool:
    return settings.get(conn, _K_ENABLED, "0") == "1"


def set_enabled(conn, on: bool) -> None:
    settings.set_value(conn, _K_ENABLED, "1" if on else "0")


def preview(conn) -> dict:
    from app import outreach, sequences
    due = sequences.due_queue(conn, "email")
    sendable = [d for d in due if conn.execute(
        "SELECT 1 FROM leads WHERE no=? AND email IS NOT NULL AND email != ''"
        " AND COALESCE(email_status, '') != 'invalid'",
        (d["lead_no"],),
    ).fetchone()]
    oldest = conn.execute(
        "SELECT MIN(e.next_due_date) AS oldest FROM sequence_enrollments e"
        " JOIN sequences s ON s.id=e.sequence_id"
        " WHERE e.status='active' AND s.channel='email' AND e.next_due_date <= date('now')"
    ).fetchone()["oldest"]
    return {
        "due": len(due),
        "sendable": len(sendable),
        "will_send": min(len(sendable), outreach.remaining_today(conn), outreach.MAX_BATCH),
        "oldest_due": oldest,
    }


def status(conn) -> dict:
    return {"enabled": enabled(conn),
            "last_date": settings.get(conn, _K_LAST_DATE) or None,
            "last_result": settings.get(conn, _K_LAST_RESULT) or None,
            "preview": preview(conn)}


def should_run(conn, now: _dt.datetime | None = None) -> bool:
    """Once per day, inside the window, only when enabled."""
    now = now or _dt.datetime.now()
    if not enabled(conn):
        return False
    if not (WINDOW[0] <= now.hour < WINDOW[1]):
        return False
    return settings.get(conn, _K_LAST_DATE) != now.date().isoformat()


def run_once(conn, sender, image_default: str | None, now: _dt.datetime | None = None,
             email_delay=(16, 28)) -> dict:
    """Send today's due EMAIL steps within budget and record the outcome.
    Marks the day as done even on failure — retrying a failing send path every five
    minutes all day would hammer the SMTP account, which is its own red flag."""
    from app import sequence_send, sequences
    now = now or _dt.datetime.now()
    settings.set_value(conn, _K_LAST_DATE, now.date().isoformat())
    due_ids = [d["enrollment_id"] for d in sequences.due_queue(conn, "email")]
    if not due_ids:
        settings.set_value(conn, _K_LAST_RESULT, f"{now:%m-%d %H:%M} 无到期邮件跟进")
        return {"sent": 0, "failed": 0, "deferred": 0}
    try:
        res = sequence_send.send_due(
            conn, due_ids, sender=sender, image_default=image_default,
            email_delay=email_delay,
        )
    except Exception as exc:  # noqa: BLE001
        settings.set_value(conn, _K_LAST_RESULT, f"{now:%m-%d %H:%M} 运行失败：{str(exc)[:120]}")
        return {"sent": 0, "failed": len(due_ids), "deferred": 0}
    note = f"{now:%m-%d %H:%M} 自动发送：成功 {res['sent']}，失败 {res['failed']}"
    if res.get("deferred"):
        note += f"，额度外延后 {res['deferred']}（明天继续）"
    settings.set_value(conn, _K_LAST_RESULT, note)
    return res


def scheduler_loop(db_path: str) -> None:
    """Daemon thread: check every CHECK_SECONDS whether today's run is owed."""
    from app.db import connect
    from app.api import send as send_api
    while True:
        try:
            conn = connect(db_path)
            try:
                if should_run(conn):
                    run_once(conn, send_api.pick_sender(conn), send_api.DEFAULT_ATTACHMENT)
            finally:
                conn.close()
        except Exception:  # noqa: BLE001 — the scheduler must survive anything
            pass
        time.sleep(CHECK_SECONDS)


def start_scheduler(db_path: str) -> threading.Thread:
    t = threading.Thread(target=scheduler_loop, args=(db_path,), daemon=True)
    t.start()
    return t
