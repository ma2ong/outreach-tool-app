import app.main as main
from app.db import connect, init_schema
from fastapi.testclient import TestClient


def _client(tmp_path):
    db = str(tmp_path / "t.db")
    c = connect(db)
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, website) VALUES
            (1,'Alpha','USA','a.com'),(2,'Beta','Brazil','b.com');
        INSERT INTO outreach(lead_no, channel, status) VALUES (1,'email','messaged');
    """)
    c.commit()
    c.close()
    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    return TestClient(main.app)


def test_list_leads(tmp_path):
    r = _client(tmp_path).get("/api/leads")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_list_leads_filter(tmp_path):
    r = _client(tmp_path).get("/api/leads?country=USA")
    assert [l["no"] for l in r.json()] == [1]


def test_list_leads_untouched_and_has(tmp_path):
    client = _client(tmp_path)
    r = client.get("/api/leads?status=untouched")
    assert [l["no"] for l in r.json()] == [2]
    r2 = client.get("/api/leads?channel=whatsapp&status=untouched")
    assert [l["no"] for l in r2.json()] == [1, 2]
    r3 = client.get("/api/leads?has=email")
    assert r3.json() == []


def test_get_lead(tmp_path):
    r = _client(tmp_path).get("/api/leads/1")
    assert r.status_code == 200
    assert r.json()["company_en"] == "Alpha"


def test_get_lead_404(tmp_path):
    assert _client(tmp_path).get("/api/leads/999").status_code == 404


def test_stats(tmp_path):
    r = _client(tmp_path).get("/api/stats")
    assert r.json()["total"] == 2


def test_mark_replied(tmp_path):
    client = _client(tmp_path)
    r = client.post("/api/leads/1/reply", json={"channel": "email"})
    assert r.status_code == 200
    lead = client.get("/api/leads/1").json()
    assert {"channel": "email", "status": "replied"}.items() <= {
        k: v for o in lead["outreach"] for k, v in o.items() if o["channel"] == "email"}.items()


def test_mark_replied_upserts_when_no_row(tmp_path):
    client = _client(tmp_path)
    r = client.post("/api/leads/2/reply", json={"channel": "whatsapp"})
    assert r.status_code == 200
    lead = client.get("/api/leads/2").json()
    assert any(o["channel"] == "whatsapp" and o["status"] == "replied" for o in lead["outreach"])


def test_list_leads_pagination_and_total(tmp_path):
    client = _client(tmp_path)
    r = client.get("/api/leads?limit=1&offset=0&sort=no")
    assert r.headers["x-total-count"] == "2"
    assert len(r.json()) == 1
    r2 = client.get("/api/leads?sort=company_en&order=desc")
    assert [l["company_en"] for l in r2.json()] == ["Beta", "Alpha"]


def test_export_xlsx(tmp_path):
    r = _client(tmp_path).get("/api/leads/export?fmt=xlsx")
    assert r.status_code == 200
    assert "spreadsheetml" in r.headers["content-type"]
    assert r.headers["content-disposition"].endswith('.xlsx"')
    assert r.content[:2] == b"PK"  # xlsx is a zip


def test_export_csv_respects_filter(tmp_path):
    r = _client(tmp_path).get("/api/leads/export?fmt=csv&country=USA")
    assert r.status_code == 200
    text = r.content.decode("utf-8-sig")
    assert "Alpha" in text
    assert "Beta" not in text  # Beta is Brazil, filtered out


def test_patch_lead_edits_fields(tmp_path):
    client = _client(tmp_path)
    r = client.patch("/api/leads/1", json={
        "phone": "+56 9 1", "stage": "negotiating", "tags": "hot",
        "contact_name": "Ana Silva", "title": "Purchasing Manager",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["phone"] == "+56 9 1"
    assert body["stage"] == "negotiating"
    assert body["tags"] == "hot"
    assert body["contact_name"] == "Ana Silva"
    assert body["title"] == "Purchasing Manager"
    refreshed = client.get("/api/leads/1").json()
    assert refreshed["contact_name"] == "Ana Silva"
    assert refreshed["title"] == "Purchasing Manager"


def test_patch_lead_404(tmp_path):
    assert _client(tmp_path).patch("/api/leads/999", json={"stage": "won"}).status_code == 404


def test_delete_lead(tmp_path):
    client = _client(tmp_path)
    assert client.delete("/api/leads/1").status_code == 200
    assert client.get("/api/leads/1").status_code == 404
    assert [l["no"] for l in client.get("/api/leads").json()] == [2]


def test_delete_lead_404(tmp_path):
    assert _client(tmp_path).delete("/api/leads/999").status_code == 404


def test_notes_add_and_list(tmp_path):
    client = _client(tmp_path)
    r = client.post("/api/leads/1/notes", json={"text": "打了电话"})
    assert r.status_code == 200
    assert any(n["text"] == "打了电话" for n in r.json()["notes"])
    r2 = client.get("/api/leads/1/notes")
    assert [n["text"] for n in r2.json()] == ["打了电话"]


def test_note_empty_rejected(tmp_path):
    assert _client(tmp_path).post("/api/leads/1/notes", json={"text": "  "}).status_code == 400


def test_mark_replied_bad(tmp_path):
    client = _client(tmp_path)
    assert client.post("/api/leads/999/reply", json={"channel": "email"}).status_code == 404
    assert client.post("/api/leads/1/reply", json={"channel": "telegram"}).status_code == 400


def test_bulk_delete(tmp_path):
    client = _client(tmp_path)
    r = client.post("/api/leads/bulk_delete", json={"nos": [1, 999]})
    # a stale id in the batch is skipped, not an error
    assert r.json() == {"deleted": 1, "blocked_domains": []}
    assert [l["no"] for l in client.get("/api/leads").json()] == [2]


def test_bulk_delete_can_block_the_domains(tmp_path):
    client = _client(tmp_path)
    r = client.post("/api/leads/bulk_delete", json={"nos": [1], "block": True})
    assert r.json()["blocked_domains"] == ["a.com"]
    assert [b["domain"] for b in client.get("/api/blocklist").json()] == ["a.com"]


def _merge_client(tmp_path):
    """Two rows of the same company that automatic dedupe cannot see: different
    websites, different spellings of the name (docs/109)."""
    db = str(tmp_path / "m.db")
    c = connect(db)
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, website, email, contact_name, stage) VALUES
            (119,'PixelFLEX LED','USA','pixel-flex.com','sales@pixel-flex.com',NULL,'contacted'),
            (972,'PixelFLEX','USA','pixelflexled.com',NULL,'Steve Paladino','new'),
            (5,'Other Co','USA','other.com',NULL,NULL,'new');
    """)
    c.commit()
    c.close()
    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    return TestClient(main.app)


def test_manual_merge_folds_the_selected_rows_into_the_kept_one(tmp_path):
    client = _merge_client(tmp_path)
    r = client.post("/api/leads/merge", json={"keep": 119, "dups": [972]})
    assert r.status_code == 200, r.text
    assert r.json()["merged"] == 1
    keeper = r.json()["keep"]
    assert keeper["no"] == 119
    assert keeper["website"] == "pixel-flex.com"      # the kept row wins conflicts
    assert keeper["contact_name"] == "Steve Paladino"  # blanks filled from the dup
    assert [l["no"] for l in client.get("/api/leads").json()] == [5, 119]


def test_manual_merge_can_keep_the_newer_row(tmp_path):
    client = _merge_client(tmp_path)
    r = client.post("/api/leads/merge", json={"keep": 972, "dups": [119]})
    assert r.status_code == 200, r.text
    keeper = r.json()["keep"]
    assert keeper["website"] == "pixelflexled.com"
    assert keeper["email"] == "sales@pixel-flex.com"
    assert keeper["stage"] == "contacted"  # never walks a company back to 'new'


def test_manual_merge_leaves_a_note_on_the_kept_row(tmp_path):
    client = _merge_client(tmp_path)
    client.post("/api/leads/merge", json={"keep": 119, "dups": [972]})
    notes = [n["text"] for n in client.get("/api/leads/119").json()["notes"]]
    assert any("972" in n and "PixelFLEX" in n for n in notes)


def test_manual_merge_refuses_a_single_row_and_a_missing_one(tmp_path):
    client = _merge_client(tmp_path)
    assert client.post("/api/leads/merge", json={"keep": 119, "dups": [119]}).status_code == 400
    assert client.post("/api/leads/merge", json={"keep": 119, "dups": []}).status_code == 400
    r = client.post("/api/leads/merge", json={"keep": 119, "dups": [999]})
    assert r.status_code == 404
    assert "999" in r.json()["detail"]
    assert client.post("/api/leads/merge", json={"keep": 999, "dups": [119]}).status_code == 404


def test_manual_merge_refuses_a_batch_too_big_to_have_been_checked(tmp_path):
    client = _merge_client(tmp_path)
    r = client.post("/api/leads/merge", json={"keep": 119, "dups": list(range(200, 215))})
    assert r.status_code == 400
    assert "10" in r.json()["detail"]
    assert len(client.get("/api/leads").json()) == 3  # nothing merged
