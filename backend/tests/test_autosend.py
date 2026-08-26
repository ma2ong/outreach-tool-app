"""Auto-send exists because 266 enrolled leads sat for three days with zero sends.
It must: fire once per day inside the window, email only, respect budgets, and be
trivially switchable off.

These tests isolate scheduler/delivery mechanics. PR #21's worth-now policy has its own
tests, so this fixture makes that policy deterministically return `continue`; transport
quota/SMTP tests should not fail because a sales-scoring fixture changed.
"""
import datetime as dt

import pytest

from app import autosend, outreach, sequences
from app.db import connect, init_schema


@pytest.fixture
def conn(tmp_path, monkeypatch):
    from app.agent import followup_decision

    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    rows = ", ".join(f"({i}, 'Co{i}', 'USA', 'c{i}@x.com')" for i in range(1, 41))
    c.executescript(f"INSERT INTO leads(no, company_en, country, email) VALUES {rows};")
    c.execute("UPDATE leads SET email_status='valid'")
    # one lead with phone in a WA sequence — must NOT be auto-sent
    c.execute("UPDATE leads SET phone='+15550001' WHERE no=40")
    c.commit()
    sid = sequences.create_sequence(c, "邮件序列", "email", [{"day_offset": 0, "body": "hi {name}"},
                                                            {"day_offset": 3, "body": "again {name}"}])
    sequences.enroll_leads(c, sid, list(range(1, 40)))
    wa = sequences.create_sequence(c, "WA序列", "whatsapp", [{"day_offset": 0, "body": "hi"}])
    sequences.enroll_leads(c, wa, [40])

    def allow(conn, enrollment_id, **kwargs):
        row = conn.execute(
            "SELECT lead_no,sequence_id FROM sequence_enrollments WHERE id=?", (enrollment_id,)
        ).fetchone()
        return {"enrollment_id": enrollment_id, "lead_no": row["lead_no"],
                "sequence_id": row["sequence_id"], "action": "continue",
                "reason": "transport fixture", "score": 80, "touch_count": 0,
                "signal_confidence": 0, "next_due_date": None}

    monkeypatch.setattr(followup_decision, "evaluate", allow)
    return c


def _noon(day="2026-07-20"):
    return dt.datetime.fromisoformat(f"{day}T12:00:00")


def test_should_run_once_per_day_inside_window(conn):
    autosend.set_enabled(conn, True)
    assert autosend.should_run(conn, _noon())
    autosend.run_once(conn, lambda *a: None, None, _noon(), email_delay=(0, 0))
    assert not autosend.should_run(conn, _noon())              # already ran today
    assert autosend.should_run(conn, _noon("2026-07-21"))      # next day fires again


def test_should_not_run_outside_window_or_disabled(conn):
    autosend.set_enabled(conn, True)
    assert not autosend.should_run(conn, dt.datetime.fromisoformat("2026-07-20T07:59:00"))
    assert not autosend.should_run(conn, dt.datetime.fromisoformat("2026-07-20T21:00:00"))
    autosend.set_enabled(conn, False)
    assert not autosend.should_run(conn, _noon())


def test_run_once_sends_email_only_within_budget(conn):
    sent = []
    res = autosend.run_once(
        conn, lambda to, s, b, att: sent.append(to), None, _noon(),
        email_delay=(0, 0),
    )
    assert res["sent"] == min(39, outreach.DAILY_CAP, outreach.MAX_BATCH)
    assert res["deferred"] == 39 - min(39, outreach.DAILY_CAP, outreach.MAX_BATCH)
    assert all("@x.com" in t for t in sent)
    # WA enrollment untouched: still due, step 0
    wa_due = sequences.due_queue(conn, "whatsapp")
    assert len(wa_due) == 1 and wa_due[0]["current_step"] == 0
    st = autosend.status(conn)
    expected = min(39, outreach.DAILY_CAP, outreach.MAX_BATCH)
    assert f"成功 {expected}" in st["last_result"] and st["last_date"] == "2026-07-20"


def test_run_failure_recorded_and_day_not_retried(conn):
    def boom(*a):
        raise OSError("smtp down")
    res = autosend.run_once(conn, boom, None, _noon(), email_delay=(0, 0))
    assert res["sent"] == 0 and res["failed"] > 0
    # failures are per-email inside send_due, so partial info lands in last_result;
    # either way the day is marked done — no 5-minute retry hammering
    assert not autosend.should_run(conn, _noon())


def test_status_defaults(conn):
    st = autosend.status(conn)
    assert st["enabled"] is False
    assert st["last_date"] is None and st["last_result"] is None
    assert st["preview"]["due"] == 39
    assert st["preview"]["will_send"] == min(39, outreach.DAILY_CAP, outreach.MAX_BATCH)
    assert st["preview"]["quality_gate"] == "evaluated_at_send"


def test_a_run_that_cannot_read_the_queue_still_says_so(conn, monkeypatch):
    """The day is marked done before sending, so a silent failure burns it. On
    2026-08-20 the queue read raised mid-migration and the follow-up engine sat dead
    for a fortnight behind a green tick."""
    from app import autosend, sequences, settings
    def boom(*a, **k):
        raise RuntimeError("no such column: e.next_due_date")
    monkeypatch.setattr(sequences, "due_queue", boom)
    result = autosend.run_once(conn, sender=lambda *a: None, image_default=None)
    assert result == {"sent": 0, "failed": 0, "deferred": 0}
    assert "运行失败" in settings.get(conn, "autosend_last_result")
    assert "no such column" in settings.get(conn, "autosend_last_result")


def test_a_stale_result_line_turns_the_readiness_check_red(conn):
    from app import autosend, readiness, settings
    autosend.set_enabled(conn, True)
    settings.set_value(conn, "autosend_last_date", "2026-08-20")
    settings.set_value(conn, "autosend_last_result", "08-05 09:04 自动发送：成功 30，失败 0")
    check = next(c for c in readiness.build(conn)["checks"] if c["id"] == "autosend")
    assert check["status"] == "blocked" and "今天没跑成" in check["detail"]


def test_a_result_from_today_stays_green(conn):
    from app import autosend, readiness, settings
    autosend.set_enabled(conn, True)
    settings.set_value(conn, "autosend_last_date", "2026-08-20")
    settings.set_value(conn, "autosend_last_result", "08-20 09:04 自动发送：成功 30，失败 0")
    check = next(c for c in readiness.build(conn)["checks"] if c["id"] == "autosend")
    assert check["status"] == "ok"


# ------------------------------------------- crash mid-send must not burn the day

def test_a_run_cut_short_does_not_count_as_today_being_done(conn, monkeypatch):
    """`last_date` used to be written before the sending started. A send is 30 mails at
    16-28s apart — 8 to 14 minutes — so one restart in that window (a sleeping laptop, a
    service reload) left the day marked as run, with nothing sent and nothing recorded.
    That is how the dashboard came to say "today already ran" while the last result was
    five days old."""
    from app import autosend

    def die(*args, **kwargs):
        raise KeyboardInterrupt("process going down mid-send")

    autosend.set_enabled(conn, True)
    monkeypatch.setattr("app.sequence_send.send_due", die)
    try:
        autosend.run_once(conn, lambda *a: None, None, _noon())
    except KeyboardInterrupt:
        pass
    later = _noon() + dt.timedelta(minutes=autosend.RETRY_AFTER_MINUTES + 1)
    assert autosend.should_run(conn, later) is True, "被打断的一天必须还能重跑"


def test_an_interrupted_run_is_visible_afterwards(conn, monkeypatch):
    from app import autosend, settings

    autosend.set_enabled(conn, True)
    monkeypatch.setattr("app.sequence_send.send_due",
                        lambda *a, **k: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        autosend.run_once(conn, lambda *a: None, None, _noon())
    except KeyboardInterrupt:
        pass
    autosend.should_run(conn, _noon() + dt.timedelta(minutes=autosend.RETRY_AFTER_MINUTES + 1))
    assert "中断" in (settings.get(conn, "autosend_last_result") or "")


def test_a_completed_run_still_closes_the_day(conn, monkeypatch):
    from app import autosend

    autosend.set_enabled(conn, True)
    monkeypatch.setattr("app.sequence_send.send_due",
                        lambda *a, **k: {"sent": 3, "failed": 0, "deferred": 0})
    autosend.run_once(conn, lambda *a: None, None, _noon())
    assert autosend.should_run(conn, _noon()) is False


def test_a_restart_storm_does_not_retry_instantly(conn, monkeypatch):
    """Retrying is right; retrying every few seconds through a crash loop is not."""
    from app import autosend

    autosend.set_enabled(conn, True)
    monkeypatch.setattr("app.sequence_send.send_due",
                        lambda *a, **k: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        autosend.run_once(conn, lambda *a: None, None, _noon())
    except KeyboardInterrupt:
        pass
    assert autosend.should_run(conn, _noon() + dt.timedelta(minutes=1)) is False
    assert autosend.should_run(
        conn, _noon() + dt.timedelta(minutes=autosend.RETRY_AFTER_MINUTES + 1)) is True
