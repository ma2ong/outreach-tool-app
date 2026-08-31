"""Step zero of a sequence, after the gates came off (docs/75).

This file used to assert that a sequence's first letter went through the strict
first-touch gate — evidence, a named buyer, a verified address — so sequences could not
become a back door around it. Allen removed that gate entirely: "质量门拆了，以后不许
设置质量门". What is asserted now is what took its place, because the risk did not
disappear with the gate — it moved to the frequency rule.
"""
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
        " VALUES (21,'VenueWorks','USA','ops@venueworks.com','valid','https://venueworks.com',"
        " '活动租赁 (90)','VenueWorks provides event production')"
    )
    c.commit()
    sid = sequences.create_sequence(c, "First touch", "email", [
        {"day_offset": 0, "subject": "LED project question", "body": "Hi VenueWorks, quick question."},
        {"day_offset": 14, "subject": "Re", "body": "Following up."},
    ])
    sequences.enroll_leads(c, sid, [21])
    eid = c.execute("SELECT id FROM sequence_enrollments WHERE lead_no=21").fetchone()["id"]
    return c, sid, eid


def _thin(monkeypatch, **over):
    facts = {"score": 12, "grade": "D", "best_signal": None,
             "data_incomplete": True, "missing_decision_maker": True}
    facts.update(over)
    monkeypatch.setattr(followup_decision.sales_intelligence, "score_lead",
                        lambda *a, **k: facts)


def test_a_first_letter_goes_out_with_nothing_known_about_the_company(conn, monkeypatch):
    """Low score, no named buyer, incomplete evidence — every one of these used to stop
    the letter, and together they stopped 77 of 113 on 2026-08-28."""
    c, _, eid = conn
    _thin(monkeypatch)
    assert followup_decision.evaluate(c, eid)["action"] == "continue"


def test_the_sender_actually_sends_it(conn, monkeypatch):
    c, _, eid = conn
    _thin(monkeypatch)
    sent = []
    res = sequence_send.send_due(c, [eid], sender=lambda *a: sent.append(a),
                                 email_delay=(0, 0), autonomous_quality=True)
    assert res["sent"] == 1 and len(sent) == 1


def test_a_first_letter_is_never_held_for_the_cooldown(conn, monkeypatch):
    """Nothing has been sent yet, so there is no clock to wait on — a lead must not be
    able to start life already throttled."""
    c, _, eid = conn
    _thin(monkeypatch)
    d = followup_decision.evaluate(c, eid)
    assert d["action"] == "continue" and d["touch_count"] == 0


def test_someone_who_replied_still_gets_no_cold_letter(conn, monkeypatch):
    c, _, eid = conn
    _thin(monkeypatch)
    c.execute("INSERT INTO outreach(lead_no,channel,status) VALUES (21,'email','replied')")
    c.commit()
    d = followup_decision.evaluate(c, eid)
    assert d["action"] == "stop" and "回复" in d["reason"]


def test_a_customer_who_bought_still_gets_no_cold_letter(conn, monkeypatch):
    c, _, eid = conn
    _thin(monkeypatch)
    c.execute("UPDATE leads SET stage='won' WHERE no=21")
    c.commit()
    assert followup_decision.evaluate(c, eid)["action"] == "stop"


def test_the_second_step_waits_two_weeks_after_the_first(conn, monkeypatch):
    c, _, eid = conn
    _thin(monkeypatch)
    c.execute("INSERT INTO send_log(lead_no,channel,campaign,sent_at)"
              " VALUES (21,'email','序列:First touch',datetime('now','-3 days'))")
    c.commit()
    d = followup_decision.evaluate(c, eid)
    assert d["action"] == "delay"
    assert dt.date.fromisoformat(d["next_due_date"]) > dt.date.today()
