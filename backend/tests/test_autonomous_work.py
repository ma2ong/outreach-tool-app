import datetime as dt

import app.main as main
from app import activities, contacts, enrich
from app.agent import autonomous_work, proposals, task_ownership
from app.db import connect, init_schema
from fastapi.testclient import TestClient


def _research_task(conn, lead_no: int, key: str, *, dedupe: str):
    proposals.set_autonomy(conn, "create_task", "auto")
    return proposals.create(
        conn, "create_task", lead_no=lead_no, title=f"research {key}",
        payload={
            "title": f"research {key}", "type": "task",
            "due_at": dt.date.today().isoformat(), "priority": "normal",
            "completion_rule": {
                "type": "account_brain", "next_action_key": key,
                "context": {}, "baseline_last_touch": "2026-08-01",
            },
        },
        risk="low", dedupe_key=dedupe,
    )


def test_exact_agent_research_is_not_human_work(conn):
    manual = activities.create(conn, 1, {"title": "人工报价确认", "due_at": dt.date.today().isoformat()})
    proposal = _research_task(conn, 1, "refresh_icp", dedupe="owner-research")
    assert proposal and proposal["status"] == "executed"

    result = task_ownership.backfill(conn)
    agent_task = conn.execute(
        "SELECT * FROM activities WHERE source_ref=?", (f"proposal:{proposal['id']}",)
    ).fetchone()
    assert agent_task["work_owner"] == "agent"
    assert conn.execute("SELECT work_owner FROM activities WHERE id=?", (manual["id"],)).fetchone()[0] == "human"
    assert result["owners_changed"] >= 1
    assert task_ownership.stats(conn, "human")["open_count"] == 1
    assert task_ownership.stats(conn, "agent")["open_count"] == 1


def test_refresh_icp_is_done_by_agent(monkeypatch, conn):
    proposal = _research_task(conn, 1, "refresh_icp", dedupe="refresh-icp")
    task_ownership.backfill(conn)

    monkeypatch.setattr(enrich, "enrich_domain", lambda _domain: {
        "pages": 1, "email": None, "phone": None, "instagram": None,
        "facebook": None, "linkedin": None, "email_source": None,
        "brief": "", "hook": "", "buying_signals": [],
        "icp_type": "integrator", "fit_score": 85,
    })

    result = autonomous_work.sweep(conn, limit=5)
    task = conn.execute(
        "SELECT status,work_owner FROM activities WHERE source_ref=?",
        (f"proposal:{proposal['id']}",),
    ).fetchone()
    lead = conn.execute("SELECT target_fit,tags FROM leads WHERE no=1").fetchone()
    assert result["done"] == 1
    assert task["status"] == "done"
    assert task["work_owner"] == "agent"
    assert lead["target_fit"] == "AV集成商 (85)"
    assert "icp:integrator" in (lead["tags"] or "")


def test_unknown_icp_stays_in_hidden_agent_retry_queue(monkeypatch, conn):
    proposal = _research_task(conn, 1, "refresh_icp", dedupe="refresh-unknown")
    task_ownership.backfill(conn)
    monkeypatch.setattr(enrich, "enrich_domain", lambda _domain: {
        "pages": 1, "email": None, "phone": None, "instagram": None,
        "facebook": None, "linkedin": None, "email_source": None,
        "brief": "", "hook": "", "buying_signals": [],
        "icp_type": "unknown", "fit_score": 0,
    })

    result = autonomous_work.sweep(conn, limit=5)
    task = conn.execute(
        "SELECT status,work_owner,due_at FROM activities WHERE source_ref=?",
        (f"proposal:{proposal['id']}",),
    ).fetchone()
    assert result["rescheduled"] == 1
    assert task["status"] == "open"
    assert task["work_owner"] == "agent"
    assert task["due_at"] > dt.date.today().isoformat()


def test_decision_maker_title_evidence_closes_agent_task(monkeypatch, conn):
    proposal = _research_task(conn, 1, "find_decision_maker", dedupe="find-owner")
    task_ownership.backfill(conn)

    def fake_scan(c, lead_no, **_kwargs):
        contacts.create(c, lead_no, {
            "name": "Jane Buyer", "title": "Purchasing Manager",
            "email": "jane@alpha.com", "role": "other",
        }, source="agent.public-site")
        return {"created": 1, "promoted": 1, "candidates": []}

    import app.decision_maker_radar as radar
    monkeypatch.setattr(radar, "scan", fake_scan)
    result = autonomous_work.sweep(conn, limit=5)
    task = conn.execute(
        "SELECT status FROM activities WHERE source_ref=?", (f"proposal:{proposal['id']}",)
    ).fetchone()
    contact = conn.execute("SELECT role,title FROM contacts WHERE lead_no=1 LIMIT 1").fetchone()
    assert result["done"] == 1
    assert task["status"] == "done"
    assert contact["role"] == "other"  # title is evidence; Agent did not assert CRM authority
    assert "Purchasing" in contact["title"]


def test_activity_api_separates_human_and_agent_queues(tmp_path):
    db = str(tmp_path / "owned.db")
    conn = connect(db)
    init_schema(conn)
    conn.execute("INSERT INTO leads(no,company_en,country,website) VALUES (1,'Owned AV','USA','owned.test')")
    conn.commit()
    activities.create(conn, 1, {"title": "human task", "due_at": dt.date.today().isoformat()})
    _research_task(conn, 1, "refresh_icp", dedupe="api-owner")
    task_ownership.backfill(conn)
    conn.close()

    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    try:
        client = TestClient(main.app)
        human = client.get("/api/activities?work_owner=human").json()
        agent = client.get("/api/activities?work_owner=agent").json()
        default_stats = client.get("/api/activities/stats").json()
        agent_stats = client.get("/api/activities/stats?work_owner=agent").json()
        assert [row["title"] for row in human] == ["human task"]
        assert [row["title"] for row in agent] == ["research refresh_icp"]
        assert default_stats["open_count"] == 1
        assert agent_stats["open_count"] == 1
    finally:
        main.app.dependency_overrides.pop(main.get_conn, None)
