"""Never-collect-again list. Deleting a lead is not enough on its own: the collector's
files still hold the company and `app.migrate` replays them, so every import path has to
consult this list or the deleted competitor walks back in."""
import pytest

import app.main as main
from app import blocklist, repository as repo
from app.db import connect, init_schema


def test_domain_from_website_email_and_url():
    assert blocklist.domain_of("https://www.XcolorLEDusa.com/about") == "xcolorledusa.com"
    assert blocklist.domain_of("info@xcolorledusa.com") == "xcolorledusa.com"
    assert blocklist.domain_of("") is None


def test_insert_lead_refuses_a_blocked_domain(conn):
    blocklist.add(conn, "https://xcolorledusa.com", "同行")
    with pytest.raises(blocklist.BlockedLead):
        repo.insert_lead(conn, {"company_en": "XcolorLED USA", "website": "xcolorledusa.com"})
    # matched on the email too — a record may carry no website at all
    with pytest.raises(blocklist.BlockedLead):
        repo.insert_lead(conn, {"company_en": "Xcolor", "email": "sales@xcolorledusa.com"})
    # and on a subdomain, which is still the same company
    with pytest.raises(blocklist.BlockedLead):
        repo.insert_lead(conn, {"company_en": "Xcolor", "website": "shop.xcolorledusa.com"})


def test_unrelated_lead_still_inserts(conn):
    blocklist.add(conn, "xcolorledusa.com")
    no = repo.insert_lead(conn, {"company_en": "Real Customer", "website": "realcustomer.com"})
    assert repo.get_lead(conn, no).company_en == "Real Customer"


def test_removing_the_block_lets_it_back_in(conn):
    row = blocklist.add(conn, "xcolorledusa.com")
    assert blocklist.remove(conn, row["id"]) is True
    assert repo.insert_lead(conn, {"company_en": "Xcolor", "website": "xcolorledusa.com"})


def test_blocking_the_same_domain_twice_is_one_row(conn):
    blocklist.add(conn, "https://www.xcolorledusa.com/")
    blocklist.add(conn, "info@xcolorledusa.com")
    assert [r["domain"] for r in blocklist.list_all(conn)] == ["xcolorledusa.com"]


def _client(tmp_path):
    db = str(tmp_path / "t.db")
    c = connect(db)
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, website, email) VALUES
            (1,'XcolorLED USA','USA','xcolorledusa.com','info@xcolorledusa.com'),
            (2,'Real Customer','USA','realcustomer.com', NULL);
    """)
    c.commit()
    c.close()
    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    from fastapi.testclient import TestClient
    return TestClient(main.app)


def test_delete_with_block_adds_the_domain(tmp_path):
    client = _client(tmp_path)
    r = client.delete("/api/leads/1?block=1")
    assert r.json()["blocked_domain"] == "xcolorledusa.com"
    assert [b["domain"] for b in client.get("/api/blocklist").json()] == ["xcolorledusa.com"]


def test_delete_without_block_leaves_the_list_alone(tmp_path):
    client = _client(tmp_path)
    assert client.delete("/api/leads/2").json()["blocked_domain"] is None
    assert client.get("/api/blocklist").json() == []


def test_blocklist_api_add_and_remove(tmp_path):
    client = _client(tmp_path)
    row = client.post("/api/blocklist", json={"value": "info@rival.com", "reason": "同行"}).json()
    assert row["domain"] == "rival.com"
    assert client.delete(f"/api/blocklist/{row['id']}").status_code == 200
    assert client.get("/api/blocklist").json() == []


def test_blocklist_api_rejects_a_value_with_no_domain(tmp_path):
    assert _client(tmp_path).post("/api/blocklist", json={"value": "  "}).status_code == 400
