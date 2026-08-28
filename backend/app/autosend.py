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
from app.outreach import EMAIL_DELAY

WINDOW = (9, 20)
CHECK_SECONDS = 300

_K_ENABLED = "autosend_enabled"
_K_LAST_DATE = "autosend_last_date"
_K_LAST_ATTEMPT = "autosend_last_attempt_at"
# A send is 30 mails at 16-28s apart, so a restart during one is ordinary on a desktop
# that sleeps. Retrying is right; retrying every tick through a crash loop is not.
RETRY_AFTER_MINUTES = 20
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
    """Cheap queue/capacity preview; Worth-Now is evaluated only at the send boundary.

    This endpoint is polled by health/UI surfaces. Running Sales Truth, memory and weak-
    sequence analysis across the whole due queue on every refresh creates needless SQLite
    work and lock pressure. The actual scheduler still evaluates each chosen enrollment
    immediately before sender invocation.
    """
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
        "quality_gate": "evaluated_at_send",
    }


def status(conn) -> dict:
    return {"enabled": enabled(conn),
            "last_date": settings.get(conn, _K_LAST_DATE) or None,
            "last_result": settings.get(conn, _K_LAST_RESULT) or None,
            "safety_pause": safety_pause(conn),
            "risk_ack": risk_ack(conn),
            "preview": preview(conn)}


def _last_attempt(conn) -> _dt.datetime | None:
    raw = settings.get(conn, _K_LAST_ATTEMPT)
    if not raw:
        return None
    try:
        return _dt.datetime.fromisoformat(raw)
    except ValueError:
        return None


def should_run(conn, now: _dt.datetime | None = None) -> bool:
    """Whether today's send still needs doing.

    The day is closed by a run that *finished*, not by one that started. `last_date` used
    to be written before the first mail went out, so a restart mid-send left the day
    marked done with nothing sent and nothing recorded — which is exactly how the
    dashboard came to report "already ran today" beside a five-day-old result.
    """
    now = now or _dt.datetime.now()
    if not enabled(conn):
        return False
    if not (WINDOW[0] <= now.hour < WINDOW[1]):
        return False
    if settings.get(conn, _K_LAST_DATE) == now.date().isoformat():
        return False
    started = _last_attempt(conn)
    if started and now - started < _dt.timedelta(minutes=RETRY_AFTER_MINUTES):
        # A previous attempt is either still running or died moments ago. Either way,
        # starting a second one now would double-send.
        return False
    if started:
        settings.set_value(
            conn, _K_LAST_RESULT,
            f"{started:%m-%d %H:%M} 上次自动发送中途中断（进程重启或休眠），现在重试")
    return True


def _top_up(conn, gap: int) -> int:
    """Fill a thin day with companies that have gone cold long enough (docs/73 R3).

    Relaxing `eligible_leads` alone changes nothing: this runs the due sequence steps and
    never looks at that pool, so without a way in, the 322 re-approachable companies stay
    exactly as idle as the bookkeeping had left them.

    Korea keeps Korean and every other country gets English (docs/67 R1), decided by
    country here rather than left to the sequence — `language_blocked` only guards the
    Korean sequence, so an unrouted Korean lead would quietly receive the English letter.
    """
    from app import message_guard, recontact, sequences
    from app.seed_angle2 import EN_NAME, KO_NAME

    # Cooled down is not the same as writable. 44 of the 321 re-approachable records have
    # somebody's mailbox in the company-name column, and another 77 carry a real name with
    # nothing personal to say about it; the guard refuses both at send time. Filtering here
    # means `gap` is filled with letters that will actually go out.
    candidates = recontact.reapproachable(conn, "email")
    if not candidates:
        return 0
    # `IN (...)` does not preserve order, so the longest-silent-first ordering that
    # `reapproachable` established is re-applied here rather than lost to rowid order.
    facts = {r["no"]: dict(r) for r in conn.execute(
        "SELECT no, company_en, website, city, hook FROM leads WHERE no IN (%s)"
        % ",".join("?" * len(candidates)), candidates)}
    ids = []
    for no in candidates:
        if message_guard.can_be_addressed(facts.get(no, {})):
            ids.append(no)
            if len(ids) >= gap:
                break
    if not ids:
        return 0
    sid = {}
    for name in (EN_NAME, KO_NAME):
        row = conn.execute("SELECT id FROM sequences WHERE name=?", (name,)).fetchone()
        if row:
            sid[name] = row["id"]
    if KO_NAME not in sid or EN_NAME not in sid:
        return 0
    # Leads the Korean sequence does *not* block are the Korean-country ones.
    korean = set(ids) - set(sequences.language_blocked(conn, sid[KO_NAME], ids))
    added = sequences.enroll_leads(conn, sid[KO_NAME], sorted(korean))
    added += sequences.enroll_leads(
        conn, sid[EN_NAME], [i for i in ids if i not in korean])
    return added


def run_once(conn, sender, image_default: str | None, now: _dt.datetime | None = None,
             email_delay=EMAIL_DELAY) -> dict:
    """Evaluate and send today's due EMAIL steps within budget; record the outcome."""
    from app import sequence_send, sequences
    now = now or _dt.datetime.now()
    # Mark the attempt, not the day. The day is closed below, once this actually
    # finished — a run that dies halfway must come back, not silently skip to tomorrow.
    settings.set_value(conn, _K_LAST_ATTEMPT, now.isoformat())
    try:
        from app import local_time

        due = sequences.due_queue(conn, "email")
        # A day with fewer follow-ups due than budget is not a day to send less; it is a
        # day to bring back companies that have been silent long enough to be prospects
        # again (docs/73 R3). Top up to the budget, never past it.
        from app import outreach as _outreach
        gap = _outreach.remaining_today(conn) - len(due)
        if gap > 0 and _top_up(conn, gap):
            due = sequences.due_queue(conn, "email")
        # His window is the outer bound (R1); the recipient's small hours are the veto
        # (R2). Anything held back stays due and goes tomorrow — these are follow-ups,
        # and a day costs nothing (docs/66 R4).
        held: dict[str, int] = {}
        due_ids = []
        for item in due:
            allowed, why = local_time.may_email(item.get("_lead_country"), _dt.datetime.now(_dt.UTC))
            if allowed:
                due_ids.append(item["enrollment_id"])
            else:
                held[why] = held.get(why, 0) + 1
        if held and not due_ids:
            settings.set_value(conn, _K_LAST_RESULT,
                               f"{now:%m-%d %H:%M} 到期 {len(due)} 封都不在收件人当地的合适时间，明天再发")
            return {"sent": 0, "failed": 0, "deferred": len(due), "held": held}
        if not due_ids:
            settings.set_value(conn, _K_LAST_DATE, now.date().isoformat())
            settings.set_value(conn, _K_LAST_RESULT, f"{now:%m-%d %H:%M} 无到期邮件跟进")
            return {"sent": 0, "failed": 0, "deferred": 0}
        # A heartbeat, not a start stamp. At 60-110 seconds a letter a full run takes
        # over an hour, and `due_now` treats 20 minutes of silence as a dead run — so
        # without this the loop would start a second run on top of the first and send
        # everything twice.
        started_at = time.monotonic()

        def beat(_done, _total):
            # Anchored on this run's own `now` plus real elapsed time, so a simulated
            # clock in a test does not get stamped with today's wall clock.
            elapsed = _dt.timedelta(seconds=time.monotonic() - started_at)
            settings.set_value(conn, _K_LAST_ATTEMPT, (now + elapsed).isoformat())

        res = sequence_send.send_due(
            conn, due_ids, sender=sender, image_default=image_default,
            email_delay=email_delay, autonomous_quality=True, on_progress=beat,
        )
    except Exception as exc:  # noqa: BLE001
        # A failure is a finished run: it is recorded and the day is closed, because
        # retrying a broken send every 20 minutes would only repeat the failure.
        settings.set_value(conn, _K_LAST_DATE, now.date().isoformat())
        settings.set_value(conn, _K_LAST_RESULT, f"{now:%m-%d %H:%M} 运行失败：{str(exc)[:120]}")
        return {"sent": 0, "failed": 0, "deferred": 0}
    # The day is closed here, by a run that finished — not when it started.
    settings.set_value(conn, _K_LAST_DATE, now.date().isoformat())
    # Keep the original prefix stable for readiness/UI/tests; quality outcomes append.
    note = f"{now:%m-%d %H:%M} 自动发送：成功 {res['sent']}，失败 {res['failed']}"
    if held:
        # Otherwise a short day looks like the system missed something.
        note += f"，避开收件人夜间 {sum(held.values())}"
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
