import datetime as dt

import app.main as main
from app import activities
from app.agent import control_center, proposals
from app.db import connect, init_schema
from fastapi.testclient import TestClient


def test_execution_mode_uses_existing_decision_and_execution_timestamps():
    assert control_center.execution_mode({"status": "pending"}) == "awaiting_approval"
    assert control_center.execution_mode({"status": "approved"}) == "executing"
    assert control_center.execution_mode({
        "status": "executed", "executed_at": "2026-08-24T08:00:00+00:00", "decided_at": None,
    }) == "auto"
    assert control_center.execution_mode({
        "status": "executed", "executed_at": "2026-08-24T08:00:00+00:00",
        "decided_at": "2026-08-24T07:59:00+00:00",
    }) == "approved"


def test_control_center_receipts_do_not_expose_reply_addresses():
    reply = control_center._receipt_result({
        "kind": "reply_draft", "status": "executed",
        "execution_result": "已从 sales@example.com 回复 buyer@customer.com",
    })
    generic = control_center._receipt_result({
        "kind": "send_outreach", "status": "executed",
        "execution_result": "已发 3 封，sender@example.com 无异常",
    })
    assert reply == "客户回复已执行"
    assert "@" not in generic
    assert "[email]" in generic


def test_snapshot_surfaces_high_risk_approval_without_mutating_crm(conn):
    activities.ensure_schema(conn)
    p = proposals.create(
        conn, "mark_do_not_contact", lead_no=1, title="需要人工确认停发",
        payload={"reason": "customer asked to stop"}, risk="high",
    )
    before_proposals = conn.execute("SELECT COUNT(*) FROM agent_proposals").fetchone()[0]
    before_activities = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]

    snap = control_center.snapshot(
        conn, now=dt.datetime(2026, 8, 24, 8, 0, tzinfo=dt.UTC),
    )

    assert snap["counters"]["awaiting_approval"] >= 1
    assert snap["counters"]["high_risk_approval"] >= 1
    assert any(b["code"] == "high_risk_approvals" for b in snap["blockers"])
    receipt = next(item for item in snap["approval_backlog"] if item["id"] == p["id"])
    assert receipt["mode"] == "awaiting_approval"
    assert conn.execute("SELECT COUNT(*) FROM agent_proposals").fetchone()[0] == before_proposals
    assert conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0] == before_activities


def test_snapshot_ledger_distinguishes_auto_from_human_approved(conn):
    proposals.set_autonomy(conn, "create_task", "auto")
    auto = proposals.create(
        conn, "create_task", lead_no=2, title="Agent 自动内部任务",
        payload={"title": "Agent 自动内部任务", "due_at": "2026-08-24"}, risk="low",
        dedupe_key="auto-control-center-test",
    )
    assert auto["status"] == "executed" and auto["decided_at"] is None

    proposals.set_autonomy(conn, "create_task", "propose")
    approved = proposals.create(
        conn, "create_task", lead_no=3, title="人工确认内部任务",
        payload={"title": "人工确认内部任务", "due_at": "2026-08-24"}, risk="low",
        dedupe_key="approved-control-center-test",
    )
    approved = proposals.approve(conn, approved["id"])
    assert approved["status"] == "executed" and approved["decided_at"]

    snap = control_center.snapshot(conn)
    by_id = {row["id"]: row for row in snap["ledger"]}
    assert by_id[auto["id"]]["mode"] == "auto"
    assert by_id[approved["id"]]["mode"] == "approved"


def test_control_center_api_is_available_on_a_new_database(tmp_path):
    db = str(tmp_path / "control.db")
    conn = connect(db)
    init_schema(conn)
    conn.execute("INSERT INTO leads(no, company_en, country) VALUES (1,'Control AV','USA')")
    conn.commit()
    conn.close()

    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    try:
        client = TestClient(main.app)
        response = client.get("/api/agent/control-center")
        assert response.status_code == 200
        body = response.json()
        assert body["state"] in ("healthy", "attention", "critical")
        assert "awaiting_approval" in body["counters"]
        assert "ledger" in body
    finally:
        main.app.dependency_overrides.pop(main.get_conn, None)
