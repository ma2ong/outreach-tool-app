import datetime as dt

import pytest

from app import sequences, sequence_send
from app.agent import followup_decision
from app.db import connect, init_schema


@pytest.fixture
def conn(tmp_path, monkeypatch):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.execute(
        "INSERT INTO leads(no,company_en,country,email,email_status,website,target_fit,hook)"
        " VALUES (10,'Alpha AV','USA','buyer@alpha.com','valid','https://alpha.com',"
        " 'AV集成商 (85)','Alpha installs commercial AV systems')"
    )
    c.commit()
    sid = sequences.create_sequence(c, "Cold follow-up", "email", [
        {"day_offset": 0, "subject": "Hi {name}", "body": "Hi {name}, quick question."},
        {"day_offset": 3, "subject": "Re: LED", "body": "Following up on my note."},
        {"day_offset": 8, "subject": "Re: LED", "body": "One last useful check-in."},
    ])
    sequences.enroll_leads(c, sid, [10])
    # The module owns all optional evidence-schema dependencies; make that explicit in
    # this standalone fixture rather than relying on FastAPI startup side effects.
    followup_decision.ensure_schema(c)
    eid = c.execute("SELECT id FROM sequence_enrollments WHERE lead_no=10").fetchone()["id"]
    monkeypatch.setattr(
        followup_decision.sales_intelligence, "score_lead",
        lambda *a, **k: {"score": 72, "grade": "B", "best_signal": None,
                         "data_incomplete": False},
    )
    monkeypatch.setattr("app.agent.oversight.weak_sequence_ids", lambda conn: set())
    return c, sid, eid


def _touch(conn, count=1, days_ago=10):
    conn.execute(
        "INSERT INTO outreach(lead_no,channel,status,touch_count,message_sent_date)"
        " VALUES (10,'email','messaged',?,date('now',?))"
        " ON CONFLICT(lead_no,channel) DO UPDATE SET status='messaged',touch_count=excluded.touch_count,"
        " message_sent_date=excluded.message_sent_date",
        (count, f"-{days_ago} days"),
    )
    for i in range(count):
        conn.execute(
            "INSERT INTO send_log(lead_no,channel,campaign,sent_at)"
            " VALUES (10,'email','序列:Cold follow-up',datetime('now',?))",
            (f"-{days_ago + i} days",),
        )
    conn.commit()


def test_good_due_followup_continues(conn):
    c, _, eid = conn
    _touch(c, 1, 10)
    d = followup_decision.evaluate(c, eid)
    assert d["action"] == "continue"
    assert d["score"] == 72


def test_low_value_account_is_delayed_not_declared_uninterested(conn, monkeypatch):
    c, _, eid = conn
    _touch(c, 1, 10)
    monkeypatch.setattr(
        followup_decision.sales_intelligence, "score_lead",
        lambda *a, **k: {"score": 45, "grade": "C", "best_signal": None},
    )
    today = dt.date(2026, 8, 25)
    d = followup_decision.evaluate(c, eid, today=today)
    assert d["action"] == "delay"
    assert d["next_due_date"] == "2026-09-08"
    assert "不感兴趣" not in d["reason"]


def test_very_low_value_account_holds_for_new_angle(conn, monkeypatch):
    c, _, eid = conn
    monkeypatch.setattr(
        followup_decision.sales_intelligence, "score_lead",
        lambda *a, **k: {"score": 20, "grade": "D", "best_signal": None},
    )
    d = followup_decision.evaluate(c, eid)
    assert d["action"] == "change_angle"


def test_too_soon_is_delayed_by_touch_count_cadence(conn):
    c, _, eid = conn
    _touch(c, 2, 2)
    today = dt.date.today()
    d = followup_decision.evaluate(c, eid, today=today)
    assert d["action"] == "delay"
    assert dt.date.fromisoformat(d["next_due_date"]) > today
    assert "至少间隔 5 天" in d["reason"]


def test_repeated_silence_changes_angle_without_inventing_rejection(conn):
    c, _, eid = conn
    _touch(c, 3, 12)
    d = followup_decision.evaluate(c, eid)
    assert d["action"] == "change_angle"
    assert "无真人回复" in d["reason"]
    assert "拒绝" not in d["reason"] and "不感兴趣" not in d["reason"]


def test_fresh_signal_prevents_silence_angle_hold(conn, monkeypatch):
    c, _, eid = conn
    _touch(c, 3, 12)
    monkeypatch.setattr(
        followup_decision.sales_intelligence, "score_lead",
        lambda *a, **k: {"score": 80, "grade": "A", "best_signal": {
            "confidence": 80, "headline": "New venue project", "source_url": "https://alpha.com/news"
        }},
    )
    d = followup_decision.evaluate(c, eid)
    assert d["action"] == "continue"
    assert d["signal_confidence"] == 80


def test_weak_sequence_is_parked_before_another_send(conn, monkeypatch):
    c, sid, eid = conn
    _touch(c, 1, 10)
    monkeypatch.setattr("app.agent.oversight.weak_sequence_ids", lambda conn: {sid})
    d = followup_decision.evaluate(c, eid)
    assert d["action"] == "change_angle"
    assert "零回复" in d["reason"]


def test_open_opportunity_stops_cold_sequence_ownership(conn):
    c, _, eid = conn
    from app import opportunities
    opportunities.create(c, 10, {"title": "Lobby LED", "stage": "qualified"})
    d = followup_decision.evaluate(c, eid)
    assert d["action"] == "stop"
    assert "开放商机" in d["reason"]


def test_customer_reply_stops_cold_followup(conn):
    c, _, eid = conn
    c.execute(
        "INSERT INTO inbox_messages(lead_no,channel,kind,from_addr,subject,body,received_at)"
        " VALUES (10,'email','reply','buyer@alpha.com','Re','Interested',datetime('now'))"
    )
    c.commit()
    d = followup_decision.evaluate(c, eid)
    assert d["action"] == "stop"
    assert "已经回复" in d["reason"]


def test_apply_delay_updates_only_machine_schedule_and_audits(conn):
    c, _, eid = conn
    d = {"enrollment_id": eid, "lead_no": 10,
         "sequence_id": c.execute("SELECT sequence_id FROM sequence_enrollments WHERE id=?", (eid,)).fetchone()[0],
         "action": "delay", "reason": "cadence", "score": 60,
         "touch_count": 2, "signal_confidence": 0, "next_due_date": "2026-09-01"}
    followup_decision.apply(c, d)
    row = c.execute("SELECT status,next_due_date FROM sequence_enrollments WHERE id=?", (eid,)).fetchone()
    assert row["status"] == "active" and row["next_due_date"] == "2026-09-01"
    audit = c.execute("SELECT action,applied FROM followup_decisions WHERE enrollment_id=?", (eid,)).fetchone()
    assert audit["action"] == "delay" and audit["applied"] == 1


def test_apply_change_angle_parks_without_creating_sales_task(conn):
    c, sid, eid = conn
    before = c.execute("SELECT COUNT(*) c FROM activities").fetchone()["c"]
    followup_decision.apply(c, {"enrollment_id": eid, "lead_no": 10, "sequence_id": sid,
        "action": "change_angle", "reason": "weak angle", "score": 60,
        "touch_count": 3, "signal_confidence": 0, "next_due_date": None})
    status = c.execute("SELECT status FROM sequence_enrollments WHERE id=?", (eid,)).fetchone()["status"]
    after = c.execute("SELECT COUNT(*) c FROM activities").fetchone()["c"]
    assert status == "quality_hold" and after == before


def test_automatic_send_obeys_delay_but_manual_send_keeps_human_timing(conn, monkeypatch):
    c, sid, eid = conn
    sent = []

    def fake_decision(conn, enrollment_id, **kwargs):
        return {"enrollment_id": enrollment_id, "lead_no": 10, "sequence_id": sid,
                "action": "delay", "reason": "wait", "score": 60, "touch_count": 1,
                "signal_confidence": 0,
                "next_due_date": (dt.date.today() + dt.timedelta(days=5)).isoformat()}

    monkeypatch.setattr(followup_decision, "evaluate", fake_decision)
    auto = sequence_send.send_due(
        c, [eid], sender=lambda *a: sent.append(a), email_delay=(0, 0), autonomous_quality=True)
    assert auto["sent"] == 0 and auto["delayed"] == 1 and sent == []

    c.execute("UPDATE sequence_enrollments SET next_due_date=date('now') WHERE id=?", (eid,))
    c.commit()
    manual = sequence_send.send_due(
        c, [eid], sender=lambda *a: sent.append(a), email_delay=(0, 0), autonomous_quality=False)
    assert manual["sent"] == 1 and len(sent) == 1
