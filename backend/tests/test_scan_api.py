import app.main as main
import app.api.channels as channels_api
from app.browser_engine import FakeEngine
from app.db import connect, init_schema
from fastapi.testclient import TestClient


def _client(tmp_path):
    db = str(tmp_path / "t.db")
    c = connect(db)
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, phone, instagram) VALUES
            (1,'Alpha','+55 11 98888-7777','alpha_ig');
        INSERT INTO outreach(lead_no, channel, status, touch_count) VALUES
            (1,'whatsapp','messaged',1);
    """)
    c.commit()
    c.close()
    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    engine = channels_api.ENGINE = FakeEngine()
    return TestClient(main.app), engine


def test_scan_without_a_connected_channel_says_what_to_do(tmp_path):
    """Scanning a logged-out session returns an empty list, which would read as
    'no replies' — the same false negative that hid every reply for weeks."""
    client, _ = _client(tmp_path)
    r = client.post("/api/replies/scan")
    assert r.status_code == 400
    assert "渠道" in r.json()["detail"]


def test_scan_reads_connected_channels_and_skips_the_rest(tmp_path):
    client, engine = _client(tmp_path)
    engine.simulate_login("whatsapp")
    engine.threads["whatsapp"] = [{
        "sender": "+55 11 98888-7777", "name": "+55 11 98888-7777",
        "preview": "please quote P3", "outgoing": False, "unread": True}]

    body = client.post("/api/replies/scan").json()
    assert body["replies"] == 1 and body["stored"] == 1
    assert body["skipped"] == ["instagram"]

    inbox = client.get("/api/inbox").json()
    assert [(m["channel"], m["kind"], m["body"]) for m in inbox] == \
        [("whatsapp", "reply", "please quote P3")]


def test_scan_status_reports_the_last_sweep(tmp_path):
    client, engine = _client(tmp_path)
    engine.simulate_login("whatsapp")
    client.post("/api/replies/scan")
    body = client.get("/api/replies/scan/status").json()
    assert body["last_at"] and body["last_result"]["threads"] == 0
