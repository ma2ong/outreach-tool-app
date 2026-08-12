import datetime as dt

import pytest

from app import contacts, dedupe, opportunities, repository, sales_documents


def _setup(conn, lead_no=100):
    conn.execute(
        "INSERT INTO leads(no, company_en, country, website) VALUES (?,?,?,?)",
        (lead_no, "Buyer <AV>", "USA", "buyer.example"),
    )
    conn.commit()
    contact = contacts.create(conn, lead_no, {
        "name": "Jane <script>alert(1)</script>",
        "title": "Purchasing", "email": "jane@buyer.example",
    }, is_primary=True)
    opportunity = opportunities.create(conn, lead_no, {"title": "Church wall"})
    return contact, opportunity


def _items():
    return [
        {
            "description": "Main screen", "model": "MX-P2.5", "pixel_pitch": "P2.5",
            "width_m": 2.5, "height_m": 1.75, "quantity": 2,
            "pricing_unit": "sqm", "unit_price": 1000,
        },
        {
            "description": "Spare module", "quantity": 4,
            "pricing_unit": "unit", "unit_price": 50,
        },
    ]


def test_quote_calculation_send_and_order_flow(conn, monkeypatch):
    contact, opportunity = _setup(conn)
    monkeypatch.setattr(sales_documents.dt, "date", type(
        "FixedDate", (dt.date,), {"today": classmethod(lambda cls: cls(2026, 8, 11))}
    ))
    quote = sales_documents.create_quote(conn, 100, {
        "title": "P2.5 <Lobby>", "opportunity_id": opportunity["id"],
        "contact_id": contact["id"], "shipping": 300, "discount": 50,
        "incoterm": "CIF", "destination": "Los Angeles",
    }, _items())
    assert quote["quote_no"] == "MCV-202608-0001"
    assert quote["subtotal"] == 8950
    assert quote["total"] == 9200
    assert quote["items"][0]["area_sqm"] == 8.75
    assert quote["items"][0]["line_total"] == 8750
    assert quote["items"][1]["line_total"] == 200

    sent = sales_documents.set_quote_status(conn, quote["id"], "sent")
    assert sent["status"] == "sent"
    deal = opportunities.get(conn, opportunity["id"], today=dt.date(2026, 8, 11))
    assert deal["stage"] == "quoted"
    assert deal["amount"] == 9200
    assert deal["next_action_date"] == "2026-08-14"
    task = conn.execute(
        "SELECT * FROM activities WHERE opportunity_id=? AND status='open'", (opportunity["id"],)
    ).fetchone()
    assert task["title"] == f"跟进报价 {quote['quote_no']}"
    assert task["due_at"] == "2026-08-14"

    accepted = sales_documents.set_quote_status(conn, quote["id"], "accepted")
    assert accepted["accepted_at"]
    order = sales_documents.create_order(conn, quote["id"])
    assert order["order_no"] == "MCO-202608-0001"
    assert order["total"] == 9200
    assert order["balance"] == 9200
    assert opportunities.get(conn, opportunity["id"])["stage"] == "won"
    assert conn.execute(
        "SELECT status FROM activities WHERE opportunity_id=?", (opportunity["id"],)
    ).fetchone()["status"] == "cancelled"

    order = sales_documents.update_order(conn, order["id"], {
        "status": "deposit", "deposit_amount": 2800, "paid_amount": 2800,
    })
    assert order["balance"] == 6400
    order = sales_documents.update_order(conn, order["id"], {"status": "production"})
    order = sales_documents.update_order(conn, order["id"], {"status": "inspection"})
    order = sales_documents.update_order(conn, order["id"], {
        "status": "shipped", "tracking_no": "MAEU123", "note": "Packed in flight cases",
    })
    assert order["shipped_at"] == "2026-08-11"
    assert order["note"] == "Packed in flight cases"
    with pytest.raises(sales_documents.SalesDocumentValidation, match="尾款"):
        sales_documents.update_order(conn, order["id"], {"status": "completed"})
    complete = sales_documents.update_order(conn, order["id"], {
        "status": "completed", "paid_amount": 9200,
    })
    assert complete["balance"] == 0


def test_quote_validation_and_state_guards(conn):
    contact, opportunity = _setup(conn)
    with pytest.raises(sales_documents.SalesDocumentValidation, match="宽度和高度"):
        sales_documents.create_quote(conn, 100, {
            "title": "Bad", "opportunity_id": opportunity["id"],
        }, [{"description": "screen", "pricing_unit": "sqm", "quantity": 1, "unit_price": 1}])
    with pytest.raises(sales_documents.SalesDocumentValidation, match="折扣"):
        sales_documents.create_quote(conn, 100, {"title": "Bad", "discount": 9999}, _items())

    quote = sales_documents.create_quote(conn, 100, {
        "title": "Valid", "opportunity_id": opportunity["id"], "contact_id": contact["id"],
    }, _items())
    with pytest.raises(sales_documents.SalesDocumentValidation, match="不能从"):
        sales_documents.set_quote_status(conn, quote["id"], "accepted")
    sales_documents.set_quote_status(conn, quote["id"], "sent")
    with pytest.raises(sales_documents.SalesDocumentValidation, match="只有草稿"):
        sales_documents.update_quote(conn, quote["id"], {"title": "Changed"})
    with pytest.raises(sales_documents.SalesDocumentValidation, match="只有已接受"):
        sales_documents.create_order(conn, quote["id"])
    sales_documents.set_quote_status(conn, quote["id"], "accepted")
    sales_documents.create_order(conn, quote["id"])
    with pytest.raises(sales_documents.SalesDocumentValidation, match="已经生成"):
        sales_documents.create_order(conn, quote["id"])


def test_closed_opportunity_rolls_back_quote_and_order_changes(conn):
    contact, opportunity = _setup(conn)
    blocked_send = sales_documents.create_quote(conn, 100, {
        "title": "Do not send", "opportunity_id": opportunity["id"],
        "contact_id": contact["id"],
    }, _items())
    opportunities.update(conn, opportunity["id"], {
        "stage": "lost", "loss_reason": "Project cancelled",
    })
    with pytest.raises(sales_documents.SalesDocumentValidation, match="已关闭"):
        sales_documents.set_quote_status(conn, blocked_send["id"], "sent")
    assert sales_documents.get_quote(conn, blocked_send["id"])["status"] == "draft"

    second = opportunities.create(conn, 100, {"title": "Second project"})
    accepted = sales_documents.create_quote(conn, 100, {
        "title": "Accepted then cancelled", "opportunity_id": second["id"],
        "contact_id": contact["id"],
    }, _items())
    sales_documents.set_quote_status(conn, accepted["id"], "sent")
    sales_documents.set_quote_status(conn, accepted["id"], "accepted")
    opportunities.update(conn, second["id"], {
        "stage": "lost", "loss_reason": "Customer cancelled after acceptance",
    })
    with pytest.raises(sales_documents.SalesDocumentValidation, match="不可成交"):
        sales_documents.create_order(conn, accepted["id"])
    assert conn.execute(
        "SELECT COUNT(*) FROM orders WHERE quote_id=?", (accepted["id"],)
    ).fetchone()[0] == 0


def test_draft_edit_recalculates_and_print_escapes_html(conn):
    contact, opportunity = _setup(conn)
    quote = sales_documents.create_quote(conn, 100, {
        "title": "P2.5 <Lobby>", "opportunity_id": opportunity["id"],
        "contact_id": contact["id"], "payment_terms": "30% <deposit>",
    }, _items())
    edited = sales_documents.update_quote(conn, quote["id"], {"shipping": 100}, [{
        "description": "One cabinet", "quantity": 3, "pricing_unit": "unit", "unit_price": 99.995,
        "note": "Spare <serial> batch",
    }])
    assert edited["subtotal"] == 300
    assert edited["total"] == 400
    page = sales_documents.print_quote_html(conn, quote["id"])
    assert "Buyer &lt;AV&gt;" in page
    assert "P2.5 &lt;Lobby&gt;" in page
    assert "&lt;script&gt;" in page and "<script>" not in page
    assert "Spare &lt;serial&gt; batch" in page
    assert "USD 400.00" in page


def test_delete_health_and_dedupe_preserve_sales_documents(conn):
    contact, opportunity = _setup(conn)
    quote = sales_documents.create_quote(conn, 100, {
        "title": "Persistent quote", "opportunity_id": opportunity["id"], "contact_id": contact["id"],
    }, _items())
    assert repository.delete_lead(conn, 100) is True
    assert sales_documents.get_quote(conn, quote["id"]) is None

    keep_contact, _ = _setup(conn, 200)
    conn.execute("INSERT INTO leads(no, company_en, country, website) VALUES (201,'Duplicate','USA','buyer.example')")
    conn.commit()
    duplicate_contact = contacts.create(conn, 201, {
        "name": "Jane Duplicate", "email": "jane@buyer.example",
    }, is_primary=True)
    quote = sales_documents.create_quote(conn, 201, {
        "title": "Move me", "contact_id": duplicate_contact["id"],
    }, _items())
    dedupe.merge_leads(conn, 200, [201])
    moved = sales_documents.get_quote(conn, quote["id"])
    assert moved["lead_no"] == 200
    assert moved["contact_id"] == keep_contact["id"]
