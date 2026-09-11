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


# docs/114：一个联系人挂多个信箱 / 号码。
def test_extra_channel_add_promote_and_delete(tmp_path):
    client = _client(tmp_path)
    javier = client.post("/api/contacts", json={
        "lead_no": 1, "name": "Javier Carlos", "email": "javier@alpha.com"}).json()
    added = client.post(f"/api/contacts/{javier['id']}/channels",
                        json={"kind": "email", "value": "info@alpha.com"})
    assert added.status_code == 200
    channel_id = added.json()["id"]
    listed = client.get("/api/contacts?lead_no=1").json()
    assert len(listed) == 1 and listed[0]["channels"][0]["value"] == "info@alpha.com"

    promoted = client.post(f"/api/contacts/channels/{channel_id}/primary")
    assert promoted.status_code == 200 and promoted.json()["email"] == "info@alpha.com"
    swapped = promoted.json()["channels"][0]
    assert swapped["value"] == "javier@alpha.com"

    assert client.delete(f"/api/contacts/channels/{swapped['id']}").status_code == 200
    assert client.get("/api/contacts?lead_no=1").json()[0]["channels"] == []
    assert client.delete("/api/contacts/channels/999").status_code == 404


def test_adding_an_address_another_contact_holds_asks_before_merging(tmp_path):
    client = _client(tmp_path)
    javier = client.post("/api/contacts", json={
        "lead_no": 1, "name": "Javier Carlos", "email": "javier@alpha.com"}).json()
    info = client.post("/api/contacts", json={
        "lead_no": 1, "email": "info@alpha.com", "title": "Front desk"}).json()

    clash = client.post(f"/api/contacts/{javier['id']}/channels",
                        json={"kind": "email", "value": "info@alpha.com"})
    assert clash.status_code == 409
    assert clash.json()["detail"]["contact_id"] == info["id"]
    assert len(client.get("/api/contacts?lead_no=1").json()) == 2

    merged = client.post(f"/api/contacts/{javier['id']}/channels",
                         json={"kind": "email", "value": "info@alpha.com", "merge": True})
    assert merged.status_code == 200
    assert [c["value"] for c in merged.json()["channels"]] == ["info@alpha.com"]
    assert merged.json()["title"] == "Front desk"
    assert len(client.get("/api/contacts?lead_no=1").json()) == 1


def test_merging_the_primary_contact_away_is_refused(tmp_path):
    client = _client(tmp_path)
    javier = client.post("/api/contacts", json={
        "lead_no": 1, "name": "Javier", "email": "javier@alpha.com"}).json()
    other = client.post("/api/contacts", json={
        "lead_no": 1, "email": "info@alpha.com"}).json()
    refused = client.post(f"/api/contacts/{other['id']}/channels",
                          json={"kind": "email", "value": "javier@alpha.com", "merge": True})
    assert refused.status_code == 400
    assert len(client.get("/api/contacts?lead_no=1").json()) == 2
