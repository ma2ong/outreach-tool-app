# Discovery Panel Implementation Plan — S4

> **For agentic workers:** Use superpowers:executing-plans. Steps use `- [ ]`.

**Goal:** Let the user type a keyword in the dashboard, search + scrape candidate companies (email extracted), see which are already in the DB, and import selected ones as leads — all from the browser (spec sub-project S4).

**Architecture:** Search runs by reading a DuckDuckGo HTML results page **through** `r.jina.ai` (no API key), extracting result domains from `uddg=` redirect params. Each domain is enriched by fetching its contact/home page through `r.jina.ai` and regex-extracting emails. Duplicates are flagged via the existing `repository.find_duplicate`. Discovery runs as a background job (reusing the jobs registry) because each fetch is slow; the UI polls. Selected candidates are imported via a bulk insert that assigns the next `no`.

**Tech Stack:** httpx (server-side fetch of r.jina.ai), FastAPI BackgroundTasks + jobs registry, pytest with injected fetch (no network in tests); React panel.

**Key constraint discovered:** `s.jina.ai` (Jina search) now requires an API key (401). `r.jina.ai` (read) works without a key. So search is done by reading DDG HTML via `r.jina.ai`. The fetch function is injectable/pluggable so a keyed search API can replace it later.

**Spec:** `docs/superpowers/specs/2026-07-02-outreach-tool-design.md` §4 (Discovery + Enrichment), §7 (S4).

---

## File Structure

```
backend/app/
  jina.py            # fetch(url) -> str via r.jina.ai (httpx)
  search.py          # search_domains(query, limit, fetch) -> list[dict{domain,title}]
  enrich.py          # extract_emails(text); enrich_domain(domain, fetch) -> dict
  discovery.py       # run_discovery(conn, query, limit, search_fn, enrich_fn, on_progress) -> candidates
  repository.py      # + next_no(), insert_lead()
  api/discover.py    # POST /api/discover (bg job), GET /api/discover/jobs/{id}, POST /api/leads/import
backend/tests/
  test_search.py test_enrich.py test_discovery.py test_repository_insert.py test_discover_api.py
frontend/src/
  types.ts           # + Candidate, DiscoverJob
  api.ts             # + startDiscover, fetchDiscoverJob, importLeads
  components/DiscoveryPanel.tsx
  App.tsx            # + panel
```

---

### Task 1: Jina fetch + domain search

**Files:** Create `backend/app/jina.py`, `backend/app/search.py`; Test `backend/tests/test_search.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_search.py
from app import search

FAKE_DDG = """Markdown Content:
## [AV One | LED Video Walls](https://duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.avone.com%2F&rut=x)
## [Bright Screens](https://duckduckgo.com/l/?uddg=https%3A%2F%2Fbrightscreens.com%2Fcontact&rut=y)
## [AV One again](https://duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.avone.com%2Fabout&rut=z)
"""


def test_search_domains_extracts_unique_domains():
    out = search.search_domains("led wall", limit=10, fetch=lambda url: FAKE_DDG)
    domains = [c["domain"] for c in out]
    assert domains == ["avone.com", "brightscreens.com"]  # deduped, www stripped, order preserved


def test_search_domains_respects_limit():
    out = search.search_domains("led wall", limit=1, fetch=lambda url: FAKE_DDG)
    assert len(out) == 1
```

- [ ] **Step 2: Run → FAIL** `cd backend && python -m pytest tests/test_search.py -v`

- [ ] **Step 3: Implement**

```python
# app/jina.py
import httpx

BASE = "https://r.jina.ai/"


def fetch(url: str, timeout: int = 45) -> str:
    r = httpx.get(BASE + url, timeout=timeout, follow_redirects=True)
    r.raise_for_status()
    return r.text
```

```python
# app/search.py
import re
import urllib.parse
from typing import Callable

from app.jina import fetch as jina_fetch

_SKIP = ("duckduckgo.com", "jina.ai", "wikipedia.org", "w3.org", "schema.org", "google.com", "bing.com")


def search_domains(query: str, limit: int = 10,
                   fetch: Callable[[str], str] = jina_fetch) -> list[dict]:
    enc = urllib.parse.quote(query)
    text = fetch(f"https://html.duckduckgo.com/html/?q={enc}")
    seen: dict[str, dict] = {}
    for m in re.finditer(r'uddg=([^&"\)\s]+)', text):
        target = urllib.parse.unquote(m.group(1))
        host = urllib.parse.urlparse(target).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        if not host or any(s in host for s in _SKIP):
            continue
        if host not in seen:
            seen[host] = {"domain": host, "title": ""}
        if len(seen) >= limit:
            break
    return list(seen.values())
```

- [ ] **Step 4: Run → PASS** (2 passed).
- [ ] **Step 5: Commit** `git add backend/app/jina.py backend/app/search.py backend/tests/test_search.py && git commit -m "feat: domain search via DuckDuckGo-through-Jina"`

---

### Task 2: Enrichment (email extraction)

**Files:** Create `backend/app/enrich.py`; Test `backend/tests/test_enrich.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_enrich.py
from app import enrich


def test_extract_emails_filters_junk():
    text = "Contact info@acme.com or sales@acme.com. img@2x.png sentry@abc.io a@b.jpg"
    got = enrich.extract_emails(text)
    assert got == ["info@acme.com", "sales@acme.com"]


def test_enrich_domain_picks_best_email():
    pages = {
        "https://acme.com/contact": "reach info@acme.com",
        "https://acme.com": "home",
    }
    out = enrich.enrich_domain("acme.com", fetch=lambda url: pages.get(url, ""))
    assert out["domain"] == "acme.com"
    assert out["email"] == "info@acme.com"
    assert "info@acme.com" in out["emails"]


def test_enrich_domain_no_email():
    out = enrich.enrich_domain("none.com", fetch=lambda url: "no address here")
    assert out["email"] is None
    assert out["emails"] == []
```

- [ ] **Step 2: Run → FAIL**

- [ ] **Step 3: Implement**

```python
# app/enrich.py
import re
from typing import Callable

from app.jina import fetch as jina_fetch

_EMAIL = re.compile(r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}', re.I)
_JUNK = ("sentry", "wixpress", "example.", "@2x", "@3x", ".png", ".jpg", ".jpeg", ".gif", ".webp")
_PREFER = ("info@", "sales@", "contact@", "hello@", "enquiries@", "office@")


def extract_emails(text: str) -> list[str]:
    out, seen = [], set()
    for m in _EMAIL.finditer(text):
        e = m.group(0)
        low = e.lower()
        if any(j in low for j in _JUNK):
            continue
        if low not in seen:
            seen.add(low)
            out.append(e)
    return out


def enrich_domain(domain: str, fetch: Callable[[str], str] = jina_fetch) -> dict:
    emails: list[str] = []
    for path in ("/contact", "/contact-us", ""):
        try:
            text = fetch(f"https://{domain}{path}")
        except Exception:  # noqa: BLE001
            continue
        for e in extract_emails(text):
            if e not in emails:
                emails.append(e)
        if emails:
            break
    best = None
    for e in emails:
        if any(e.lower().startswith(p) for p in _PREFER):
            best = e
            break
    if best is None and emails:
        best = emails[0]
    return {"domain": domain, "emails": emails, "email": best}
```

- [ ] **Step 4: Run → PASS** (3 passed).
- [ ] **Step 5: Commit** `git add backend/app/enrich.py backend/tests/test_enrich.py && git commit -m "feat: domain enrichment (email extraction)"`

---

### Task 3: Repository insert + next_no

**Files:** Modify `backend/app/repository.py`; Test `backend/tests/test_repository_insert.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_repository_insert.py
from app import repository as repo


def test_next_no_empty(tmp_path):
    from app.db import connect, init_schema
    c = connect(str(tmp_path / "t.db")); init_schema(c)
    assert repo.next_no(c) == 1


def test_insert_and_next_no(conn):
    n = repo.next_no(conn)  # conn fixture has leads 1..3
    assert n == 4
    repo.insert_lead(conn, {"company_en": "New Co", "country": "USA",
                            "website": "new.com", "email": "info@new.com"})
    lead = repo.get_lead(conn, 4)
    assert lead.company_en == "New Co"
    assert lead.email == "info@new.com"
    assert repo.next_no(conn) == 5
```

- [ ] **Step 2: Run → FAIL**

- [ ] **Step 3: Implement (append to repository.py)**

```python
# append to app/repository.py
import datetime as _dt

_INSERT_COLS = ["company_en", "company_local", "country", "region", "city",
                "email", "phone", "website", "instagram", "facebook", "linkedin",
                "business", "target_fit"]


def next_no(conn) -> int:
    row = conn.execute("SELECT MAX(no) m FROM leads").fetchone()
    return (row["m"] or 0) + 1


def insert_lead(conn, data: dict) -> int:
    no = next_no(conn)
    cols = ["no"] + _INSERT_COLS + ["created_at", "updated_at"]
    now = _dt.datetime.utcnow().isoformat()
    vals = [no] + [data.get(c) for c in _INSERT_COLS] + [now, now]
    placeholders = ",".join("?" * len(cols))
    conn.execute(f"INSERT INTO leads({','.join(cols)}) VALUES ({placeholders})", vals)
    conn.commit()
    return no
```

- [ ] **Step 4: Run → PASS** (2 passed). Full suite still green.
- [ ] **Step 5: Commit** `git add backend/app/repository.py backend/tests/test_repository_insert.py && git commit -m "feat: repository insert_lead + next_no"`

---

### Task 4: Discovery orchestration

**Files:** Create `backend/app/discovery.py`; Test `backend/tests/test_discovery.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_discovery.py
from app import discovery


def test_run_discovery_flags_duplicates_and_progress(conn):
    # conn fixture: lead 1 has website 'alpha.com'
    search_fn = lambda q, limit: [{"domain": "alpha.com", "title": ""},
                                   {"domain": "newco.com", "title": ""}]
    enrich_fn = lambda d: {"domain": d, "emails": [f"info@{d}"], "email": f"info@{d}"}
    seen = []
    cands = discovery.run_discovery(conn, "led", 10, search_fn=search_fn, enrich_fn=enrich_fn,
                                    on_progress=lambda done, total: seen.append((done, total)))
    by = {c["domain"]: c for c in cands}
    assert by["alpha.com"]["duplicate_of"] == 1
    assert by["newco.com"]["duplicate_of"] is None
    assert by["newco.com"]["email"] == "info@newco.com"
    assert seen[-1] == (2, 2)
```

- [ ] **Step 2: Run → FAIL**

- [ ] **Step 3: Implement**

```python
# app/discovery.py
from typing import Callable

from app import repository as repo
from app.search import search_domains
from app.enrich import enrich_domain


def run_discovery(conn, query: str, limit: int = 10,
                  search_fn: Callable = None, enrich_fn: Callable = None,
                  on_progress: Callable[[int, int], None] | None = None) -> list[dict]:
    search_fn = search_fn or (lambda q, lim: search_domains(q, lim))
    enrich_fn = enrich_fn or (lambda d: enrich_domain(d))
    domains = search_fn(query, limit)
    out = []
    total = len(domains)
    for i, d in enumerate(domains, 1):
        info = enrich_fn(d["domain"])
        dup = repo.find_duplicate(conn, website=d["domain"], instagram=None,
                                  company_en=d.get("title") or None)
        out.append({
            "domain": d["domain"],
            "title": d.get("title") or d["domain"],
            "email": info.get("email"),
            "emails": info.get("emails", []),
            "duplicate_of": dup,
        })
        if on_progress:
            on_progress(i, total)
    return out
```

- [ ] **Step 4: Run → PASS** (1 passed).
- [ ] **Step 5: Commit** `git add backend/app/discovery.py backend/tests/test_discovery.py && git commit -m "feat: discovery orchestration (search+enrich+dedup)"`

---

### Task 5: Discover + import API

**Files:** Create `backend/app/api/discover.py`; Modify `backend/app/main.py`; Test `backend/tests/test_discover_api.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_discover_api.py
import app.main as main
from app import jobs
from app.db import connect, init_schema
from fastapi.testclient import TestClient


def _client(tmp_path):
    import app.api.discover as disc
    db = str(tmp_path / "t.db")
    c = connect(db); init_schema(c)
    c.execute("INSERT INTO leads(no, company_en, website) VALUES (1,'Alpha','alpha.com')")
    c.commit(); c.close()
    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    disc.DB_PATH = db
    disc.SEARCH_FN = lambda q, limit: [{"domain": "alpha.com", "title": "Alpha"},
                                       {"domain": "newco.com", "title": "New Co"}]
    disc.ENRICH_FN = lambda d: {"domain": d, "emails": [f"info@{d}"], "email": f"info@{d}"}
    return TestClient(main.app), db


def test_discover_job_and_import(tmp_path):
    jobs.clear()
    client, db = _client(tmp_path)
    r = client.post("/api/discover", json={"query": "led wall", "limit": 10})
    jid = r.json()["job_id"]
    job = client.get(f"/api/discover/jobs/{jid}").json()
    assert job["status"] == "done"
    cands = job["result"]["candidates"]
    assert {c["domain"] for c in cands} == {"alpha.com", "newco.com"}
    # import the new one
    r2 = client.post("/api/leads/import", json={"country": "USA", "candidates": [
        {"company_en": "New Co", "website": "newco.com", "email": "info@newco.com"}]})
    assert r2.json()["imported"] == 1
    conn = connect(db)
    assert conn.execute("SELECT COUNT(*) c FROM leads WHERE website='newco.com'").fetchone()["c"] == 1


def test_discover_jobs_404(tmp_path):
    client, _ = _client(tmp_path)
    assert client.get("/api/discover/jobs/nope").status_code == 404
```

- [ ] **Step 2: Run → FAIL**

- [ ] **Step 3: Implement**

```python
# app/api/discover.py
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from app import discovery, jobs, repository
from app.db import connect
from app.main_deps import DB_PATH as _DB_PATH, get_conn

router = APIRouter(prefix="/api")

DB_PATH = _DB_PATH
SEARCH_FN = None   # injectable in tests; None -> real search
ENRICH_FN = None   # injectable in tests; None -> real enrich


class DiscoverRequest(BaseModel):
    query: str
    limit: int = 10


class Candidate(BaseModel):
    company_en: str
    website: str | None = None
    email: str | None = None
    city: str | None = None
    instagram: str | None = None


class ImportRequest(BaseModel):
    country: str | None = None
    candidates: list[Candidate]


def _run(job_id: str, query: str, limit: int):
    conn = connect(DB_PATH)
    try:
        cands = discovery.run_discovery(
            conn, query, limit, search_fn=SEARCH_FN, enrich_fn=ENRICH_FN,
            on_progress=lambda done, total: jobs.update(job_id, done))
        jobs.finish(job_id, {"candidates": cands})
    except Exception as exc:  # noqa: BLE001
        jobs.fail(job_id, str(exc))
    finally:
        conn.close()


@router.post("/discover")
def discover(req: DiscoverRequest, background: BackgroundTasks):
    job_id = jobs.create(total=req.limit)
    background.add_task(_run, job_id, req.query, req.limit)
    return {"job_id": job_id}


@router.get("/discover/jobs/{job_id}")
def discover_job(job_id: str):
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.post("/leads/import")
def import_leads(req: ImportRequest, conn=Depends(get_conn)):
    imported = 0
    for c in req.candidates:
        if c.website and repository.find_duplicate(conn, website=c.website, instagram=c.instagram, company_en=c.company_en):
            continue
        repository.insert_lead(conn, {
            "company_en": c.company_en, "country": req.country, "city": c.city,
            "website": c.website, "email": c.email, "instagram": c.instagram,
            "target_fit": "discovered"})
        imported += 1
    return {"imported": imported}
```

Modify `app/main.py` — add import + include router (before static mount):

```python
from app.api import discover as discover_api
# ...
app.include_router(discover_api.router)
```

- [ ] **Step 4: Run → PASS** (2 passed). Full suite green.
- [ ] **Step 5: Commit** `git add backend/app/api/discover.py backend/app/main.py backend/tests/test_discover_api.py && git commit -m "feat: discover (bg job) + import API"`

---

### Task 6: DiscoveryPanel + wire into App

**Files:** Modify `frontend/src/types.ts`, `frontend/src/api.ts`; Create `frontend/src/components/DiscoveryPanel.tsx`; Modify `frontend/src/App.tsx`

- [ ] **Step 1: types.ts (append)**

```typescript
export interface Candidate {
  domain: string; title: string; email: string | null; emails: string[]; duplicate_of: number | null;
}
export interface DiscoverJob {
  id: string; status: string; done: number; total: number;
  result: { candidates: Candidate[] } | { error: string } | null;
}
```

- [ ] **Step 2: api.ts (append)**

```typescript
import type { DiscoverJob } from "./types";

export async function startDiscover(query: string, limit = 10): Promise<{ job_id: string }> {
  const r = await fetch("/api/discover", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, limit }),
  });
  if (!r.ok) throw new Error(`discover ${r.status}`);
  return r.json();
}

export async function fetchDiscoverJob(id: string): Promise<DiscoverJob> {
  const r = await fetch(`/api/discover/jobs/${id}`);
  if (!r.ok) throw new Error(`discover job ${r.status}`);
  return r.json();
}

export async function importLeads(country: string, candidates: { company_en: string; website: string; email: string | null }[]): Promise<{ imported: number }> {
  const r = await fetch("/api/leads/import", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ country, candidates }),
  });
  if (!r.ok) throw new Error(`import ${r.status}`);
  return r.json();
}
```

- [ ] **Step 3: Create DiscoveryPanel.tsx**

```tsx
import { useState } from "react";
import { startDiscover, fetchDiscoverJob, importLeads } from "../api";
import type { Candidate } from "../types";

export function DiscoveryPanel({ onImported }: { onImported: () => void }) {
  const [query, setQuery] = useState("LED video wall installer AV integrator USA contact");
  const [country, setCountry] = useState("USA");
  const [cands, setCands] = useState<Candidate[]>([]);
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  async function run() {
    setBusy(true); setMsg("搜索深挖中…"); setCands([]); setPicked(new Set());
    try {
      const { job_id } = await startDiscover(query, 10);
      const poll = setInterval(async () => {
        const j = await fetchDiscoverJob(job_id);
        setMsg(`进度 ${j.done}/${j.total}`);
        if (j.status !== "running") {
          clearInterval(poll); setBusy(false);
          if (j.result && "candidates" in j.result) {
            setCands(j.result.candidates);
            setPicked(new Set(j.result.candidates.filter((c) => !c.duplicate_of && c.email).map((c) => c.domain)));
            setMsg(`找到 ${j.result.candidates.length} 个候选`);
          } else if (j.result && "error" in j.result) setMsg("失败：" + j.result.error);
        }
      }, 2000);
    } catch (e) { setBusy(false); setMsg("失败：" + String(e)); }
  }

  async function doImport() {
    const chosen = cands.filter((c) => picked.has(c.domain));
    const res = await importLeads(country, chosen.map((c) => ({ company_en: c.title, website: c.domain, email: c.email })));
    setMsg(`已导入 ${res.imported} 家`); onImported();
  }

  const box = { background: "#0d1117", color: "#e6edf3", border: "1px solid #30363d", borderRadius: 6, padding: "6px 10px" };
  const toggle = (d: string) => setPicked((s) => { const n = new Set(s); if (n.has(d)) { n.delete(d); } else { n.add(d); } return n; });
  return (
    <div style={{ background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 16, marginBottom: 20 }}>
      <h3 style={{ color: "#e6edf3", marginTop: 0 }}>客户开发（搜索 + 深挖 + 入库）</h3>
      <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
        <input style={{ ...box, flex: 1 }} value={query} onChange={(e) => setQuery(e.target.value)} placeholder="关键词，如 LED video wall installer Texas" />
        <input style={{ ...box, width: 90 }} value={country} onChange={(e) => setCountry(e.target.value)} placeholder="国家" />
        <button onClick={run} disabled={busy} style={{ background: busy ? "#30363d" : "#1f6feb", color: "#fff", border: "none", borderRadius: 6, padding: "6px 16px" }}>
          {busy ? "搜索中…" : "搜索深挖"}
        </button>
      </div>
      {msg && <div style={{ color: "#8b949e", marginBottom: 8 }}>{msg}</div>}
      {cands.length > 0 && (
        <>
          <table style={{ width: "100%", borderCollapse: "collapse", color: "#e6edf3", fontSize: 13 }}>
            <thead><tr>
              <th></th><th style={{ textAlign: "left", padding: 6 }}>网站</th>
              <th style={{ textAlign: "left", padding: 6 }}>邮箱</th><th style={{ textAlign: "left", padding: 6 }}>状态</th>
            </tr></thead>
            <tbody>
              {cands.map((c) => (
                <tr key={c.domain}>
                  <td style={{ padding: 6 }}><input type="checkbox" disabled={!!c.duplicate_of} checked={picked.has(c.domain)} onChange={() => toggle(c.domain)} /></td>
                  <td style={{ padding: 6 }}><a href={`https://${c.domain}`} target="_blank" rel="noreferrer" style={{ color: "#58a6ff" }}>{c.domain}</a></td>
                  <td style={{ padding: 6 }}>{c.email || <span style={{ color: "#8b949e" }}>—</span>}</td>
                  <td style={{ padding: 6 }}>{c.duplicate_of ? <span style={{ color: "#d29922" }}>已在库 #{c.duplicate_of}</span> : <span style={{ color: "#3fb950" }}>新</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <button onClick={doImport} style={{ marginTop: 10, background: "#238636", color: "#fff", border: "none", borderRadius: 6, padding: "8px 18px" }}>
            导入选中（{picked.size}）
          </button>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Wire into App.tsx** — add import and render `<DiscoveryPanel onImported={reload} />` right after `<OutreachPanel .../>`:

```tsx
import { DiscoveryPanel } from "./components/DiscoveryPanel";
// ... inside return, after <OutreachPanel .../>:
      <DiscoveryPanel onImported={reload} />
```

- [ ] **Step 5: Typecheck + build** `cd frontend && npx tsc --noEmit && npm run build` — no errors.
- [ ] **Step 6: Commit** `git add frontend/src/types.ts frontend/src/api.ts frontend/src/components/DiscoveryPanel.tsx frontend/src/App.tsx && git commit -m "feat: discovery panel — search, enrich, import from UI"`

---

### Task 7: Smoke + finish

**Files:** Modify `frontend/tests/smoke.spec.ts` (append)

- [ ] **Step 1: Append smoke assertion**

```typescript
test("discovery panel is present", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "搜索深挖" })).toBeVisible();
  await expect(page.getByText(/客户开发（搜索/)).toBeVisible();
});
```

- [ ] **Step 2: Full backend suite** `cd backend && python -m pytest -q` → all green.
- [ ] **Step 3: Rebuild + smoke** — start one uvicorn on 8000 (kill any existing first), `cd frontend && npm run build && npx playwright test`. Expected: 3 passed.

  > SAFETY: smoke never clicks 搜索深挖 or 导入 (would hit network / write DB).

- [ ] **Step 4: Commit** `git add frontend/tests/smoke.spec.ts && git commit -m "test: smoke assertion for discovery panel"`

---

## Self-Review

**Spec coverage (S4):** search → Task 1; enrich → Task 2; dedup+insert → Tasks 3–4; API bg job + import → Task 5; UI search/enrich/import → Task 6. ✓
**Constraint handled:** s.jina.ai needs key → search via DDG-through-r.jina.ai; fetch injectable so a keyed provider can replace it. ✓
**Safety:** import re-checks find_duplicate server-side (double-guard); duplicate candidates' checkboxes disabled in UI; smoke never triggers network/writes. ✓
**Placeholder scan:** none. **Type consistency:** `run_discovery(conn, query, limit, search_fn, enrich_fn, on_progress)` and API `SEARCH_FN/ENRICH_FN/DB_PATH` module seams mirror the S3 send pattern; `Candidate`/`DiscoverJob` TS mirror backend. ✓
**Note:** discovery `_run` uses module-global `DB_PATH` (same seam as send) — tests set `disc.DB_PATH`.
