import datetime as dt

from app import activities, seeds
from app.agent import autonomous_work, followup_router, proposals, task_ownership


def _task(conn, lead_no: int, key: str, *, autonomy: str = "auto", dedupe: str):
    proposals.set_autonomy(conn, "create_task", autonomy)
    return proposals.create(
        conn, "create_task", lead_no=lead_no, title=f"agent {key}",
        payload={
            "title": f"agent {key}", "type": "task",
            "due_at": dt.date.today().isoformat(), "priority": "normal",
            "completion_rule": {
                "type": "account_brain", "next_action_key": key,
                "context": {}, "baseline_last_touch": "2026-08-01",
            },
        },
        risk="low", dedupe_key=dedupe,
    )


def _email_lead(conn, *, touches: int, tags: str = "租赁商"):
    # Tagged, because the sequence a lead lands on is its customer type's and
    # two English segments send a single letter with nothing to follow up.
    conn.execute(
        "UPDATE leads SET email='buyer@alpha.com',email_status='valid',recheck_due=NULL,"
        "tags=? WHERE no=1", (tags,)
    )
    conn.execute("DELETE FROM outreach WHERE lead_no=1")
    conn.execute(
        "INSERT INTO outreach(lead_no,channel,status,touch_count,message_sent_date)"
        " VALUES (1,'email','messaged',?,?)",
        (touches, (dt.date.today() - dt.timedelta(days=10)).isoformat()),
    )
    conn.commit()


def test_one_prior_email_routes_to_second_approved_sequence_step(conn):
    _email_lead(conn, touches=1)
    seeds.seed_sequences(conn)
    result = followup_router.continue_no_reply(conn, 1)
    enrollment = conn.execute(
        "SELECT e.current_step,e.status,s.name FROM sequence_enrollments e"
        " JOIN sequences s ON s.id=e.sequence_id WHERE e.lead_no=1"
    ).fetchone()
    assert result["status"] == "owned"
    assert result["step_order"] == 1
    assert enrollment["current_step"] == 1
    assert enrollment["status"] == "active"
    assert "英语·Rental" in enrollment["name"]


def test_two_prior_emails_route_to_final_step(conn):
    _email_lead(conn, touches=2)
    result = followup_router.continue_no_reply(conn, 1)
    enrollment = conn.execute(
        "SELECT current_step,status FROM sequence_enrollments WHERE lead_no=1"
    ).fetchone()
    assert result["status"] == "owned"
    assert result["step_order"] == 2
    assert enrollment["current_step"] == 2


def test_three_prior_emails_are_not_followed_indefinitely(conn):
    _email_lead(conn, touches=3)
    result = followup_router.continue_no_reply(conn, 1)
    assert result["status"] == "retired"
    assert result["reason"] == "cold_email_cap_reached"
    assert conn.execute(
        "SELECT COUNT(*) FROM sequence_enrollments WHERE lead_no=1"
    ).fetchone()[0] == 0
    assert conn.execute("SELECT recheck_due FROM leads WHERE no=1").fetchone()[0]


def test_social_only_touch_does_not_start_email_as_a_fake_followup(conn):
    conn.execute("UPDATE leads SET email='buyer@alpha.com',email_status='valid',recheck_due=NULL WHERE no=1")
    conn.execute("DELETE FROM outreach WHERE lead_no=1")
    conn.execute(
        "INSERT INTO outreach(lead_no,channel,status,touch_count,message_sent_date)"
        " VALUES (1,'instagram','messaged',1,?)",
        ((dt.date.today() - dt.timedelta(days=10)).isoformat(),),
    )
    conn.commit()
    result = followup_router.continue_no_reply(conn, 1)
    assert result["status"] == "retired"
    assert result["reason"] == "no_prior_email"
    assert conn.execute("SELECT COUNT(*) FROM sequence_enrollments WHERE lead_no=1").fetchone()[0] == 0


def test_schedule_followup_task_is_closed_after_sequence_ownership(conn):
    _email_lead(conn, touches=1)
    proposal = _task(conn, 1, "schedule_followup", dedupe="followup-owned")
    task_ownership.backfill(conn)
    result = autonomous_work.sweep(conn, limit=5)
    task = conn.execute(
        "SELECT status,work_owner FROM activities WHERE source_ref=?",
        (f"proposal:{proposal['id']}",),
    ).fetchone()
    assert result["done"] == 1
    assert task["status"] == "done"
    assert task["work_owner"] == "agent"
    assert conn.execute(
        "SELECT COUNT(*) FROM sequence_enrollments WHERE lead_no=1 AND status='active'"
    ).fetchone()[0] == 1


def test_safe_machine_task_materializes_even_when_generic_create_task_is_propose(conn, monkeypatch):
    activities.ensure_schema(conn)
    proposal = _task(conn, 1, "refresh_icp", autonomy="propose", dedupe="safe-propose")
    assert proposal["status"] == "pending"
    assert conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0] == 0

    # Keep the live-I/O half deterministic; the assertion here is about ownership /
    # proposal materialization, not website parsing.
    monkeypatch.setattr(autonomous_work, "_refresh_icp", lambda c, task, lead: (
        activities.update(c, task["id"], {"status": "done"}) and "done"
    ))
    result = autonomous_work.sweep(conn, limit=5)
    refreshed = proposals.get(conn, proposal["id"])
    task = conn.execute(
        "SELECT source,work_owner,status FROM activities WHERE source_ref=?",
        (f"proposal:{proposal['id']}",),
    ).fetchone()
    assert result["materialized"]["executed"] == 1
    assert refreshed["status"] == "executed"
    assert task["source"] == "agent"
    assert task["work_owner"] == "agent"
    assert task["status"] == "done"


def test_human_commercial_task_stays_pending_when_create_task_is_propose(conn):
    proposals.set_autonomy(conn, "create_task", "propose")
    proposal = proposals.create(
        conn, "create_task", lead_no=1, title="确认报价价格",
        payload={"title": "确认报价价格", "type": "task", "due_at": dt.date.today().isoformat()},
        risk="low", dedupe_key="human-price-task",
    )
    result = autonomous_work.sweep(conn, limit=5)
    assert proposal["status"] == "pending"
    assert proposals.get(conn, proposal["id"])["status"] == "pending"
    assert result["materialized"]["executed"] == 0
    assert conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0] == 0
