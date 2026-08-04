import json
from pathlib import Path

from app import blocklist
from app.db import connect, init_schema
from app.migrate import load_leads, load_pipeline_rows, run_migration


def _make_leads_dir(tmp_path: Path) -> Path:
    d = tmp_path / "leads"
    (d / "pipeline" / "email").mkdir(parents=True)
    (d / "generate_led_leads_v4.py").write_text(
        "leads = [\n"
        "    {'no': 1, 'company_en': 'Alpha', 'country': 'USA', 'website': 'a.com',\n"
        "     'phone_whatsapp': '+1 555', 'whatsapp_verified': False, 'source_urls': ['u']},\n"
        "]\n", encoding="utf-8")
    (d / "generate_led_leads_v5.py").write_text(
        "new_entries = [\n"
        "    {'no': 2, 'company_en': 'Beta', 'country': 'Brazil', 'website': 'b.com'},\n"
        "]\n", encoding="utf-8")
    (d / "pipeline" / "email" / "prospects.json").write_text(json.dumps([
        {"no": 1, "company_en": "Alpha", "country": "USA", "email": "a@a.com",
         "status": "messaged", "touch_count": 1, "message_sent_date": "2026-07-01"}
    ]), encoding="utf-8")
    return d


def test_load_leads_follows_chain(tmp_path):
    d = _make_leads_dir(tmp_path)
    leads = load_leads(str(d))
    assert {l["no"] for l in leads} == {1, 2}


def test_load_pipeline_rows(tmp_path):
    d = _make_leads_dir(tmp_path)
    rows = load_pipeline_rows(str(d))
    assert rows[0]["channel"] == "email"
    assert rows[0]["lead_no"] == 1
    assert rows[0]["status"] == "messaged"


def test_run_migration_populates_db(tmp_path):
    d = _make_leads_dir(tmp_path)
    conn = connect(str(tmp_path / "t.db"))
    init_schema(conn)
    run_migration(conn, str(d))
    assert conn.execute("SELECT COUNT(*) c FROM leads").fetchone()["c"] == 2
    assert conn.execute("SELECT COUNT(*) c FROM outreach").fetchone()["c"] == 1
    row = conn.execute("SELECT phone, whatsapp_verified, source_urls FROM leads WHERE no=1").fetchone()
    assert row["phone"] == "+1 555"
    assert row["whatsapp_verified"] == 0
    assert json.loads(row["source_urls"]) == ["u"]


def test_blocked_domains_do_not_come_back_on_re_import(tmp_path):
    """The collector's files are never edited when a lead is deleted, so this replay is
    how a deleted competitor returns. Its pipeline row must be skipped too, or the
    outreach table keeps a row pointing at a lead that no longer exists."""
    d = _make_leads_dir(tmp_path)
    conn = connect(str(tmp_path / "t.db"))
    init_schema(conn)
    blocklist.add(conn, "a.com", "同行")
    assert run_migration(conn, str(d)) == 1
    assert [r["no"] for r in conn.execute("SELECT no FROM leads")] == [2]
    assert conn.execute("SELECT COUNT(*) c FROM outreach").fetchone()["c"] == 0
