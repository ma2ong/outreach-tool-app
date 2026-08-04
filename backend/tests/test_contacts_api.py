import app.main as main
from app.db import connect, init_schema
from fastapi.testclient import TestClient


def _client(tmp_path):
    db = str(tmp_path / "t.db")
    conn = connect(db)
    init_schema(conn)
    conn.execute("INSERT INTO leads(no, company_en, country) VALUES (1,'Alpha AV','USA')")
    conn.commit()
    conn.close()
    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    return TestClient(main.app)


def test_contact_crud_and_primary_switch(tmp_path):
    client = _client(tmp_path)
    first = client.post("/api/contacts", json={
        "lead_no": 1, "name": "Ana", "email": "ana@alpha.com",
        "role": "decision_maker",
    })
    assert first.status_code == 200 and first.json()["is_primary"] is True
    assert client.get("/api/contacts/stats").json()["named_contacts"] == 1
    second = client.post("/api/contacts", json={
        "lead_no": 1, "name": "Tom", "email": "tom@alpha.com", "role": "technical",
    })
    contact_id = second.json()["id"]
    assert second.json()["is_primary"] is False
    assert len(client.get("/api/contacts?lead_no=1").json()) == 2
    assert client.post(f"/api/contacts/{contact_id}/primary").json()["is_primary"] is True
    updated = client.patch(f"/api/contacts/{contact_id}", json={"title": "CTO"})
    assert updated.status_code == 200 and updated.json()["title"] == "CTO"
    assert client.delete(f"/api/contacts/{contact_id}").status_code == 200
    assert len(client.get("/api/contacts?lead_no=1").json()) == 1


def test_contact_api_validation_and_missing_rows(tmp_path):
    client = _client(tmp_path)
    assert client.post("/api/contacts", json={"lead_no": 1, "name": ""}).status_code == 400
    assert client.post("/api/contacts", json={
        "lead_no": 1, "email": "not-an-email"}).status_code == 400
    assert client.patch("/api/contacts/999", json={"name": "x"}).status_code == 404
    assert client.post("/api/contacts/999/primary").status_code == 404
    assert client.delete("/api/contacts/999").status_code == 404
