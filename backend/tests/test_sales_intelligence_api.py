import app.main as main
from app import sales_intelligence
from app.db import connect, init_schema
from fastapi.testclient import TestClient


def _client(tmp_path):
    db = str(tmp_path / "t.db")
    conn = connect(db)
    init_schema(conn)
    sales_intelligence.ensure_schema(conn)
    conn.execute(
        "INSERT INTO leads(no, company_en, country, website, target_fit)"
        " VALUES (1,'Alpha AV','USA','alpha.com','AV集成商 (85)')"
    )
    conn.commit()
    conn.close()
    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    return TestClient(main.app)


def _payload():
    return {
        "signal_type": "tender",
        "headline": "Arena LED tender",
        "evidence": "Public tender lists an outdoor LED display package.",
        "source_url": "https://example.gov/tenders/arena-led",
        "confidence": 90,
        "use_case": "Sports",
        "suggested_angle": "Confirm tender schedule and local installation partner.",
    }


def test_sales_intelligence_api_workflow(tmp_path):
    client = _client(tmp_path)
    created = client.post("/api/leads/1/buying-signals", json=_payload())
    assert created.status_code == 200
    signal_id = created.json()["id"]
    assert client.get("/api/buying-signals?status=new").json()[0]["id"] == signal_id

    ranked = client.get("/api/sales-intelligence/ranked").json()
    assert ranked[0]["lead_no"] == 1
    assert len(ranked[0]["components"]) == 5
    assert client.get("/api/sales-intelligence/summary").json()["new_signals"] == 1
    assert client.get("/api/leads/1/intelligence").json()["signals"][0]["id"] == signal_id

    task = client.post(f"/api/buying-signals/{signal_id}/task")
    assert task.status_code == 200 and task.json()["source"] == "signal"
    opportunity = client.post(f"/api/buying-signals/{signal_id}/opportunity")
    assert opportunity.status_code == 200 and opportunity.json()["use_case"] == "Sports"
    assert client.patch(
        f"/api/buying-signals/{signal_id}", json={"status": "dismissed"}
    ).status_code == 200


def test_sales_intelligence_api_rejects_unverifiable_signal(tmp_path):
    client = _client(tmp_path)
    bad = _payload() | {"evidence": "", "source_url": "not-a-url"}
    response = client.post("/api/leads/1/buying-signals", json=bad)
    assert response.status_code == 400
    assert "证据" in response.json()["detail"]
    assert client.get("/api/leads/999/intelligence").status_code == 404
    assert client.post("/api/buying-signals/999/task").status_code == 404
