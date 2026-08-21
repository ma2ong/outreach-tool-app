import datetime as dt

from app import main
from app.agent import account_brain, plan, proposals, world


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


def test_world_treats_approved_execution_as_already_open_work(conn):
    p = proposals.create(conn, "create_task", lead_no=1, title="正在执行的工作",
                         payload={"title": "正在执行的工作"})
    proposals.mark_approved(conn, p["id"])

    rows = world.build(conn)["already_pending"]
    assert any(row["title"] == "正在执行的工作" and row["status"] == "approved"
               for row in rows)


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


def test_disabling_email_poll_does_not_disable_the_background_cycle(monkeypatch):
    monkeypatch.setenv("OUTREACH_AUTO_POLL", "0")
    assert main.auto_poll_replies() is True

    called = []
    monkeypatch.setattr(main, "auto_scan_social", lambda: called.append("social"))
    monkeypatch.setattr(main, "auto_recheck", lambda: called.append("recheck"))
    monkeypatch.setattr(main, "auto_prune_sequences", lambda: called.append("prune"))
    monkeypatch.setattr(main, "auto_agent_run", lambda: called.append("agent"))

    assert main.background_cycle() is True
    assert called == ["social", "recheck", "prune", "agent"]
