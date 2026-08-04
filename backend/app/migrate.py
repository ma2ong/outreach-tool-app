import ast
import glob
import json
import os
import re
import sqlite3
import sys

DEFAULT_LEADS_DIR = r"C:\Users\Administrator\ai-topic-generator\output\leads"
CHANNELS = ["email", "whatsapp", "instagram", "facebook"]

_LEAD_COLS = [
    "no", "company_en", "company_local", "country", "region", "city",
    "contact_name", "title", "email", "phone", "website", "instagram",
    "facebook", "linkedin", "business", "target_fit", "whatsapp_verified",
    "source_urls",
]


def load_leads(leads_dir: str) -> list[dict]:
    v4 = open(os.path.join(leads_dir, "generate_led_leads_v4.py"), encoding="utf-8").read()
    leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", v4, re.M | re.S).group(1))
    versions = []
    for f in glob.glob(os.path.join(leads_dir, "generate_led_leads_v*.py")):
        m = re.search(r"_v(\d+)\.py$", f)
        if m and int(m.group(1)) >= 5:
            versions.append(int(m.group(1)))
    for n in sorted(versions):
        src = open(os.path.join(leads_dir, f"generate_led_leads_v{n}.py"), encoding="utf-8").read()
        m = re.search(r"^new_entries = (\[.+?^\])", src, re.M | re.S)
        if m:
            leads.extend(ast.literal_eval(m.group(1)))
    return leads


def load_pipeline_rows(leads_dir: str) -> list[dict]:
    rows = []
    for ch in CHANNELS:
        path = os.path.join(leads_dir, "pipeline", ch, "prospects.json")
        if not os.path.exists(path):
            continue
        for rec in json.load(open(path, encoding="utf-8")):
            if rec.get("no") is None:
                continue
            rows.append({
                "lead_no": rec["no"],
                "channel": ch,
                "status": rec.get("status", "prospect"),
                "touch_count": rec.get("touch_count", 0) or 0,
                "message_sent_date": rec.get("message_sent_date") or rec.get("email_sent_date"),
                "reply_received": 1 if rec.get("reply_received") else 0,
                "exclude_reason": rec.get("exclude_reason"),
            })
    return rows


def _lead_values(lead: dict) -> list:
    src = dict(lead)
    src["phone"] = lead.get("phone") or lead.get("phone_whatsapp")
    src["whatsapp_verified"] = 1 if lead.get("whatsapp_verified") else 0
    urls = lead.get("source_urls")
    src["source_urls"] = json.dumps(urls) if urls else None
    return [src.get(c) for c in _LEAD_COLS]


def run_migration(conn: sqlite3.Connection, leads_dir: str = DEFAULT_LEADS_DIR) -> int:
    """Replay the collector's files into the DB. Returns how many rows were skipped for
    being on the never-collect-again list — this replay is exactly how a hand-deleted
    competitor would otherwise come back. Deleting the lead does not edit the collector's
    source files, so the check has to happen on every import."""
    from app import blocklist
    blocked = blocklist.blocked_domains(conn)
    placeholders = ",".join("?" * len(_LEAD_COLS))
    cols = ",".join(_LEAD_COLS)
    skipped: set[int] = set()
    for lead in load_leads(leads_dir):
        if blocklist.match(blocked, lead.get("website"), lead.get("email")):
            skipped.add(lead.get("no"))
            continue
        conn.execute(
            f"INSERT OR REPLACE INTO leads({cols}, updated_at) VALUES ({placeholders}, datetime('now'))",
            _lead_values(lead),
        )
    for r in load_pipeline_rows(leads_dir):
        if r["lead_no"] in skipped:  # its lead was never inserted; this row would orphan
            continue
        conn.execute(
            "INSERT OR REPLACE INTO outreach"
            "(lead_no, channel, status, touch_count, message_sent_date, reply_received, exclude_reason)"
            " VALUES (?,?,?,?,?,?,?)",
            [r["lead_no"], r["channel"], r["status"], r["touch_count"],
             r["message_sent_date"], r["reply_received"], r["exclude_reason"]],
        )
    conn.commit()
    return len(skipped)


if __name__ == "__main__":
    from app.db import connect, init_schema
    leads_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_LEADS_DIR
    db_path = sys.argv[2] if len(sys.argv) > 2 else "outreach.db"
    c = connect(db_path)
    init_schema(c)
    blocked = run_migration(c, leads_dir)
    n = c.execute("SELECT COUNT(*) c FROM leads").fetchone()["c"]
    o = c.execute("SELECT COUNT(*) c FROM outreach").fetchone()["c"]
    print(f"Migrated {n} leads, {o} outreach rows into {db_path}"
          + (f" ({blocked} skipped: 永不再收录)" if blocked else ""))
