# Lead Store + Read-Only Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the 79-file Python lead chain + 4 pipeline JSONs into a single SQLite database exposed through a FastAPI read API and a React dashboard, so Allen can see all ~925 leads and their outreach status in a browser (milestones S1 + S2 of the design spec).

**Architecture:** Python FastAPI backend over a single SQLite file (`outreach.db`). A one-time migration script imports existing data. A React+Vite SPA calls the read-only JSON API and renders stat cards + a filterable leads table. FastAPI also serves the built frontend so the whole thing runs from one command.

**Tech Stack:** Python 3.14, FastAPI, uvicorn, pytest, httpx (TestClient); SQLite (stdlib `sqlite3`); React 18 + Vite + TypeScript; Playwright (already installed) for a smoke test.

**Spec:** `docs/superpowers/specs/2026-07-02-outreach-tool-design.md` (sub-projects S1 + S2).

---

## File Structure

```
outreach-tool/
  backend/
    requirements.txt
    pytest.ini
    app/
      __init__.py
      db.py              # SQLite connection + schema init
      models.py          # Pydantic response models
      repository.py      # data access: list/get/stats/find_duplicate
      migrate.py         # one-time import from output/leads/*
      main.py            # FastAPI app: API routes + static frontend mount
      api/
        __init__.py
        leads.py         # GET /api/leads, GET /api/leads/{no}
        stats.py         # GET /api/stats
    tests/
      __init__.py
      conftest.py        # in-memory / temp-file db fixture + sample data
      test_db.py
      test_repository.py
      test_migrate.py
      test_api.py
  frontend/
    package.json
    vite.config.ts
    index.html
    src/
      main.tsx
      api.ts             # typed fetch client
      types.ts
      components/
        StatCards.tsx
        LeadsTable.tsx
      App.tsx
    tests/
      smoke.spec.ts      # Playwright smoke test
  README.md
```

Boundary notes: `db.py` owns connection + schema only. `repository.py` owns all SQL queries (nothing else runs raw SQL). `migrate.py` is a standalone script, not imported by the app. API modules are thin — they call the repository and return Pydantic models.

---

### Task 1: Backend scaffold

**Files:**
- Create: `outreach-tool/backend/requirements.txt`
- Create: `outreach-tool/backend/pytest.ini`
- Create: `outreach-tool/backend/app/__init__.py` (empty)
- Create: `outreach-tool/backend/app/api/__init__.py` (empty)
- Create: `outreach-tool/backend/tests/__init__.py` (empty)

- [ ] **Step 1: Create requirements.txt**

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
pydantic==2.10.4
httpx==0.28.1
pytest==8.3.4
```

- [ ] **Step 2: Create pytest.ini**

```ini
[pytest]
testpaths = tests
pythonpath = .
```

- [ ] **Step 3: Create empty package files**

Create `app/__init__.py`, `app/api/__init__.py`, `tests/__init__.py` as empty files.

- [ ] **Step 4: Install deps**

Run: `cd outreach-tool/backend && python -m pip install -r requirements.txt`
Expected: installs without error.

- [ ] **Step 5: Commit**

```bash
git add outreach-tool/backend/requirements.txt outreach-tool/backend/pytest.ini outreach-tool/backend/app/__init__.py outreach-tool/backend/app/api/__init__.py outreach-tool/backend/tests/__init__.py
git commit -m "chore: scaffold outreach-tool backend"
```

---

### Task 2: Database schema + connection

**Files:**
- Create: `outreach-tool/backend/app/db.py`
- Test: `outreach-tool/backend/tests/test_db.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_db.py
from app.db import connect, init_schema


def test_init_schema_creates_tables(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    init_schema(conn)
    names = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    assert {"leads", "outreach"} <= names


def test_outreach_unique_lead_channel(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    init_schema(conn)
    conn.execute("INSERT INTO leads(no, company_en) VALUES (1, 'A')")
    conn.execute("INSERT INTO outreach(lead_no, channel, status) VALUES (1,'email','messaged')")
    import sqlite3
    import pytest
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO outreach(lead_no, channel, status) VALUES (1,'email','prospect')")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd outreach-tool/backend && python -m pytest tests/test_db.py -v`
Expected: FAIL (ModuleNotFoundError: app.db).

- [ ] **Step 3: Write minimal implementation**

```python
# app/db.py
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    no INTEGER PRIMARY KEY,
    company_en TEXT NOT NULL,
    company_local TEXT,
    country TEXT,
    region TEXT,
    city TEXT,
    contact_name TEXT,
    title TEXT,
    email TEXT,
    phone TEXT,
    website TEXT,
    instagram TEXT,
    facebook TEXT,
    linkedin TEXT,
    business TEXT,
    target_fit TEXT,
    whatsapp_verified INTEGER DEFAULT 0,
    source_urls TEXT,
    created_at TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS outreach (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_no INTEGER NOT NULL,
    channel TEXT NOT NULL,
    status TEXT NOT NULL,
    touch_count INTEGER DEFAULT 0,
    message_sent_date TEXT,
    reply_received INTEGER DEFAULT 0,
    exclude_reason TEXT,
    UNIQUE(lead_no, channel)
);
CREATE INDEX IF NOT EXISTS idx_leads_country ON leads(country);
CREATE INDEX IF NOT EXISTS idx_outreach_channel ON outreach(channel, status);
"""


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd outreach-tool/backend && python -m pytest tests/test_db.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add outreach-tool/backend/app/db.py outreach-tool/backend/tests/test_db.py
git commit -m "feat: sqlite schema for leads + outreach"
```

---

### Task 3: Pydantic response models

**Files:**
- Create: `outreach-tool/backend/app/models.py`
- Test: `outreach-tool/backend/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
from app.models import Lead, OutreachStatus, Stats


def test_lead_from_row_parses_source_urls():
    lead = Lead(no=1, company_en="A", source_urls=["https://x.com"],
                outreach=[OutreachStatus(channel="email", status="messaged")])
    assert lead.no == 1
    assert lead.outreach[0].channel == "email"


def test_stats_shape():
    s = Stats(total=10, by_country={"USA": 5}, by_channel_status={"email": {"messaged": 3}})
    assert s.total == 10
    assert s.by_country["USA"] == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd outreach-tool/backend && python -m pytest tests/test_models.py -v`
Expected: FAIL (ModuleNotFoundError: app.models).

- [ ] **Step 3: Write minimal implementation**

```python
# app/models.py
from pydantic import BaseModel


class OutreachStatus(BaseModel):
    channel: str
    status: str
    touch_count: int = 0
    message_sent_date: str | None = None
    reply_received: bool = False
    exclude_reason: str | None = None


class Lead(BaseModel):
    no: int
    company_en: str
    company_local: str | None = None
    country: str | None = None
    region: str | None = None
    city: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    instagram: str | None = None
    facebook: str | None = None
    linkedin: str | None = None
    business: str | None = None
    target_fit: str | None = None
    whatsapp_verified: bool = False
    source_urls: list[str] = []
    outreach: list[OutreachStatus] = []


class Stats(BaseModel):
    total: int
    by_country: dict[str, int]
    by_channel_status: dict[str, dict[str, int]]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd outreach-tool/backend && python -m pytest tests/test_models.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add outreach-tool/backend/app/models.py outreach-tool/backend/tests/test_models.py
git commit -m "feat: pydantic models for lead/outreach/stats"
```

---

### Task 4: Test fixture with sample data

**Files:**
- Create: `outreach-tool/backend/tests/conftest.py`

- [ ] **Step 1: Write conftest fixture**

```python
# tests/conftest.py
import pytest
from app.db import connect, init_schema


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, website, instagram) VALUES
            (1, 'Alpha AV', 'USA', 'alpha.com', 'alphaig'),
            (2, 'Beta Screens', 'USA', 'beta.com', NULL),
            (3, 'Gamma LED', 'Brazil', 'gamma.com', 'gammaig');
        INSERT INTO outreach(lead_no, channel, status, touch_count, message_sent_date) VALUES
            (1, 'email', 'messaged', 1, '2026-07-01'),
            (2, 'email', 'prospect', 0, NULL),
            (1, 'instagram', 'messaged', 1, '2026-07-01'),
            (3, 'whatsapp', 'messaged', 1, '2026-06-30');
    """)
    c.commit()
    return c
```

- [ ] **Step 2: Verify fixture loads (no dedicated test yet)**

Run: `cd outreach-tool/backend && python -m pytest tests/ -v`
Expected: existing tests still PASS (conftest import error would fail collection).

- [ ] **Step 3: Commit**

```bash
git add outreach-tool/backend/tests/conftest.py
git commit -m "test: sample-data db fixture"
```

---

### Task 5: Repository — list, get, find_duplicate

**Files:**
- Create: `outreach-tool/backend/app/repository.py`
- Test: `outreach-tool/backend/tests/test_repository.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_repository.py
from app import repository as repo


def test_list_leads_all(conn):
    leads = repo.list_leads(conn)
    assert len(leads) == 3


def test_list_leads_filter_country(conn):
    leads = repo.list_leads(conn, country="USA")
    assert {l.no for l in leads} == {1, 2}


def test_list_leads_filter_channel_status(conn):
    leads = repo.list_leads(conn, channel="email", status="messaged")
    assert [l.no for l in leads] == [1]


def test_list_leads_search(conn):
    leads = repo.list_leads(conn, search="gamma")
    assert [l.no for l in leads] == [3]


def test_get_lead_includes_outreach(conn):
    lead = repo.get_lead(conn, 1)
    assert lead.company_en == "Alpha AV"
    channels = {o.channel for o in lead.outreach}
    assert channels == {"email", "instagram"}


def test_find_duplicate_by_website(conn):
    assert repo.find_duplicate(conn, website="alpha.com", instagram=None, company_en="X") == 1
    assert repo.find_duplicate(conn, website="new.com", instagram=None, company_en="New") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd outreach-tool/backend && python -m pytest tests/test_repository.py -v`
Expected: FAIL (ModuleNotFoundError: app.repository).

- [ ] **Step 3: Write minimal implementation**

```python
# app/repository.py
import json
import sqlite3

from app.models import Lead, OutreachStatus


def _lead_from_row(row: sqlite3.Row, outreach: list[OutreachStatus]) -> Lead:
    d = dict(row)
    d["whatsapp_verified"] = bool(d.get("whatsapp_verified"))
    raw = d.get("source_urls")
    d["source_urls"] = json.loads(raw) if raw else []
    return Lead(**{k: d.get(k) for k in Lead.model_fields if k != "outreach"}, outreach=outreach)


def _outreach_for(conn: sqlite3.Connection, lead_nos: list[int]) -> dict[int, list[OutreachStatus]]:
    if not lead_nos:
        return {}
    q = "SELECT * FROM outreach WHERE lead_no IN (%s)" % ",".join("?" * len(lead_nos))
    out: dict[int, list[OutreachStatus]] = {}
    for r in conn.execute(q, lead_nos):
        out.setdefault(r["lead_no"], []).append(OutreachStatus(
            channel=r["channel"], status=r["status"], touch_count=r["touch_count"] or 0,
            message_sent_date=r["message_sent_date"], reply_received=bool(r["reply_received"]),
            exclude_reason=r["exclude_reason"],
        ))
    return out


def list_leads(conn, country=None, channel=None, status=None, search=None) -> list[Lead]:
    where, params = [], []
    if country:
        where.append("l.country = ?"); params.append(country)
    if search:
        where.append("(l.company_en LIKE ? OR l.website LIKE ? OR l.city LIKE ?)")
        params += [f"%{search}%"] * 3
    if channel or status:
        sub, sp = [], []
        if channel:
            sub.append("channel = ?"); sp.append(channel)
        if status:
            sub.append("status = ?"); sp.append(status)
        where.append("l.no IN (SELECT lead_no FROM outreach WHERE %s)" % " AND ".join(sub))
        params += sp
    sql = "SELECT l.* FROM leads l"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY l.no"
    rows = list(conn.execute(sql, params))
    om = _outreach_for(conn, [r["no"] for r in rows])
    return [_lead_from_row(r, om.get(r["no"], [])) for r in rows]


def get_lead(conn, no: int) -> Lead | None:
    row = conn.execute("SELECT * FROM leads WHERE no = ?", (no,)).fetchone()
    if row is None:
        return None
    om = _outreach_for(conn, [no])
    return _lead_from_row(row, om.get(no, []))


def find_duplicate(conn, website=None, instagram=None, company_en=None) -> int | None:
    checks = []
    if website:
        checks.append(("website", website))
    if instagram:
        checks.append(("instagram", instagram))
    if company_en:
        checks.append(("company_en", company_en))
    for col, val in checks:
        row = conn.execute(f"SELECT no FROM leads WHERE lower({col}) = lower(?)", (val,)).fetchone()
        if row:
            return row["no"]
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd outreach-tool/backend && python -m pytest tests/test_repository.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add outreach-tool/backend/app/repository.py outreach-tool/backend/tests/test_repository.py
git commit -m "feat: lead repository (list/get/find_duplicate)"
```

---

### Task 6: Repository — stats

**Files:**
- Modify: `outreach-tool/backend/app/repository.py` (append `stats`)
- Test: `outreach-tool/backend/tests/test_repository.py` (append)

- [ ] **Step 1: Write the failing test (append)**

```python
# append to tests/test_repository.py
def test_stats(conn):
    s = repo.stats(conn)
    assert s.total == 3
    assert s.by_country == {"USA": 2, "Brazil": 1}
    assert s.by_channel_status["email"]["messaged"] == 1
    assert s.by_channel_status["email"]["prospect"] == 1
    assert s.by_channel_status["instagram"]["messaged"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd outreach-tool/backend && python -m pytest tests/test_repository.py::test_stats -v`
Expected: FAIL (AttributeError: module 'app.repository' has no attribute 'stats').

- [ ] **Step 3: Write minimal implementation (append to repository.py)**

```python
# append to app/repository.py
from app.models import Stats


def stats(conn) -> Stats:
    total = conn.execute("SELECT COUNT(*) c FROM leads").fetchone()["c"]
    by_country = {r["country"]: r["c"] for r in conn.execute(
        "SELECT country, COUNT(*) c FROM leads WHERE country IS NOT NULL GROUP BY country"
    )}
    by_cs: dict[str, dict[str, int]] = {}
    for r in conn.execute(
        "SELECT channel, status, COUNT(*) c FROM outreach GROUP BY channel, status"
    ):
        by_cs.setdefault(r["channel"], {})[r["status"]] = r["c"]
    return Stats(total=total, by_country=by_country, by_channel_status=by_cs)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd outreach-tool/backend && python -m pytest tests/test_repository.py -v`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add outreach-tool/backend/app/repository.py outreach-tool/backend/tests/test_repository.py
git commit -m "feat: repository stats aggregation"
```

---

### Task 7: Migration script

**Files:**
- Create: `outreach-tool/backend/app/migrate.py`
- Test: `outreach-tool/backend/tests/test_migrate.py`

The migration reuses the existing chain-loader pattern: `generate_led_leads_v4.py` holds the base `leads = [...]`; every `v5+` holds `new_entries = [...]`. Pipelines live in `output/leads/pipeline/{email,whatsapp,instagram,facebook}/prospects.json`, keyed by `no`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_migrate.py
import json
from pathlib import Path

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd outreach-tool/backend && python -m pytest tests/test_migrate.py -v`
Expected: FAIL (ModuleNotFoundError: app.migrate).

- [ ] **Step 3: Write minimal implementation**

```python
# app/migrate.py
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


def run_migration(conn: sqlite3.Connection, leads_dir: str = DEFAULT_LEADS_DIR) -> None:
    placeholders = ",".join("?" * len(_LEAD_COLS))
    cols = ",".join(_LEAD_COLS)
    for lead in load_leads(leads_dir):
        conn.execute(
            f"INSERT OR REPLACE INTO leads({cols}, updated_at) VALUES ({placeholders}, datetime('now'))",
            _lead_values(lead),
        )
    for r in load_pipeline_rows(leads_dir):
        conn.execute(
            "INSERT OR REPLACE INTO outreach"
            "(lead_no, channel, status, touch_count, message_sent_date, reply_received, exclude_reason)"
            " VALUES (?,?,?,?,?,?,?)",
            [r["lead_no"], r["channel"], r["status"], r["touch_count"],
             r["message_sent_date"], r["reply_received"], r["exclude_reason"]],
        )
    conn.commit()


if __name__ == "__main__":
    from app.db import connect, init_schema
    leads_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_LEADS_DIR
    db_path = sys.argv[2] if len(sys.argv) > 2 else "outreach.db"
    c = connect(db_path)
    init_schema(c)
    run_migration(c, leads_dir)
    n = c.execute("SELECT COUNT(*) c FROM leads").fetchone()["c"]
    o = c.execute("SELECT COUNT(*) c FROM outreach").fetchone()["c"]
    print(f"Migrated {n} leads, {o} outreach rows into {db_path}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd outreach-tool/backend && python -m pytest tests/test_migrate.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add outreach-tool/backend/app/migrate.py outreach-tool/backend/tests/test_migrate.py
git commit -m "feat: migration from lead chain + pipelines to sqlite"
```

---

### Task 8: Run migration on real data

**Files:**
- Create: `outreach-tool/backend/outreach.db` (generated; add to .gitignore, do not commit)
- Create: `outreach-tool/.gitignore`

- [ ] **Step 1: Add .gitignore**

```
# outreach-tool/.gitignore
backend/outreach.db
backend/__pycache__/
backend/**/__pycache__/
backend/.pytest_cache/
frontend/node_modules/
frontend/dist/
```

- [ ] **Step 2: Run migration against the real leads dir**

Run: `cd outreach-tool/backend && python -m app.migrate "C:\Users\Administrator\ai-topic-generator\output\leads" outreach.db`
Expected: prints `Migrated 9XX leads, N outreach rows into outreach.db` (leads ~925+).

- [ ] **Step 3: Sanity-check counts**

Run: `cd outreach-tool/backend && python -c "import sqlite3;c=sqlite3.connect('outreach.db');print('leads',c.execute('SELECT COUNT(*) FROM leads').fetchone()[0]);print('email messaged',c.execute(\"SELECT COUNT(*) FROM outreach WHERE channel='email' AND status='messaged'\").fetchone()[0])"`
Expected: leads matches the chain total; email messaged ~291.

- [ ] **Step 4: Commit (gitignore only)**

```bash
git add outreach-tool/.gitignore
git commit -m "chore: gitignore generated db and build artifacts"
```

---

### Task 9: FastAPI app + leads/stats endpoints

**Files:**
- Create: `outreach-tool/backend/app/main.py`
- Create: `outreach-tool/backend/app/api/leads.py`
- Create: `outreach-tool/backend/app/api/stats.py`
- Test: `outreach-tool/backend/tests/test_api.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_api.py
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
    c.commit(); c.close()
    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    return TestClient(main.app)


def test_list_leads(tmp_path):
    r = _client(tmp_path).get("/api/leads")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_list_leads_filter(tmp_path):
    r = _client(tmp_path).get("/api/leads?country=USA")
    assert [l["no"] for l in r.json()] == [1]


def test_get_lead(tmp_path):
    r = _client(tmp_path).get("/api/leads/1")
    assert r.status_code == 200
    assert r.json()["company_en"] == "Alpha"


def test_get_lead_404(tmp_path):
    assert _client(tmp_path).get("/api/leads/999").status_code == 404


def test_stats(tmp_path):
    r = _client(tmp_path).get("/api/stats")
    assert r.json()["total"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd outreach-tool/backend && python -m pytest tests/test_api.py -v`
Expected: FAIL (ModuleNotFoundError: app.main).

- [ ] **Step 3: Write implementations**

```python
# app/main.py
import os
import sqlite3

from fastapi import FastAPI

from app.db import connect
from app.api import leads as leads_api
from app.api import stats as stats_api

DB_PATH = os.environ.get("OUTREACH_DB", "outreach.db")

app = FastAPI(title="Outreach Tool")


def get_conn() -> sqlite3.Connection:
    conn = connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


app.include_router(leads_api.router)
app.include_router(stats_api.router)
```

```python
# app/api/leads.py
from fastapi import APIRouter, Depends, HTTPException

from app import repository as repo
from app.main_deps import get_conn  # see note below
from app.models import Lead

router = APIRouter(prefix="/api")


@router.get("/leads", response_model=list[Lead])
def list_leads(country: str | None = None, channel: str | None = None,
               status: str | None = None, search: str | None = None, conn=Depends(get_conn)):
    return repo.list_leads(conn, country=country, channel=channel, status=status, search=search)


@router.get("/leads/{no}", response_model=Lead)
def get_lead(no: int, conn=Depends(get_conn)):
    lead = repo.get_lead(conn, no)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead not found")
    return lead
```

```python
# app/api/stats.py
from fastapi import APIRouter, Depends

from app import repository as repo
from app.main_deps import get_conn
from app.models import Stats

router = APIRouter(prefix="/api")


@router.get("/stats", response_model=Stats)
def get_stats(conn=Depends(get_conn)):
    return repo.stats(conn)
```

> **Note on `get_conn` location:** to avoid a circular import (main imports the routers, routers need `get_conn`), put `get_conn` and `DB_PATH` in a small `app/main_deps.py` and have `main.py` import from it. Adjust Step 3:

```python
# app/main_deps.py
import os
import sqlite3
from app.db import connect

DB_PATH = os.environ.get("OUTREACH_DB", "outreach.db")


def get_conn() -> sqlite3.Connection:
    conn = connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()
```

```python
# app/main.py  (final version)
from fastapi import FastAPI

from app.main_deps import get_conn  # re-exported for tests
from app.api import leads as leads_api
from app.api import stats as stats_api

app = FastAPI(title="Outreach Tool")
app.include_router(leads_api.router)
app.include_router(stats_api.router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd outreach-tool/backend && python -m pytest tests/test_api.py -v`
Expected: PASS (5 passed). Then run full suite: `python -m pytest -v` → all green.

- [ ] **Step 5: Commit**

```bash
git add outreach-tool/backend/app/main.py outreach-tool/backend/app/main_deps.py outreach-tool/backend/app/api/leads.py outreach-tool/backend/app/api/stats.py outreach-tool/backend/tests/test_api.py
git commit -m "feat: read-only leads + stats API"
```

---

### Task 10: React + Vite scaffold + typed API client

**Files:**
- Create: `outreach-tool/frontend/package.json`
- Create: `outreach-tool/frontend/vite.config.ts`
- Create: `outreach-tool/frontend/index.html`
- Create: `outreach-tool/frontend/src/main.tsx`
- Create: `outreach-tool/frontend/src/types.ts`
- Create: `outreach-tool/frontend/src/api.ts`

- [ ] **Step 1: package.json**

```json
{
  "name": "outreach-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.4",
    "typescript": "^5.7.2",
    "vite": "^6.0.5",
    "@playwright/test": "^1.49.1"
  }
}
```

- [ ] **Step 2: vite.config.ts** (proxy /api to backend during dev; build to dist)

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
  build: { outDir: "dist" },
});
```

- [ ] **Step 3: index.html + main.tsx**

```html
<!-- index.html -->
<!doctype html>
<html lang="zh">
  <head><meta charset="UTF-8" /><title>客户开发工具</title></head>
  <body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body>
</html>
```

```tsx
// src/main.tsx
import React from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";

createRoot(document.getElementById("root")!).render(<App />);
```

- [ ] **Step 4: types.ts + api.ts**

```typescript
// src/types.ts
export interface OutreachStatus {
  channel: string; status: string; touch_count: number;
  message_sent_date: string | null; reply_received: boolean; exclude_reason: string | null;
}
export interface Lead {
  no: number; company_en: string; country: string | null; city: string | null;
  email: string | null; phone: string | null; website: string | null;
  instagram: string | null; business: string | null; outreach: OutreachStatus[];
}
export interface Stats {
  total: number; by_country: Record<string, number>;
  by_channel_status: Record<string, Record<string, number>>;
}
```

```typescript
// src/api.ts
import type { Lead, Stats } from "./types";

export async function fetchLeads(params: Record<string, string> = {}): Promise<Lead[]> {
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString();
  const r = await fetch(`/api/leads${qs ? "?" + qs : ""}`);
  if (!r.ok) throw new Error(`leads ${r.status}`);
  return r.json();
}

export async function fetchStats(): Promise<Stats> {
  const r = await fetch("/api/stats");
  if (!r.ok) throw new Error(`stats ${r.status}`);
  return r.json();
}
```

- [ ] **Step 5: Install + typecheck**

Run: `cd outreach-tool/frontend && npm install && npx tsc --noEmit`
Expected: installs; tsc reports no errors (App.tsx will be added next task — if tsc fails only on missing App, proceed).

- [ ] **Step 6: Commit**

```bash
git add outreach-tool/frontend/package.json outreach-tool/frontend/vite.config.ts outreach-tool/frontend/index.html outreach-tool/frontend/src/main.tsx outreach-tool/frontend/src/types.ts outreach-tool/frontend/src/api.ts
git commit -m "chore: scaffold react+vite frontend + api client"
```

---

### Task 11: Dashboard components (StatCards, LeadsTable, App)

**Files:**
- Create: `outreach-tool/frontend/src/components/StatCards.tsx`
- Create: `outreach-tool/frontend/src/components/LeadsTable.tsx`
- Create: `outreach-tool/frontend/src/App.tsx`

- [ ] **Step 1: StatCards.tsx**

```tsx
// src/components/StatCards.tsx
import type { Stats } from "../types";

export function StatCards({ stats }: { stats: Stats }) {
  const email = stats.by_channel_status.email ?? {};
  const ig = stats.by_channel_status.instagram ?? {};
  const wa = stats.by_channel_status.whatsapp ?? {};
  const card = (label: string, value: number | string) => (
    <div style={{ background: "#1e2733", color: "#e6edf3", padding: 16, borderRadius: 8, minWidth: 140 }}>
      <div style={{ fontSize: 13, opacity: 0.7 }}>{label}</div>
      <div style={{ fontSize: 26, fontWeight: 700 }}>{value}</div>
    </div>
  );
  return (
    <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 20 }}>
      {card("客户总数", stats.total)}
      {card("Email 已发", email.messaged ?? 0)}
      {card("IG 已发", ig.messaged ?? 0)}
      {card("WhatsApp 已发", wa.messaged ?? 0)}
      {card("国家数", Object.keys(stats.by_country).length)}
    </div>
  );
}
```

- [ ] **Step 2: LeadsTable.tsx**

```tsx
// src/components/LeadsTable.tsx
import type { Lead } from "../types";

export function LeadsTable({ leads }: { leads: Lead[] }) {
  const th = { textAlign: "left" as const, padding: "8px 10px", borderBottom: "2px solid #30363d", position: "sticky" as const, top: 0, background: "#0d1117" };
  const td = { padding: "8px 10px", borderBottom: "1px solid #21262d" };
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", color: "#e6edf3", fontSize: 14 }}>
      <thead><tr>
        <th style={th}>#</th><th style={th}>公司</th><th style={th}>国家</th>
        <th style={th}>城市</th><th style={th}>Email</th><th style={th}>渠道状态</th>
      </tr></thead>
      <tbody>
        {leads.map((l) => (
          <tr key={l.no}>
            <td style={td}>{l.no}</td>
            <td style={td}>{l.website ? <a href={`https://${l.website}`} target="_blank" style={{ color: "#58a6ff" }}>{l.company_en}</a> : l.company_en}</td>
            <td style={td}>{l.country}</td>
            <td style={td}>{l.city}</td>
            <td style={td}>{l.email}</td>
            <td style={td}>{l.outreach.map((o) => `${o.channel}:${o.status}`).join(", ")}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 3: App.tsx**

```tsx
// src/App.tsx
import { useEffect, useState } from "react";
import { fetchLeads, fetchStats } from "./api";
import type { Lead, Stats } from "./types";
import { StatCards } from "./components/StatCards";
import { LeadsTable } from "./components/LeadsTable";

export function App() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [country, setCountry] = useState("");
  const [search, setSearch] = useState("");
  const [err, setErr] = useState("");

  useEffect(() => { fetchStats().then(setStats).catch((e) => setErr(String(e))); }, []);
  useEffect(() => { fetchLeads({ country, search }).then(setLeads).catch((e) => setErr(String(e))); }, [country, search]);

  const input = { background: "#0d1117", color: "#e6edf3", border: "1px solid #30363d", borderRadius: 6, padding: "6px 10px" };
  return (
    <div style={{ fontFamily: "system-ui, sans-serif", background: "#0d1117", minHeight: "100vh", padding: 24 }}>
      <h1 style={{ color: "#e6edf3" }}>客户开发看板</h1>
      {err && <div style={{ color: "#f85149" }}>加载失败：{err}</div>}
      {stats && <StatCards stats={stats} />}
      <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
        <select style={input} value={country} onChange={(e) => setCountry(e.target.value)}>
          <option value="">全部国家</option>
          {stats && Object.keys(stats.by_country).sort().map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <input style={input} placeholder="搜索公司/网站/城市" value={search} onChange={(e) => setSearch(e.target.value)} />
        <span style={{ color: "#8b949e", alignSelf: "center" }}>{leads.length} 条</span>
      </div>
      <LeadsTable leads={leads} />
    </div>
  );
}
```

- [ ] **Step 4: Typecheck + build**

Run: `cd outreach-tool/frontend && npx tsc --noEmit && npm run build`
Expected: no type errors; `dist/` produced.

- [ ] **Step 5: Commit**

```bash
git add outreach-tool/frontend/src/components/StatCards.tsx outreach-tool/frontend/src/components/LeadsTable.tsx outreach-tool/frontend/src/App.tsx
git commit -m "feat: read-only dashboard (stat cards + filterable leads table)"
```

---

### Task 12: Serve frontend from FastAPI + smoke test + README

**Files:**
- Modify: `outreach-tool/backend/app/main.py` (mount static dist)
- Create: `outreach-tool/frontend/tests/smoke.spec.ts`
- Create: `outreach-tool/frontend/playwright.config.ts`
- Create: `outreach-tool/README.md`

- [ ] **Step 1: Mount built frontend in main.py (append after routers)**

```python
# append to app/main.py
import os
from fastapi.staticfiles import StaticFiles

_DIST = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
if os.path.isdir(_DIST):
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="static")
```

- [ ] **Step 2: playwright.config.ts**

```typescript
import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  use: { baseURL: "http://127.0.0.1:8000" },
});
```

- [ ] **Step 3: smoke.spec.ts**

```typescript
import { test, expect } from "@playwright/test";

test("dashboard loads leads and stats", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("客户开发看板")).toBeVisible();
  await expect(page.getByText("客户总数")).toBeVisible();
  // table has at least one data row
  await expect(page.locator("table tbody tr").first()).toBeVisible();
});
```

- [ ] **Step 4: README.md (run instructions)**

```markdown
# 客户开发 / 触达工具 (Phase 1 MVP)

## 一次性准备
1. 后端依赖：`cd backend && python -m pip install -r requirements.txt`
2. 导入历史数据：`cd backend && python -m app.migrate`
3. 前端构建：`cd frontend && npm install && npm run build`

## 启动
`cd backend && python -m uvicorn app.main:app --port 8000`
浏览器打开 http://127.0.0.1:8000

## 开发模式（热更新）
- 后端：`cd backend && python -m uvicorn app.main:app --reload --port 8000`
- 前端：`cd frontend && npm run dev`（自动代理 /api 到 8000）
```

- [ ] **Step 5: Run smoke test end-to-end**

Run (two shells): start backend `cd outreach-tool/backend && python -m uvicorn app.main:app --port 8000`; then `cd outreach-tool/frontend && npx playwright test`
Expected: 1 passed (dashboard shows title, 客户总数 card, and ≥1 table row from migrated data).

- [ ] **Step 6: Commit**

```bash
git add outreach-tool/backend/app/main.py outreach-tool/frontend/tests/smoke.spec.ts outreach-tool/frontend/playwright.config.ts outreach-tool/README.md
git commit -m "feat: serve dashboard from fastapi + playwright smoke test + readme"
```

---

## Self-Review

**Spec coverage (S1 + S2):**
- S1 Lead Store (SQLite + dedup) → Tasks 2, 5 (`find_duplicate`), migration Task 7/8. ✓
- S1 migration of 79 files + pipelines → Task 7 (`load_leads` chain loader, `load_pipeline_rows`), Task 8 (real run). ✓
- S2 read API (leads list/filter/search, stats) → Tasks 9. ✓
- S2 dashboard (stat cards, filterable table) → Tasks 10–11. ✓
- Single-command run (FastAPI serves frontend) → Task 12. ✓
- Chinese UI (spec §9 decision 4) → App/StatCards/LeadsTable use 中文 labels. ✓

**Deferred to later plans (correctly out of scope here):** Outreach Engine + EmailAdapter (S3), Discovery/Enrichment (S4), CDP channel adapters (S5). Dedup-on-add UI belongs to S4; `find_duplicate` is built now so S4 can use it.

**Placeholder scan:** No TBD/TODO; every code step has complete code. ✓

**Type consistency:** `Lead`/`OutreachStatus`/`Stats` fields match across `models.py`, `repository.py`, `api/*`, and frontend `types.ts`. `get_conn` lives in `main_deps.py` (imported by main + routers + tests) — no circular import. `list_leads` signature identical in repository, API, and tests. ✓

**Note for implementer:** Windows uses `cd x && cmd` in Git Bash; the backend default `OUTREACH_DB=outreach.db` is relative to the backend dir, so run uvicorn from `outreach-tool/backend`.
