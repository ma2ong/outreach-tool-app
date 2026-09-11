import datetime as dt

from app.agent import account_brain, catchup, plan, proposals, world


TODAY = dt.date(2026, 8, 21)


def test_contacted_account_with_no_owner_becomes_due(conn):
    rows = account_brain.due_accounts(conn, today=TODAY, limit=20)
    by_no = {row["lead_no"]: row for row in rows}

    assert 1 in by_no
    # Alpha was touched twice across email + Instagram on 2026-07-01, so the second
    # touch cadence is seven days rather than treating each channel as a new account.
    assert by_no[1]["touch_count"] == 2
    assert by_no[1]["due_date"] == "2026-07-08"
    assert by_no[1]["days_overdue"] == 44
    assert by_no[1]["next_action"]


def test_open_task_owns_the_next_step_and_removes_account_from_brain(conn):
    from app import activities

    activities.create(conn, 1, {
        "title": "Allen 已经安排了跟进",
        "type": "task",
        "due_at": "2026-08-22",
        "priority": "normal",
    })
    assert 1 not in {r["lead_no"] for r in account_brain.due_accounts(
        conn, today=TODAY, limit=20)}


def test_active_sequence_owns_followup_and_removes_account_from_brain(conn):
    conn.executescript("""
        INSERT INTO sequences(id, name, channel, active) VALUES (90, 'Owned followup', 'email', 1);
        INSERT INTO sequence_steps(sequence_id, step_order, day_offset, subject, body)
            VALUES (90, 1, 0, 'Hi', 'Body');
        INSERT INTO sequence_enrollments(lead_no, sequence_id, current_step, status,
                                         enrolled_at, next_due_date)
            VALUES (1, 90, 0, 'active', '2026-08-20', '2026-08-22');
    """)
    conn.commit()

    assert 1 not in {r["lead_no"] for r in account_brain.due_accounts(
        conn, today=TODAY, limit=20)}


def test_safety_net_is_idempotent_across_repeated_agent_cycles(conn):
    first = account_brain.safety_net(conn, today=TODAY, limit=3)
    second = account_brain.safety_net(conn, today=TODAY, limit=3)

    assert first["proposed"] >= 1
    assert second["proposed"] == 0
    open_tasks = proposals.list_proposals(conn, status="pending", kind="create_task")
    assert len(open_tasks) == first["proposed"]
    assert any("Account Brain" in (p["payload"].get("note") or "") for p in open_tasks)


def test_world_exposes_due_followups(conn):
    state = world.build(conn)
    assert "due_followups" in state
    assert any(row["lead_no"] == 1 for row in state["due_followups"])


def test_world_and_summary_treat_approved_execution_as_open_work(conn):
    p = proposals.create(conn, "create_task", lead_no=1, title="正在执行的工作",
                         payload={"title": "正在执行的工作"})
    proposals.mark_approved(conn, p["id"])

    rows = world.build(conn)["already_pending"]
    assert any(row["title"] == "正在执行的工作" and row["status"] == "approved"
               for row in rows)
    assert proposals.summary(conn)["pending"] == 1


def test_plan_dedupe_keeps_distinct_batches_but_collapses_exact_repeats():
    a = {"kind": "send_outreach", "lead_no": None,
         "payload": {"template_id": 1, "channel": "email", "lead_nos": [1, 2]}}
    b = {"kind": "send_outreach", "lead_no": None,
         "payload": {"template_id": 1, "channel": "email", "lead_nos": [3, 4]}}

    assert plan._dedupe_key("2026-08-21", a) == plan._dedupe_key("2026-08-21", a)
    assert plan._dedupe_key("2026-08-21", a) != plan._dedupe_key("2026-08-21", b)


def test_discovery_dedupe_still_allows_one_run_per_market_per_day():
    usa = {"kind": "discover_run", "lead_no": None,
           "payload": {"queries": ["LED integrator"], "country": "USA"}}
    korea = {"kind": "discover_run", "lead_no": None,
             "payload": {"queries": ["LED integrator"], "country": "South Korea"}}
    assert plan._dedupe_key("2026-08-21", usa) != plan._dedupe_key("2026-08-21", korea)


def test_late_start_can_catch_up_plan_before_report_hour(conn, monkeypatch):
    afternoon = dt.datetime(2026, 8, 21, 15, 0)
    assert catchup.due(conn, afternoon) is True

    called = []
    monkeypatch.setattr(catchup.run, "make_plan",
                        lambda c, now: called.append(now) or {"proposed": 2})
    result = catchup.run_if_due(conn, afternoon)
    assert result["ran"] is True and result["proposed"] == 2
    assert called == [afternoon]
    assert catchup.due(conn, dt.datetime(2026, 8, 21, 18, 0)) is False


def test_late_start_respects_existing_retry_cooldown(conn):
    from app import settings

    settings.set_value(conn, "agent_plan_attempt_date", "2026-08-21")
    settings.set_value(conn, "agent_plan_attempts", "1")
    settings.set_value(conn, "agent_plan_last_attempt_at", "2026-08-21T14:45:00")
    assert catchup.due(conn, dt.datetime(2026, 8, 21, 15, 0)) is False
    assert catchup.due(conn, dt.datetime(2026, 8, 21, 15, 15)) is False
    assert catchup.due(conn, dt.datetime(2026, 8, 21, 15, 45)) is True


def test_disabling_email_poll_does_not_disable_the_background_cycle(monkeypatch):
    from app import background_jobs

    monkeypatch.setenv("OUTREACH_AUTO_POLL", "0")
    assert background_jobs.email_poll("unused.db") == {"status": "disabled"}

    called = []
    monkeypatch.setattr(background_jobs, "social_scan", lambda _p: called.append("social") or True)
    monkeypatch.setattr(background_jobs, "website_recheck", lambda _p: called.append("recheck") or True)
    monkeypatch.setattr(background_jobs, "sequence_maintenance", lambda _p: called.append("prune") or True)
    monkeypatch.setattr(background_jobs, "email_send", lambda _p: True)
    monkeypatch.setattr(background_jobs, "social_send", lambda _p: called.append("queue") or True)
    monkeypatch.setattr(background_jobs, "agent", lambda _p: called.append("agent") or True)
    monkeypatch.setattr(background_jobs, "contact_names", lambda _p: called.append("names") or True)

    assert [fn() for _name, fn in background_jobs.ordered_stages("unused.db")]
    assert called == ["social", "recheck", "prune", "queue", "names", "agent"]
