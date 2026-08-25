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

A due date is not itself permission to send. Automatic sequence steps pass the
follow-up decision layer immediately before the sender is called; manual sends retain
human timing judgment while using the same delivery/message safety guards.
"""
import datetime as _dt
import json
import threading
import time

from app import settings

WINDOW = (9, 20)
CHECK_SECONDS = 300

_K_ENABLED = "autosend_enabled"
_K_LAST_DATE = "autosend_last_date"
_K_LAST_RESULT = "autosend_last_result"
_K_SAFETY_PAUSE = "autosend_safety_pause"
_K_RISK_ACK = "autosend_risk_ack"

ACK_TOLERANCE_PCT = 1.0


def enabled(conn) -> bool:
    return settings.get(conn, _K_ENABLED, "0") == "1"


def set_enabled(conn, on: bool) -> None:
    settings.set_value(conn, _K_ENABLED, "1" if on else "0")
    if on:
        settings.set_value(conn, _K_SAFETY_PAUSE, "")
    else:
        clear_risk_ack(conn)


def acknowledge(conn, pause: dict) -> dict:
    evidence = pause.get("evidence") or pause.get("deliverability") or {}
    data = {"code": pause.get("code"),
            "bounce_rate": float(evidence.get("bounce_rate") or 0.0),
            "acked_at": _dt.datetime.now(_dt.UTC).isoformat()}
    settings.set_value(conn, _K_RISK_ACK, json.dumps(data, ensure_ascii=False))
    return data


def risk_ack(conn) -> dict | None:
    raw = settings.get(conn, _K_RISK_ACK)
    try:
        return json.loads(raw) if raw else None
    except json.JSONDecodeError:
        return None


def clear_risk_ack(conn) -> None:
    settings.set_value(conn, _K_RISK_ACK, "")


def ack_covers(ack: dict | None, code: str, bounce_rate: float) -> bool:
    if not ack or ack.get("code") != code:
        return False
    return bounce_rate <= float(ack.get("bounce_rate") or 0.0) + ACK_TOLERANCE_PCT


def safety_pause(conn) -> dict | None:
    raw = settings.get(conn, _K_SAFETY_PAUSE)
    try:
        return json.loads(raw) if raw else None
    except json.JSONDecodeError:
        return None


def pause(conn, code: str, reason: str, evidence: dict) -> dict:
    data = {"code": code, "reason": reason, "evidence": evidence,
            "paused_at": _dt.datetime.now(_dt.UTC).isoformat()}
    settings.set_value(conn, _K_ENABLED, "0")
    settings.set_value(conn, _K_SAFETY_PAUSE, json.dumps(data, ensure_ascii=False))
    return data


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
    quality = {"continue": 0, "delay": 0, "change_angle": 0, "stop": 0}
    if sendable:
        from app.agent import followup_decision
        assessment = followup_decision.evaluate_due(
            conn, [d["enrollment_id"] for d in sendable])
        quality = {key: assessment[key] for key in quality}
    return {
        "due": len(due),
        "sendable": len(sendable),
        "will_send": min(quality["continue"], outreach.remaining_today(conn), outreach.MAX_BATCH),
        "oldest_due": oldest,
        "followup_quality": quality,
    }


def status(conn) -> dict:
    return {"enabled": enabled(conn),
            "last_date": settings.get(conn, _K_LAST_DATE) or None,
            "last_result": settings.get(conn, _K_LAST_RESULT) or None,
            "safety_pause": safety_pause(conn),
            "risk_ack": risk_ack(conn),
            "preview": preview(conn)}


def should_run(conn, now: _dt.datetime | None = None) -> bool:
    now = now or _dt.datetime.now()
    if not enabled(conn):
        return False
    if not (WINDOW[0] <= now.hour < WINDOW[1]):
        return False
    return settings.get(conn, _K_LAST_DATE) != now.date().isoformat()


def run_once(conn, sender, image_default: str | None, now: _dt.datetime | None = None,
             email_delay=(16, 28)) -> dict:
    """Evaluate and send today's due EMAIL steps within budget; record the outcome."""
    from app import sequence_send, sequences
    now = now or _dt.datetime.now()
    settings.set_value(conn, _K_LAST_DATE, now.date().isoformat())
    try:
        due_ids = [d["enrollment_id"] for d in sequences.due_queue(conn, "email")]
        if not due_ids:
            settings.set_value(conn, _K_LAST_RESULT, f"{now:%m-%d %H:%M} 无到期邮件跟进")
            return {"sent": 0, "failed": 0, "deferred": 0}
        res = sequence_send.send_due(
            conn, due_ids, sender=sender, image_default=image_default,
            email_delay=email_delay, autonomous_quality=True,
        )
    except Exception as exc:  # noqa: BLE001
        settings.set_value(conn, _K_LAST_RESULT, f"{now:%m-%d %H:%M} 运行失败：{str(exc)[:120]}")
        return {"sent": 0, "failed": 0, "deferred": 0}
    # Keep the original prefix stable for readiness/UI/tests; quality outcomes append.
    note = f"{now:%m-%d %H:%M} 自动发送：成功 {res['sent']}，失败 {res['failed']}"
    if res.get("delayed"):
        note += f"，质量延后 {res['delayed']}"
    if res.get("quality_held"):
        note += f"，换角度暂停 {res['quality_held']}"
    if res.get("stopped"):
        note += f"，停止冷跟进 {res['stopped']}"
    if res.get("held"):
        note += f"，安全拦下 {res['held']}"
    if res.get("deferred"):
        note += f"，额度外延后 {res['deferred']}（明天继续）"
    settings.set_value(conn, _K_LAST_RESULT, note)
    return res


def scheduler_loop(db_path: str) -> None:
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
        except Exception:  # noqa: BLE001
            pass
        time.sleep(CHECK_SECONDS)


def start_scheduler(db_path: str) -> threading.Thread:
    t = threading.Thread(target=scheduler_loop, args=(db_path,), daemon=True)
    t.start()
    return t
