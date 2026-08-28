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


def test_a_high_bounce_rate_reports_but_never_stops_the_sending(conn):
    """docs/67 R2. Allen's instruction, and the reasoning behind it: a bounce says one
    address is wrong, not that the customer should not be contacted and certainly not
    that today is a day to send less. The number is still measured and still shown;
    stopping is his call, not a threshold's."""
    _recent_email_sample(conn, size=25, bounced=1)
    settings.set_value(conn, "reply_sync_last_status", "success")
    autosend.set_enabled(conn, True)

    result = oversight.evaluate(conn)

    assert result["paused"] is False
    assert autosend.enabled(conn) is True
    # docs/75 R3: it is not even reported as something to look at any more. "不要管退信率
    # 多少" — a warning nobody may act on is a number asking to be obeyed.
    assert "warning" not in result


def test_a_bounce_becomes_work_rather_than_a_brake(conn):
    conn.execute("UPDATE leads SET bounced_at=datetime('now') WHERE no=1")
    conn.commit()
    assert oversight.bounce_followup_tasks(conn) >= 1
    task = proposals.list_proposals(conn)[0]
    assert task["kind"] == "create_task"
    assert "另一个联系人" in task["title"] or "退信" in task["title"]


def test_unmeasurable_bounces_do_not_stop_anything_either(conn):
    """docs/67 turned this from a circuit breaker into a warning; docs/75 R3 took the
    warning away too. What a broken inbox actually costs is customer replies, and the
    dashboard says that in its own words rather than through a bounce statistic."""
    _recent_email_sample(conn, size=25)
    settings.set_value(conn, "reply_sync_last_status", "error")
    autosend.set_enabled(conn, True)
    result = oversight.evaluate(conn)
    assert result["paused"] is False
    assert autosend.enabled(conn) is True
    assert "warning" not in result


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
    """Nothing pauses on its own any more (docs/67 R2), but a pause Allen set himself
    must keep showing up — a stop that goes quiet is how a stopped system looks healthy."""
    _recent_email_sample(conn, size=25, bounced=1)
    settings.set_value(conn, "reply_sync_last_status", "success")
    autosend.set_enabled(conn, True)
    autosend.pause(conn, "bounce_rate", "Allen 手动暂停", {"bounce_rate": 4.0})

    second = oversight.evaluate(conn)
    assert second["paused"] is True and second["already_paused"] is True
    assert second["code"] == "bounce_rate"

    monkeypatch.setattr("app.agent.classify.run",
                        lambda c: {"classified": 0, "pending": 0, "note": ""})
    monkeypatch.setattr(run, "act_on_replies", lambda c: {
        "draft": 0, "nudge": 0, "reject": 0, "quote": 0, "errors": [],
    })
    result = run.run_once(conn, dt.datetime(2026, 8, 20, 15, 0))
    assert result["safety_paused"] is True


def test_a_sequence_with_no_replies_is_still_reported_as_weak(conn):
    """The measurement survives docs/75; what it no longer does is act. Quarantining a
    sequence was a gate — the system deciding on a number that a company should hear
    less from us."""
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


def test_a_lead_is_enrolled_in_the_sequence_written_for_its_segment(conn):
    """docs/76: a rental company and an integrator do not get the same opener."""
    from app.agent import executors
    from app.seed_sequences import name_for, seed_all
    seed_all(conn)
    conn.execute("UPDATE leads SET tags='租赁商', country='USA' WHERE no=1")
    conn.execute("UPDATE leads SET tags='系统集成商', country='USA' WHERE no=2")
    conn.commit()
    rental = conn.execute("SELECT * FROM leads WHERE no=1").fetchone()
    install = conn.execute("SELECT * FROM leads WHERE no=2").fetchone()
    picked = {n: executors._sequence_for(conn, dict(r))
              for n, r in (("rental", rental), ("install", install))}
    assert picked["rental"] != picked["install"]
    assert picked["rental"] == conn.execute(
        "SELECT id FROM sequences WHERE name=?", (name_for("rental", False),)).fetchone()[0]


def test_a_lead_with_no_type_still_gets_a_letter(conn):
    """`general` is the fallback because 349 companies have no type — silence would be
    a gate by another name."""
    from app.agent import executors
    from app.seed_sequences import name_for, seed_all
    seed_all(conn)
    conn.execute("UPDATE leads SET tags=NULL, target_fit=NULL, business=NULL,"
                 " hook=NULL, brief=NULL, country='USA' WHERE no=1")
    conn.commit()
    lead = dict(conn.execute("SELECT * FROM leads WHERE no=1").fetchone())
    assert executors._sequence_for(conn, lead) == conn.execute(
        "SELECT id FROM sequences WHERE name=?", (name_for("general", False),)).fetchone()[0]


def test_korea_never_gets_the_english_segment_sequence(conn):
    from app.agent import executors
    from app.seed_sequences import name_for, seed_all
    seed_all(conn)
    conn.execute("UPDATE leads SET tags='租赁商', country='South Korea' WHERE no=1")
    conn.commit()
    lead = dict(conn.execute("SELECT * FROM leads WHERE no=1").fetchone())
    assert executors._sequence_for(conn, lead) == conn.execute(
        "SELECT id FROM sequences WHERE name=?", (name_for("rental", True),)).fetchone()[0]


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


# ------------------------------------------------- Spec 28: blockers point somewhere

def _discovery_proposal(conn, payload):
    import json
    proposals.ensure_schema(conn)
    conn.execute(
        "INSERT INTO agent_proposals(kind,title,payload,risk,status,fingerprint,"
        " created_at,updated_at) VALUES ('discover_run','找客',?,'low','executed',?,"
        " datetime('now'), datetime('now'))",   # UTC, as proposals.create writes it
        (json.dumps(payload, ensure_ascii=False), f"fp-{id(payload)}"))
    conn.commit()


def test_candidates_waiting_to_be_imported_are_not_called_unqualified(conn):
    """14 usable US leads sat in an executed proposal while the screen said no
    candidate had passed the quality gate."""
    _discovery_proposal(conn, {"found": [
        {"domain": "edenusa.com", "fit_score": 100},
        {"domain": "rentforevent.com", "fit_score": 100},
        {"domain": "chipshowledusa.com", "fit_score": 0, "excluded": True},
    ]})
    blockers = oversight.daily_outcome(conn)["blockers"]
    codes = {b["code"] for b in blockers}
    assert "candidates_awaiting_import" in codes
    assert "no_qualified_imports" not in codes
    message = next(b["message"] for b in blockers if b["code"] == "candidates_awaiting_import")
    assert "2" in message and "导入" in message


def test_a_genuinely_empty_auto_import_still_reports_the_quality_gate(conn):
    _discovery_proposal(conn, {"found": [{"domain": "x.com", "fit_score": 10}],
                               "auto_import": {"accepted": 0, "imported": 0}})
    codes = {b["code"] for b in oversight.daily_outcome(conn)["blockers"]}
    assert "no_qualified_imports" in codes
    assert "candidates_awaiting_import" not in codes


def test_the_agent_status_carries_the_pause_so_the_ui_can_offer_a_way_out(conn):
    """Since docs/67 a pause is only ever set by a person; it still has to be visible."""
    _recent_email_sample(conn, size=25, bounced=1)
    settings.set_value(conn, "reply_sync_last_status", "success")
    autosend.set_enabled(conn, True)
    autosend.pause(conn, "bounce_rate", "退信率 4.0% —— 手动停一下",
                   {"sends": 25, "bounce_rate": 4.0})

    pause = run.status(conn)["safety_pause"]
    assert pause["code"] == "bounce_rate"
    assert "退信率" in pause["reason"]
    assert pause["evidence"]["sends"] == 25


# ------------------------------------------------- Spec 29: an informed decision holds

def test_resuming_after_a_manual_pause_holds(conn):
    """Resuming used to survive exactly until the next agent run re-paused it. Nothing
    re-pauses now, but clearing has to actually clear."""
    _recent_email_sample(conn, size=25, bounced=1)
    settings.set_value(conn, "reply_sync_last_status", "success")
    pause = autosend.pause(conn, "bounce_rate", "手动暂停", {"bounce_rate": 4.0})
    assert autosend.enabled(conn) is False

    autosend.set_enabled(conn, True)
    autosend.acknowledge(conn, {"paused": True, "code": "bounce_rate", "pause": pause,
                                "deliverability": {"bounce_rate": 4.0}})
    settings.set_value(conn, "autosend_safety_pause", "")

    again = oversight.evaluate(conn)
    assert again["paused"] is False
    assert autosend.enabled(conn) is True


def test_a_worsening_bounce_rate_is_reported_but_keeps_sending(conn):
    """docs/67 R2: the number goes up, the sending does not stop. Pushing through a bad
    patch by finding better addresses is Allen's call, and this is where he made it."""
    _recent_email_sample(conn, size=25, bounced=1)
    settings.set_value(conn, "reply_sync_last_status", "success")
    autosend.set_enabled(conn, True)

    conn.execute("UPDATE leads SET bounced_at=? WHERE no IN (101,102,103)",
                 (dt.datetime.now(dt.UTC).isoformat(),))      # 4.0% -> 16.0%
    conn.commit()
    worse = oversight.evaluate(conn)
    assert worse["paused"] is False
    assert autosend.enabled(conn) is True
    assert "warning" not in worse
    # The rate is still measured — it just no longer speaks. Bounces turn into work,
    # one dead address at a time.
    assert worse["deliverability"]["bounce_rate"] == 16.0


def test_switching_autosend_off_withdraws_the_acknowledgement(conn):
    _recent_email_sample(conn, size=25, bounced=1)
    settings.set_value(conn, "reply_sync_last_status", "success")
    autosend.set_enabled(conn, True)
    autosend.acknowledge(conn, oversight.evaluate(conn))
    autosend.set_enabled(conn, False)
    assert autosend.risk_ack(conn) is None
