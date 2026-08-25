"""Auto-send exists because 266 enrolled leads sat for 3 days with zero sends.
It must: fire once per day inside the window, email only, respect budgets, and be
trivially switchable off.

These tests isolate scheduler/delivery mechanics. PR #21's commercial worth-now policy
has its own tests; here it is fixed to a healthy account so a cadence test does not turn
into an accidental sales-scoring test.
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

    monkeypatch.setattr(
        followup_decision.sales_intelligence, "score_lead",
        lambda *a, **k: {"score": 80, "grade": "A", "best_signal": None,
                         "data_incomplete": False, "missing_decision_maker": False},
    )
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
    assert res["sent"] == outreach.MAX_BATCH        # 39 due, batch cap 30
    assert res["deferred"] == 39 - outreach.MAX_BATCH
    assert all("@x.com" in t for t in sent)
    # WA enrollment untouched: still due, step 0
    wa_due = sequences.due_queue(conn, "whatsapp")
    assert len(wa_due) == 1 and wa_due[0]["current_step"] == 0
    st = autosend.status(conn)
    assert "成功 30" in st["last_result"] and st["last_date"] == "2026-07-20"


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
    assert st["preview"]["will_send"] == outreach.MAX_BATCH
    assert st["preview"]["followup_quality"]["continue"] == 39


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
