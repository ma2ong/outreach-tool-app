# Outreach Panel (Email) Implementation Plan — S3

> **For agentic workers:** Use superpowers:executing-plans to implement task-by-task. Steps use `- [ ]` checkboxes.

**Goal:** Let the user select leads in the dashboard, edit an email template, and send a rate-limited email campaign — all from the browser — with progress tracking and automatic status write-back (spec sub-project S3).

**Architecture:** A pure `EmailAdapter.send()` wraps SMTP (reusing the existing Gmail flow). `outreach.send_campaign()` iterates eligible leads (has email, not already emailed), calls an injectable sender, marks each `messaged`, and reports progress via a callback. The API starts the campaign as a FastAPI BackgroundTask, tracking live progress in an in-memory job registry the frontend polls. The dashboard gains row checkboxes + an OutreachPanel (template editor + send + progress bar).

**Tech Stack:** FastAPI BackgroundTasks, stdlib smtplib/email, pytest (inject fake sender); React state for selection + polling.

**Spec:** `docs/superpowers/specs/2026-07-02-outreach-tool-design.md` §4 (Outreach Engine + Channel Adapters), §7 (S3).

---

## File Structure

```
backend/app/
  channels/__init__.py
  channels/email_adapter.py   # send_email(to,subject,body,attachment) via SMTP_SSL
  outreach.py                 # eligible_leads(), send_campaign(sender, on_progress)
  jobs.py                     # in-memory job registry (progress state)
  api/send.py                 # POST /api/send/email, GET /api/send/jobs/{id}
backend/tests/
  test_email_adapter.py
  test_outreach.py
  test_send_api.py
frontend/src/
  types.ts                    # + SendJob, extend
  api.ts                      # + startEmailSend, fetchJob
  components/OutreachPanel.tsx
  components/LeadsTable.tsx    # + selection checkboxes
  App.tsx                     # + selection state + panel
```

Boundaries: `email_adapter.py` only knows SMTP. `outreach.py` only knows eligibility + orchestration (sender injected — no SMTP import). `jobs.py` only tracks state. `api/send.py` wires them to HTTP + BackgroundTasks.

---

### Task 1: EmailAdapter

**Files:** Create `backend/app/channels/__init__.py` (empty), `backend/app/channels/email_adapter.py`; Test `backend/tests/test_email_adapter.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_email_adapter.py
from app.channels import email_adapter


def test_build_message_has_subject_body_attachment(tmp_path):
    att = tmp_path / "poster.jpg"
    att.write_bytes(b"\xff\xd8\xff\xe0fake")
    msg = email_adapter.build_message(
        sender="me@gmail.com", to="x@y.com", subject="Hi Bob",
        body="Hello Bob", attachment=str(att))
    assert msg["To"] == "x@y.com"
    assert msg["Subject"] == "Hi Bob"
    payloads = msg.get_payload()
    assert any(p.get_filename() == "poster.jpg" for p in payloads)
    assert any("Hello Bob" in str(p.get_payload()) for p in payloads)


def test_build_message_no_attachment():
    msg = email_adapter.build_message(
        sender="me@gmail.com", to="x@y.com", subject="S", body="B", attachment=None)
    assert msg["Subject"] == "S"
```

- [ ] **Step 2: Run → FAIL** `cd backend && python -m pytest tests/test_email_adapter.py -v` (ModuleNotFoundError).

- [ ] **Step 3: Implement**

```python
# app/channels/email_adapter.py
import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

GMAIL_USER = "allenma2ong@gmail.com"
PW_FILE = Path.home() / ".gmail_app_password"


def get_password() -> str:
    return os.environ.get("GMAIL_APP_PASSWORD") or (
        PW_FILE.read_text(encoding="utf-8").strip() if PW_FILE.exists() else "")


def build_message(sender: str, to: str, subject: str, body: str, attachment: str | None) -> MIMEMultipart:
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to
    msg.attach(MIMEText(body, "plain", "utf-8"))
    if attachment and os.path.exists(attachment):
        with open(attachment, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(attachment)}"')
        msg.attach(part)
    return msg


def send_email(to: str, subject: str, body: str, attachment: str | None = None) -> None:
    pw = get_password()
    if not pw:
        raise RuntimeError("Gmail app password missing (~/.gmail_app_password or GMAIL_APP_PASSWORD)")
    msg = build_message(GMAIL_USER, to, subject, body, attachment)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, pw)
        server.sendmail(GMAIL_USER, to, msg.as_bytes())
```

- [ ] **Step 4: Run → PASS** (2 passed).
- [ ] **Step 5: Commit** `git add backend/app/channels backend/tests/test_email_adapter.py && git commit -m "feat: email adapter (build_message + SMTP send)"`

---

### Task 2: Outreach campaign orchestration

**Files:** Create `backend/app/outreach.py`; Test `backend/tests/test_outreach.py`

Eligibility: lead has non-empty `email` AND has no `outreach` row with `channel='email' AND status='messaged'`.

- [ ] **Step 1: Failing test**

```python
# tests/test_outreach.py
from app import outreach


def _seed(conn):
    conn.executescript("""
        INSERT INTO leads(no, company_en, email) VALUES
            (1,'Alpha','a@a.com'),(2,'Beta','b@b.com'),(3,'Gamma',NULL),(4,'Delta','d@d.com');
        INSERT INTO outreach(lead_no, channel, status) VALUES (4,'email','messaged');
    """)
    conn.commit()


def test_eligible_leads_skips_no_email_and_already_sent(conn):
    _seed(conn)
    elig = outreach.eligible_leads(conn, [1, 2, 3, 4], "email")
    assert [l["no"] for l in elig] == [1, 2]  # 3 no email, 4 already messaged


def test_send_campaign_sends_and_marks(conn):
    _seed(conn)
    calls = []
    result = outreach.send_campaign(
        conn, [1, 2, 3, 4], subject="Hi {name}", body="Hello {name}",
        attachment=None, sender=lambda to, s, b, a: calls.append((to, s, b)),
        delay_range=(0, 0))
    assert result["sent"] == 2
    assert result["skipped"] == 2
    assert {c[0] for c in calls} == {"a@a.com", "b@b.com"}
    assert ("a@a.com", "Hi Alpha", "Hello Alpha") in calls
    rows = conn.execute("SELECT lead_no FROM outreach WHERE channel='email' AND status='messaged' ORDER BY lead_no").fetchall()
    assert [r["lead_no"] for r in rows] == [1, 2, 4]


def test_send_campaign_records_failure(conn):
    _seed(conn)
    def boom(to, s, b, a):
        raise RuntimeError("smtp down")
    result = outreach.send_campaign(conn, [1], subject="S", body="B", attachment=None,
                                    sender=boom, delay_range=(0, 0))
    assert result["sent"] == 0
    assert result["failed"] == 1


def test_send_campaign_progress_callback(conn):
    _seed(conn)
    seen = []
    outreach.send_campaign(conn, [1, 2], subject="S", body="B", attachment=None,
                           sender=lambda *a: None, delay_range=(0, 0),
                           on_progress=lambda done, total: seen.append((done, total)))
    assert seen[-1] == (2, 2)
```

- [ ] **Step 2: Run → FAIL** (ModuleNotFoundError).

- [ ] **Step 3: Implement**

```python
# app/outreach.py
import random
import time
from typing import Callable


def eligible_leads(conn, lead_nos: list[int], channel: str) -> list[dict]:
    if not lead_nos:
        return []
    placeholders = ",".join("?" * len(lead_nos))
    rows = conn.execute(
        f"""SELECT l.no, l.company_en, l.email FROM leads l
            WHERE l.no IN ({placeholders})
              AND l.email IS NOT NULL AND l.email != ''
              AND l.no NOT IN (
                  SELECT lead_no FROM outreach WHERE channel=? AND status='messaged')
            ORDER BY l.no""",
        [*lead_nos, channel],
    ).fetchall()
    return [dict(r) for r in rows]


def _mark_messaged(conn, lead_no: int, date: str) -> None:
    conn.execute(
        "INSERT INTO outreach(lead_no, channel, status, touch_count, message_sent_date)"
        " VALUES (?, 'email', 'messaged', 1, ?)"
        " ON CONFLICT(lead_no, channel) DO UPDATE SET"
        " status='messaged', touch_count=touch_count+1, message_sent_date=excluded.message_sent_date",
        (lead_no, date),
    )
    conn.commit()


def send_campaign(conn, lead_nos: list[int], subject: str, body: str,
                  attachment: str | None, sender: Callable[[str, str, str, str | None], None],
                  delay_range: tuple[int, int] = (16, 28),
                  on_progress: Callable[[int, int], None] | None = None) -> dict:
    import datetime
    today = datetime.date.today().isoformat()
    targets = eligible_leads(conn, lead_nos, "email")
    total_selected = len(lead_nos)
    sent = failed = 0
    errors: list[dict] = []
    for i, lead in enumerate(targets, 1):
        name = lead["company_en"]
        try:
            sender(lead["email"], subject.format(name=name), body.format(name=name), attachment)
            _mark_messaged(conn, lead["no"], today)
            sent += 1
        except Exception as exc:  # noqa: BLE001
            failed += 1
            errors.append({"no": lead["no"], "error": str(exc)})
        if on_progress:
            on_progress(i, len(targets))
        if i < len(targets):
            lo, hi = delay_range
            if hi > 0:
                time.sleep(random.randint(lo, hi))
    return {"sent": sent, "failed": failed,
            "skipped": total_selected - len(targets), "errors": errors}
```

- [ ] **Step 4: Run → PASS** (4 passed).
- [ ] **Step 5: Commit** `git add backend/app/outreach.py backend/tests/test_outreach.py && git commit -m "feat: email campaign orchestration (eligibility + send + mark + progress)"`

---

### Task 3: In-memory job registry

**Files:** Create `backend/app/jobs.py`; Test `backend/tests/test_jobs.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_jobs.py
from app import jobs


def test_job_lifecycle():
    jobs.clear()
    jid = jobs.create(total=3)
    assert jobs.get(jid)["status"] == "running"
    assert jobs.get(jid)["total"] == 3
    jobs.update(jid, done=2)
    assert jobs.get(jid)["done"] == 2
    jobs.finish(jid, {"sent": 3, "failed": 0, "skipped": 0, "errors": []})
    j = jobs.get(jid)
    assert j["status"] == "done"
    assert j["result"]["sent"] == 3


def test_get_unknown_returns_none():
    jobs.clear()
    assert jobs.get("nope") is None
```

- [ ] **Step 2: Run → FAIL** (ModuleNotFoundError).

- [ ] **Step 3: Implement**

```python
# app/jobs.py
import uuid

_JOBS: dict[str, dict] = {}


def clear() -> None:
    _JOBS.clear()


def create(total: int) -> str:
    jid = uuid.uuid4().hex[:12]
    _JOBS[jid] = {"id": jid, "status": "running", "done": 0, "total": total, "result": None}
    return jid


def update(jid: str, done: int) -> None:
    if jid in _JOBS:
        _JOBS[jid]["done"] = done


def finish(jid: str, result: dict) -> None:
    if jid in _JOBS:
        _JOBS[jid].update(status="done", result=result)


def fail(jid: str, error: str) -> None:
    if jid in _JOBS:
        _JOBS[jid].update(status="error", result={"error": error})


def get(jid: str) -> dict | None:
    return _JOBS.get(jid)
```

- [ ] **Step 4: Run → PASS** (2 passed).
- [ ] **Step 5: Commit** `git add backend/app/jobs.py backend/tests/test_jobs.py && git commit -m "feat: in-memory send-job registry"`

---

### Task 4: Send API

**Files:** Create `backend/app/api/send.py`; Modify `backend/app/main.py` (include router); Test `backend/tests/test_send_api.py`

Default template + attachment live here as constants (from the existing email_sender). Sender is injectable via `send.SENDER` so tests don't hit SMTP.

- [ ] **Step 1: Failing test**

```python
# tests/test_send_api.py
import app.main as main
from app import jobs
from app.db import connect, init_schema
from fastapi.testclient import TestClient


def _client(tmp_path):
    db = str(tmp_path / "t.db")
    c = connect(db); init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, email) VALUES (1,'Alpha','a@a.com'),(2,'Beta','b@b.com');
    """)
    c.commit(); c.close()
    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    return TestClient(main.app)


def test_send_email_runs_job(tmp_path):
    import app.api.send as send_api
    jobs.clear()
    sent = []
    send_api.SENDER = lambda to, s, b, a: sent.append(to)
    send_api.DELAY_RANGE = (0, 0)
    client = _client(tmp_path)
    r = client.post("/api/send/email", json={"lead_nos": [1, 2], "subject": "Hi {name}", "body": "Hello {name}"})
    assert r.status_code == 200
    jid = r.json()["job_id"]
    job = client.get(f"/api/send/jobs/{jid}").json()
    assert job["status"] == "done"
    assert job["result"]["sent"] == 2
    assert set(sent) == {"a@a.com", "b@b.com"}


def test_send_jobs_404(tmp_path):
    assert _client(tmp_path).get("/api/send/jobs/nope").status_code == 404
```

> Note: FastAPI `BackgroundTasks` run synchronously *after* the response within `TestClient`, so by the time `.get(/jobs/{id})` is called the job has completed — the assertion on `status == "done"` holds in tests.

- [ ] **Step 2: Run → FAIL** (ModuleNotFoundError app.api.send).

- [ ] **Step 3: Implement**

```python
# app/api/send.py
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from app import jobs, outreach
from app.channels.email_adapter import send_email
from app.main_deps import DB_PATH, get_conn
from app.db import connect

router = APIRouter(prefix="/api/send")

# Injectable for tests; defaults to real SMTP send.
SENDER = send_email
DELAY_RANGE = (16, 28)
DEFAULT_ATTACHMENT = r"C:\Users\Administrator\Desktop\Recent-led-projects-poster-4k.jpg"


class EmailSendRequest(BaseModel):
    lead_nos: list[int]
    subject: str
    body: str
    attachment: str | None = DEFAULT_ATTACHMENT


def _run(job_id: str, req: EmailSendRequest):
    conn = connect(DB_PATH)
    try:
        result = outreach.send_campaign(
            conn, req.lead_nos, req.subject, req.body, req.attachment,
            sender=SENDER, delay_range=DELAY_RANGE,
            on_progress=lambda done, total: jobs.update(job_id, done))
        jobs.finish(job_id, result)
    except Exception as exc:  # noqa: BLE001
        jobs.fail(job_id, str(exc))
    finally:
        conn.close()


@router.post("/email")
def send_email_campaign(req: EmailSendRequest, background: BackgroundTasks, conn=Depends(get_conn)):
    eligible = outreach.eligible_leads(conn, req.lead_nos, "email")
    job_id = jobs.create(total=len(eligible))
    background.add_task(_run, job_id, req)
    return {"job_id": job_id, "eligible": len(eligible), "selected": len(req.lead_nos)}


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job
```

Modify `app/main.py` — add import and include router (before the static mount):

```python
from app.api import send as send_api
# ...
app.include_router(send_api.router)
```

- [ ] **Step 4: Run → PASS** (2 passed). Then full suite `python -m pytest -q` → all green.
- [ ] **Step 5: Commit** `git add backend/app/api/send.py backend/app/main.py backend/tests/test_send_api.py && git commit -m "feat: send-email campaign API with background job"`

---

### Task 5: Frontend selection + API client

**Files:** Modify `frontend/src/types.ts`, `frontend/src/api.ts`, `frontend/src/components/LeadsTable.tsx`

- [ ] **Step 1: Extend types.ts (append)**

```typescript
export interface SendJob {
  id: string; status: string; done: number; total: number;
  result: { sent: number; failed: number; skipped: number; errors: { no: number; error: string }[] } | { error: string } | null;
}
```

- [ ] **Step 2: Extend api.ts (append)**

```typescript
import type { SendJob } from "./types";

export async function startEmailSend(body: { lead_nos: number[]; subject: string; body: string }): Promise<{ job_id: string; eligible: number; selected: number }> {
  const r = await fetch("/api/send/email", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`send ${r.status}`);
  return r.json();
}

export async function fetchJob(id: string): Promise<SendJob> {
  const r = await fetch(`/api/send/jobs/${id}`);
  if (!r.ok) throw new Error(`job ${r.status}`);
  return r.json();
}
```

- [ ] **Step 3: Add selection checkboxes to LeadsTable.tsx** (replace file)

```tsx
import type { Lead } from "../types";

export function LeadsTable({ leads, selected, onToggle, onToggleAll }: {
  leads: Lead[]; selected: Set<number>;
  onToggle: (no: number) => void; onToggleAll: (checked: boolean) => void;
}) {
  const th = { textAlign: "left" as const, padding: "8px 10px", borderBottom: "2px solid #30363d", position: "sticky" as const, top: 0, background: "#0d1117" };
  const td = { padding: "8px 10px", borderBottom: "1px solid #21262d" };
  const allChecked = leads.length > 0 && leads.every((l) => selected.has(l.no));
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", color: "#e6edf3", fontSize: 14 }}>
      <thead><tr>
        <th style={th}><input type="checkbox" checked={allChecked} onChange={(e) => onToggleAll(e.target.checked)} /></th>
        <th style={th}>#</th><th style={th}>公司</th><th style={th}>国家</th>
        <th style={th}>城市</th><th style={th}>Email</th><th style={th}>渠道状态</th>
      </tr></thead>
      <tbody>
        {leads.map((l) => (
          <tr key={l.no}>
            <td style={td}><input type="checkbox" checked={selected.has(l.no)} onChange={() => onToggle(l.no)} /></td>
            <td style={td}>{l.no}</td>
            <td style={td}>{l.website ? <a href={`https://${l.website}`} target="_blank" rel="noreferrer" style={{ color: "#58a6ff" }}>{l.company_en}</a> : l.company_en}</td>
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

- [ ] **Step 4: Typecheck** `cd frontend && npx tsc --noEmit` — expected: FAIL only in App.tsx (LeadsTable props changed); fixed in Task 6.
- [ ] **Step 5: Commit** `git add frontend/src/types.ts frontend/src/api.ts frontend/src/components/LeadsTable.tsx && git commit -m "feat: lead selection checkboxes + send API client"`

---

### Task 6: OutreachPanel + wire into App

**Files:** Create `frontend/src/components/OutreachPanel.tsx`; Modify `frontend/src/App.tsx`

Default template mirrors the existing email copy. `{name}` → company name.

- [ ] **Step 1: Create OutreachPanel.tsx**

```tsx
import { useState } from "react";
import { startEmailSend, fetchJob } from "../api";
import type { SendJob } from "../types";

const DEFAULT_SUBJECT = "Recent LED Display Installations in Korea";
const DEFAULT_BODY = `Hi {name},

I'm Allen, from an LED display manufacturing factory in Shenzhen, China.

I came across your LED video wall and display work and wanted to share a recent project reference from Korea. The attached sheet includes indoor fine-pitch LED walls, outdoor LED screens, and commercial installations.

If you ever need LED panels or full displays, I can recommend options based on size, viewing distance, pixel pitch, and indoor/outdoor use.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp/WeChat: +86 135-7087-1001
Email: allenma2ong@gmail.com`;

export function OutreachPanel({ selected, onDone }: { selected: number[]; onDone: () => void }) {
  const [subject, setSubject] = useState(DEFAULT_SUBJECT);
  const [body, setBody] = useState(DEFAULT_BODY);
  const [job, setJob] = useState<SendJob | null>(null);
  const [msg, setMsg] = useState("");
  const [sending, setSending] = useState(false);

  async function send() {
    if (selected.length === 0) { setMsg("请先勾选客户"); return; }
    setSending(true); setMsg(""); setJob(null);
    try {
      const start = await startEmailSend({ lead_nos: selected, subject, body });
      setMsg(`已选 ${start.selected} 家，符合发送条件（有邮箱且未发过）${start.eligible} 家，开始发送…`);
      const poll = setInterval(async () => {
        const j = await fetchJob(start.job_id);
        setJob(j);
        if (j.status !== "running") {
          clearInterval(poll); setSending(false); onDone();
        }
      }, 1500);
    } catch (e) { setMsg("发送失败：" + String(e)); setSending(false); }
  }

  const box = { background: "#0d1117", color: "#e6edf3", border: "1px solid #30363d", borderRadius: 6, padding: 8, width: "100%" };
  return (
    <div style={{ background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 16, marginBottom: 20 }}>
      <h3 style={{ color: "#e6edf3", marginTop: 0 }}>邮件触达（已选 {selected.length} 家）</h3>
      <input style={{ ...box, marginBottom: 8 }} value={subject} onChange={(e) => setSubject(e.target.value)} />
      <textarea style={{ ...box, height: 180, fontFamily: "inherit" }} value={body} onChange={(e) => setBody(e.target.value)} />
      <div style={{ marginTop: 10, display: "flex", gap: 12, alignItems: "center" }}>
        <button onClick={send} disabled={sending}
          style={{ background: sending ? "#30363d" : "#238636", color: "#fff", border: "none", borderRadius: 6, padding: "8px 18px", cursor: sending ? "default" : "pointer" }}>
          {sending ? "发送中…" : "发送邮件"}
        </button>
        {job && <span style={{ color: "#8b949e" }}>进度 {job.done}/{job.total}
          {job.status === "done" && job.result && "sent" in job.result &&
            ` — 成功 ${job.result.sent}，失败 ${job.result.failed}，跳过 ${job.result.skipped}`}
          {job.status === "error" && job.result && "error" in job.result && ` — 错误：${job.result.error}`}
        </span>}
      </div>
      {msg && <div style={{ color: "#8b949e", marginTop: 8 }}>{msg}</div>}
    </div>
  );
}
```

- [ ] **Step 2: Rewrite App.tsx** (adds selection state + panel)

```tsx
import { useEffect, useState } from "react";
import { fetchLeads, fetchStats } from "./api";
import type { Lead, Stats } from "./types";
import { StatCards } from "./components/StatCards";
import { LeadsTable } from "./components/LeadsTable";
import { OutreachPanel } from "./components/OutreachPanel";

export function App() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [country, setCountry] = useState("");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [err, setErr] = useState("");

  function reload() {
    fetchStats().then(setStats).catch((e) => setErr(String(e)));
    fetchLeads({ country, search }).then(setLeads).catch((e) => setErr(String(e)));
  }
  useEffect(() => { fetchStats().then(setStats).catch((e) => setErr(String(e))); }, []);
  useEffect(() => { fetchLeads({ country, search }).then(setLeads).catch((e) => setErr(String(e))); }, [country, search]);

  const toggle = (no: number) => setSelected((s) => { const n = new Set(s); n.has(no) ? n.delete(no) : n.add(no); return n; });
  const toggleAll = (checked: boolean) => setSelected(checked ? new Set(leads.map((l) => l.no)) : new Set());

  const input = { background: "#0d1117", color: "#e6edf3", border: "1px solid #30363d", borderRadius: 6, padding: "6px 10px" };
  return (
    <div style={{ fontFamily: "system-ui, sans-serif", background: "#0d1117", minHeight: "100vh", padding: 24 }}>
      <h1 style={{ color: "#e6edf3" }}>客户开发看板</h1>
      {err && <div style={{ color: "#f85149" }}>加载失败：{err}</div>}
      {stats && <StatCards stats={stats} />}
      <OutreachPanel selected={[...selected]} onDone={reload} />
      <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
        <select style={input} value={country} onChange={(e) => setCountry(e.target.value)}>
          <option value="">全部国家</option>
          {stats && Object.keys(stats.by_country).sort().map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <input style={input} placeholder="搜索公司/网站/城市" value={search} onChange={(e) => setSearch(e.target.value)} />
        <span style={{ color: "#8b949e", alignSelf: "center" }}>{leads.length} 条 · 已选 {selected.size}</span>
      </div>
      <LeadsTable leads={leads} selected={selected} onToggle={toggle} onToggleAll={toggleAll} />
    </div>
  );
}
```

- [ ] **Step 3: Typecheck + build** `cd frontend && npx tsc --noEmit && npm run build` — expected: no errors, dist produced.
- [ ] **Step 4: Commit** `git add frontend/src/components/OutreachPanel.tsx frontend/src/App.tsx && git commit -m "feat: outreach panel — select leads and send email campaign from UI"`

---

### Task 7: End-to-end smoke + finish

**Files:** Modify `frontend/tests/smoke.spec.ts` (append a panel-visible assertion)

- [ ] **Step 1: Append smoke assertion**

```typescript
test("outreach panel is present", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "发送邮件" })).toBeVisible();
  await expect(page.getByText(/邮件触达/)).toBeVisible();
});
```

- [ ] **Step 2: Full backend suite** `cd backend && python -m pytest -q` → all green.
- [ ] **Step 3: Rebuild frontend + run smoke** — start `python -m uvicorn app.main:app --port 8000` (from backend), then `cd frontend && npm run build && npx playwright test`. Expected: 2 passed.

  > SAFETY: the smoke test only loads the page and checks the button exists. It MUST NOT click 发送邮件 (that would send real emails).

- [ ] **Step 4: Commit** `git add frontend/tests/smoke.spec.ts && git commit -m "test: smoke assertion for outreach panel"`

---

## Self-Review

**Spec coverage (S3):** Outreach Engine → Task 2. EmailAdapter (channel adapter) → Task 1. Campaign API + background job → Tasks 3–4. UI select + send + progress → Tasks 5–6. ✓
**Safety:** eligibility skips no-email + already-messaged (Task 2 test); rate-limited (delay_range); smoke test never clicks send. ✓
**Placeholder scan:** none — all steps have complete code. ✓
**Type consistency:** `send_campaign(conn, lead_nos, subject, body, attachment, sender, delay_range, on_progress)` identical across outreach.py, api/send.py, tests. `SendJob.result` union handled in OutreachPanel with `"sent" in result` / `"error" in result` guards matching jobs.finish/fail shapes. `LeadsTable` new props (selected/onToggle/onToggleAll) match App usage. ✓
**Note:** `_mark_messaged` uses `ON CONFLICT(lead_no, channel)` — matches the `UNIQUE(lead_no, channel)` constraint from the S1 schema.
