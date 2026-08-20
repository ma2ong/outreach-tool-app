import datetime as dt

import pytest

from app import autosend, sequences, settings
from app.agent import llm, mission, oversight, proposals, run


def _recent_email_sample(conn, size=25, bounced=0):
    now = dt.datetime.now(dt.UTC).isoformat()
    for i in range(size):
        no = 100 + i
        conn.execute(
            "INSERT INTO leads(no,company_en,country,email,bounced_at) VALUES (?,?,?,?,?)",
            (no, f"Sample {i}", "USA", f"s{i}@example.com", now if i < bounced else None),
        )
        conn.execute(
            "INSERT INTO send_log(lead_no,channel,campaign,sent_at) VALUES (?,?,?,?)",
            (no, "email", "sample", now),
        )
    conn.commit()


def test_deliverability_circuit_breaker_pauses_autosend_and_escalates(conn):
    _recent_email_sample(conn, size=25, bounced=1)
    settings.set_value(conn, "reply_sync_last_status", "success")
    autosend.set_enabled(conn, True)

    result = oversight.evaluate(conn)

    assert result["paused"] is True
    assert autosend.enabled(conn) is False
    assert autosend.status(conn)["safety_pause"]["code"] == "bounce_rate"
    p = proposals.list_proposals(conn)[0]
    assert p["kind"] == "create_task" and "暂停" in p["title"]
    assert "4.0%" in p["reasoning"]


def test_blind_bounce_measurement_is_not_treated_as_a_healthy_zero(conn):
    _recent_email_sample(conn, size=25)
    settings.set_value(conn, "reply_sync_last_status", "error")
    autosend.set_enabled(conn, True)
    result = oversight.evaluate(conn)
    assert result["paused"] is True
    assert result["code"] == "deliverability_blind"


def test_small_or_healthy_samples_do_not_trigger_the_circuit_breaker(conn):
    _recent_email_sample(conn, size=24, bounced=1)
    settings.set_value(conn, "reply_sync_last_status", "success")
    autosend.set_enabled(conn, True)
    assert oversight.evaluate(conn)["paused"] is False
    assert autosend.enabled(conn) is True


def test_an_explicit_resume_clears_the_persisted_safety_pause(conn):
    _recent_email_sample(conn, size=25, bounced=1)
    settings.set_value(conn, "reply_sync_last_status", "success")
    autosend.set_enabled(conn, True)
    oversight.evaluate(conn)
    autosend.set_enabled(conn, True)
    assert autosend.enabled(conn) is True
    assert autosend.status(conn)["safety_pause"] is None


def test_an_existing_safety_pause_stays_visible_in_every_agent_run(conn, monkeypatch):
    _recent_email_sample(conn, size=25, bounced=1)
    settings.set_value(conn, "reply_sync_last_status", "success")
    autosend.set_enabled(conn, True)
    first = oversight.evaluate(conn)
    assert first["paused"] is True

    second = oversight.evaluate(conn)
    assert second["paused"] is True and second["already_paused"] is True
    assert second["code"] == "bounce_rate"
    assert len(proposals.list_proposals(conn, status=None, kind="create_task")) == 1

    monkeypatch.setattr("app.agent.classify.run",
                        lambda c: {"classified": 0, "pending": 0, "note": ""})
    monkeypatch.setattr(run, "act_on_replies", lambda c: {
        "draft": 0, "nudge": 0, "reject": 0, "quote": 0, "errors": [],
    })
    result = run.run_once(conn, dt.datetime(2026, 8, 20, 15, 0))
    assert result["safety_paused"] is True


def test_weak_sequences_are_quarantined_from_new_autonomous_enrollment(conn):
    sid = sequences.create_sequence(conn, "Weak English", "email", [
        {"day_offset": 0, "subject": "Hello", "body": "Hello"},
    ])
    _recent_email_sample(conn, size=25)
    conn.execute("UPDATE send_log SET campaign='序列:Weak English'")
    for no in range(100, 125):
        conn.execute(
            "INSERT OR REPLACE INTO outreach(lead_no,channel,status) VALUES (?, 'email', 'messaged')",
            (no,),
        )
    conn.commit()
    assert sid in oversight.weak_sequence_ids(conn)
    from app.agent import executors
    assert executors._sequence_for_country(conn, "USA") is None


def test_market_allocation_explores_first_then_uses_real_reply_rate(conn, monkeypatch):
    monkeypatch.setattr("app.campaigns.country_stats", lambda c, min_touched=0: [
        {"country": "USA", "touched": 40, "replied": 4, "reply_rate": 10.0},
        {"country": "South Korea", "touched": 8, "replied": 0, "reply_rate": 0.0},
    ])
    assert mission.choose_market(conn, ["USA", "South Korea"]) == "South Korea"

    monkeypatch.setattr("app.campaigns.country_stats", lambda c, min_touched=0: [
        {"country": "USA", "touched": 40, "replied": 4, "reply_rate": 10.0},
        {"country": "South Korea", "touched": 30, "replied": 1, "reply_rate": 3.3},
    ])
    assert mission.choose_market(conn, ["USA", "South Korea"]) == "USA"


def test_daily_outcome_explains_a_missed_target(conn):
    result = oversight.daily_outcome(conn)
    assert result["achieved"] == 0 and result["target"] == 5
    assert result["completion_pct"] == 0
    assert any(b["code"] == "no_discovery" for b in result["blockers"])


def test_every_full_agent_run_has_a_durable_success_or_failure_record(conn, monkeypatch):
    monkeypatch.setattr("app.agent.classify.run", lambda c: {"classified": 0, "note": ""})
    monkeypatch.setattr(run, "act_on_replies", lambda c: {
        "draft": 0, "nudge": 0, "reject": 0, "quote": 0, "errors": [],
    })
    run.run_once(conn, dt.datetime(2026, 8, 20, 15, 0))
    latest = oversight.latest_runs(conn)
    assert latest[0]["status"] == "success" and latest[0]["result"]["classified"] == 0

    monkeypatch.setattr("app.agent.classify.run",
                        lambda c: (_ for _ in ()).throw(llm.LLMError("backend down")))
    with pytest.raises(llm.LLMError):
        run.run_once(conn, dt.datetime(2026, 8, 20, 15, 5))
    latest = oversight.latest_runs(conn)
    assert latest[0]["status"] == "failed" and "backend down" in latest[0]["error"]
