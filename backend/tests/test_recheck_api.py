import app.main as main
from app.db import connect, init_schema
from fastapi.testclient import TestClient


def _client(tmp_path, enrich=None):
    import app.api.leads as leads_api
    db = str(tmp_path / "t.db")
    c = connect(db)
    init_schema(c)
    c.execute("INSERT INTO leads(no, company_en, country, website, target_fit)"
              " VALUES (1,'Alpha AV','USA','alpha.com','租赁公司 (90)')")
    c.commit()
    c.close()
    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    leads_api.ENRICH_FN = enrich
    return TestClient(main.app), db


def test_recheck_endpoint_reports_what_it_filled(tmp_path):
    client, _ = _client(tmp_path, enrich=lambda d: {
        "email": "ventas@alpha.com", "email_source": "site.contact-page",
        "brief": "Alpha AV is an event rental company. It lists P3.9 panels.",
        "hook": "Saw P3.9 panels listed on your site."})
    r = client.post("/api/leads/1/recheck")
    assert r.status_code == 200
    body = r.json()
    assert body["changed"] is True
    assert body["lead"]["email"] == "ventas@alpha.com"
    assert body["lead"]["email_source"] == "site.contact-page"
    assert body["lead"]["hook"] == "Saw P3.9 panels listed on your site."
    assert body["lead"]["recheck_due"]


def test_recheck_endpoint_404s_on_a_missing_lead(tmp_path):
    client, _ = _client(tmp_path, enrich=lambda d: {})
    assert client.post("/api/leads/999/recheck").status_code == 404


def test_recheck_endpoint_reports_an_unreachable_site(tmp_path):
    def boom(domain):
        raise RuntimeError("timeout")

    client, _ = _client(tmp_path, enrich=boom)
    r = client.post("/api/leads/1/recheck")
    assert r.status_code == 400 and "timeout" in r.json()["detail"]


def test_editing_the_address_by_hand_stamps_it_as_manual(tmp_path):
    """Where a value came from decides how much it is worth: a typed address and one
    scraped off a footer are not the same evidence."""
    client, _ = _client(tmp_path)
    r = client.patch("/api/leads/1", json={"email": "carlos@alpha.com"})
    assert r.status_code == 200
    assert r.json()["email_source"] == "manual"


def test_editing_something_else_leaves_the_stamp_alone(tmp_path):
    client, _ = _client(tmp_path)
    client.patch("/api/leads/1", json={"email": "carlos@alpha.com"})
    client.patch("/api/leads/1", json={"city": "Dallas"})
    assert client.get("/api/leads/1").json()["email_source"] == "manual"
