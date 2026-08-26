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
        " VALUES (21,'VenueWorks','USA','ops@venueworks.com','valid','https://venueworks.com',"
        " '活动租赁 (90)','VenueWorks provides event production')"
    )
    c.commit()
    sid = sequences.create_sequence(c, "First touch", "email", [
        {"day_offset": 0, "subject": "VenueWorks LED", "body": "Hi VenueWorks, quick question."},
        {"day_offset": 4, "subject": "Re", "body": "Following up."},
    ])
    sequences.enroll_leads(c, sid, [21])
    eid = c.execute("SELECT id FROM sequence_enrollments WHERE lead_no=21").fetchone()["id"]
    monkeypatch.setattr("app.agent.oversight.weak_sequence_ids", lambda conn: set())
    return c, sid, eid


def test_sequence_step_zero_uses_strict_first_touch_gate(conn, monkeypatch):
    c, _, eid = conn
    monkeypatch.setattr(
        followup_decision.sales_intelligence, "score_lead",
        lambda *a, **k: {"score": 82, "grade": "A", "best_signal": None,
                         "data_incomplete": False, "missing_decision_maker": True},
    )
    d = followup_decision.evaluate(c, eid)
    assert d["action"] == "change_angle"
    assert "自主首触质量门" in d["reason"]
    assert "决策联系人" in d["reason"]


def test_sequence_step_zero_can_pass_when_pr20_requirements_are_met(conn, monkeypatch):
    c, _, eid = conn
    monkeypatch.setattr(
        followup_decision.sales_intelligence, "score_lead",
        lambda *a, **k: {"score": 82, "grade": "A", "best_signal": None,
                         "data_incomplete": False, "missing_decision_maker": False},
    )
    d = followup_decision.evaluate(c, eid)
    assert d["action"] == "continue"
    assert "PR #20" in d["reason"]


def test_autosend_sequence_first_touch_is_held_before_sender(conn, monkeypatch):
    c, _, eid = conn
    monkeypatch.setattr(
        followup_decision.sales_intelligence, "score_lead",
        lambda *a, **k: {"score": 82, "grade": "A", "best_signal": None,
                         "data_incomplete": False, "missing_decision_maker": True},
    )
    sent = []
    res = sequence_send.send_due(
        c, [eid], sender=lambda *a: sent.append(a), email_delay=(0, 0),
        autonomous_quality=True,
    )
    assert res["sent"] == 0 and res["quality_held"] == 1
    assert sent == []
    assert c.execute("SELECT status FROM sequence_enrollments WHERE id=?", (eid,)).fetchone()[0] == "quality_hold"
