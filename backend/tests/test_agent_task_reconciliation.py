import datetime as dt

from app import activities, contacts
from app.agent import proposals, task_reconciler


def _agent_task(conn, rule: dict) -> tuple[dict, dict]:
    proposals.set_autonomy(conn, "create_task", "auto")
    proposal = proposals.create(
        conn, "create_task", lead_no=1,
        title="Agent lifecycle test",
        payload={
            "title": "Agent lifecycle test",
            "type": "task",
            "due_at": dt.date.today().isoformat(),
            "priority": "normal",
            "completion_rule": rule,
        },
        risk="low",
        dedupe_key=f"reconcile-{dt.datetime.now(dt.UTC).timestamp()}",
    )
    assert proposal and proposal["status"] == "executed"
    activity = conn.execute(
        "SELECT * FROM activities WHERE source_ref=?",
        (f"proposal:{proposal['id']}",),
    ).fetchone()
    assert activity is not None
    return proposal, dict(activity)


def test_pre_pr4_manual_source_bug_is_repaired_only_by_exact_execution_task_id(conn):
    proposal, task = _agent_task(conn, {
        "type": "account_brain", "next_action_key": "generic_followup",
        "baseline_last_touch": "2026-07-01",
    })
    # Recreate the historical PR4 bug: the executor really created this task, but the
    # activity row was incorrectly stamped as manual. The proposal still preserves the
    # exact task id in execution_result.
    conn.execute(
        "UPDATE activities SET source='manual', source_ref=NULL WHERE id=?", (task["id"],)
    )
    conn.commit()

    fixed = task_reconciler.backfill_agent_task_provenance(conn)

    assert fixed == 1
    repaired = activities.get(conn, task["id"])
    assert repaired["source"] == "agent"
    assert repaired["source_ref"] == f"proposal:{proposal['id']}"


def test_unrelated_manual_task_is_not_reclassified_by_provenance_backfill(conn):
    manual = activities.create(conn, 1, {
        "title": "My own manual task", "type": "task",
        "due_at": dt.date.today().isoformat(),
    })

    fixed = task_reconciler.backfill_agent_task_provenance(conn)

    assert fixed == 0
    assert activities.get(conn, manual["id"])["source"] == "manual"


def test_finding_decision_maker_supersedes_multistep_task_instead_of_claiming_done(conn):
    _, task = _agent_task(conn, {
        "type": "account_brain", "next_action_key": "find_decision_maker",
        "baseline_last_touch": "2026-07-01",
    })
    contacts.ensure_schema(conn)
    contacts.create(conn, 1, {
        "name": "Buyer One",
        "title": "Purchasing Manager",
        "role": "decision_maker",
        "email": "buyer@example.com",
    })

    result = task_reconciler.reconcile(conn)

    assert result["superseded"] == 1
    updated = activities.get(conn, task["id"])
    assert updated["status"] == "cancelled"
    assert "下一阶段" in (updated["note"] or "")
