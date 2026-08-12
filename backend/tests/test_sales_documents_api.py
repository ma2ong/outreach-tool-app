import app.main as main
from app import contacts, opportunities, sales_documents
from app.db import connect, init_schema
from fastapi.testclient import TestClient


def _client(tmp_path):
    db = str(tmp_path / "t.db")
    conn = connect(db)
    init_schema(conn)
    sales_documents.ensure_schema(conn)
    conn.execute("INSERT INTO leads(no, company_en, country) VALUES (1,'Alpha AV','USA')")
    conn.commit()
    contact = contacts.create(conn, 1, {"name": "Ana", "email": "ana@alpha.test"}, is_primary=True)
    opportunity = opportunities.create(conn, 1, {"title": "Rental LED batch"})
    conn.close()
    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    return TestClient(main.app), contact["id"], opportunity["id"]


def _payload(contact_id, opportunity_id):
    return {
        "lead_no": 1, "contact_id": contact_id, "opportunity_id": opportunity_id,
        "title": "Rental P3.91", "incoterm": "FOB", "shipping": 100,
        "items": [{
            "description": "P3.91 cabinet", "quantity": 10,
            "pricing_unit": "unit", "unit_price": 500,
        }],
    }


def test_quote_and_order_api_workflow(tmp_path):
    client, contact_id, opportunity_id = _client(tmp_path)
    created = client.post("/api/sales/quotes", json=_payload(contact_id, opportunity_id))
    assert created.status_code == 200
    quote = created.json()
    assert quote["total"] == 5100
    quote_id = quote["id"]
    assert client.get("/api/sales/quotes").json()[0]["id"] == quote_id
    assert client.get(f"/api/sales/quotes/{quote_id}").json()["items"][0]["quantity"] == 10

    edited = client.patch(f"/api/sales/quotes/{quote_id}", json={"discount": 100})
    assert edited.status_code == 200 and edited.json()["total"] == 5000
    assert client.post(f"/api/sales/quotes/{quote_id}/status", json={"status": "sent"}).status_code == 200
    assert client.post(f"/api/sales/quotes/{quote_id}/status", json={"status": "accepted"}).status_code == 200
    order = client.post(f"/api/sales/quotes/{quote_id}/order")
    assert order.status_code == 200
    order_id = order.json()["id"]
    updated = client.patch(f"/api/sales/orders/{order_id}", json={
        "status": "deposit", "deposit_amount": 1500, "paid_amount": 1500,
    })
    assert updated.status_code == 200 and updated.json()["balance"] == 3500
    assert client.get("/api/sales/orders").json()[0]["quote_no"] == quote["quote_no"]

    printed = client.get(f"/api/sales/quotes/{quote_id}/print")
    assert printed.status_code == 200
    assert "text/html" in printed.headers["content-type"]
    assert quote["quote_no"] in printed.text


def test_sales_document_api_errors_are_actionable(tmp_path):
    client, contact_id, opportunity_id = _client(tmp_path)
    bad = _payload(contact_id, opportunity_id)
    bad["items"][0]["unit_price"] = -1
    response = client.post("/api/sales/quotes", json=bad)
    assert response.status_code == 400
    assert "单价" in response.json()["detail"]
    assert client.get("/api/sales/quotes/999").status_code == 404
    assert client.patch("/api/sales/orders/999", json={"status": "shipped"}).status_code == 404
