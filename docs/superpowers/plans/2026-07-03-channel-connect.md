# Channel Connection Infrastructure Implementation Plan — S5 Part 1

> Use superpowers:executing-plans. Steps use `- [ ]`.

**Goal:** Let the user connect WhatsApp / Instagram from inside the dashboard — the app self-manages a headed persistent Playwright browser, shows the WhatsApp QR in the web page to scan, detects logged-in state, and persists the session. No command line, no separate CDP service (spec S5, part 1 of 2; part 2 = sending).

**Architecture:** A `BrowserEngine` interface with two impls: `FakeEngine` (tests) and `PlaywrightEngine` (real). PlaywrightEngine owns a **worker thread** running the sync Playwright API (sync API must stay on one thread); API endpoints submit commands to it and block on a future. One headed `launch_persistent_context` per channel (own user-data-dir → session persists). Endpoints expose status, connect (open login page), and a live QR PNG. A module-level `ENGINE` seam lets tests inject `FakeEngine`. The React ConnectionPanel polls status and renders the QR image.

**De-risked:** headless is blocked by WhatsApp/IG; **headed works** — validated live (WhatsApp login page + QR container rendered, session-persist checkbox present).

**Honest boundary:** the one-time human login (scan QR / enter IG credentials+2FA) happens in the app-launched browser and cannot be automated away; the app makes it in-website and one-time. Automated DMs (part 2) risk platform bans — mitigated by rate limits + human-in-loop, not eliminated.

---

### Task 1: BrowserEngine interface + FakeEngine

**Files:** Create `backend/app/browser_engine.py`; Test `backend/tests/test_browser_engine.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_browser_engine.py
from app.browser_engine import FakeEngine


def test_fake_engine_status_and_connect():
    e = FakeEngine()
    assert e.status("whatsapp") == "disconnected"
    e.connect("whatsapp")
    assert e.status("whatsapp") == "connecting"
    e.simulate_login("whatsapp")
    assert e.status("whatsapp") == "connected"


def test_fake_engine_qr():
    e = FakeEngine()
    e.connect("whatsapp")
    assert e.qr_png("whatsapp") == b"FAKEPNG"
    e.simulate_login("whatsapp")
    assert e.qr_png("whatsapp") is None  # no QR once connected
```

- [ ] **Step 2: Run → FAIL**

- [ ] **Step 3: Implement**

```python
# app/browser_engine.py
from typing import Protocol

CHANNELS = {"whatsapp", "instagram"}


class BrowserEngine(Protocol):
    def status(self, channel: str) -> str: ...
    def connect(self, channel: str) -> None: ...
    def qr_png(self, channel: str) -> bytes | None: ...


class FakeEngine:
    """In-memory engine for tests. Status: disconnected -> connecting -> connected."""

    def __init__(self):
        self._state: dict[str, str] = {}

    def status(self, channel: str) -> str:
        return self._state.get(channel, "disconnected")

    def connect(self, channel: str) -> None:
        if self._state.get(channel) != "connected":
            self._state[channel] = "connecting"

    def simulate_login(self, channel: str) -> None:
        self._state[channel] = "connected"

    def qr_png(self, channel: str) -> bytes | None:
        return b"FAKEPNG" if self._state.get(channel) == "connecting" else None
```

- [ ] **Step 4: Run → PASS** (2). **Step 5: Commit** `feat: browser engine interface + fake engine`

---

### Task 2: PlaywrightEngine (worker thread, real browser)

**Files:** Create `backend/app/playwright_engine.py`; Test `backend/tests/test_playwright_engine_import.py`

Not unit-tested against live sites (verified live in Task 6). Only an import/instantiation smoke test here.

- [ ] **Step 1: Import test**

```python
# tests/test_playwright_engine_import.py
def test_playwright_engine_instantiates_without_launching():
    from app.playwright_engine import PlaywrightEngine
    e = PlaywrightEngine()  # must NOT launch a browser on construction
    assert e.status("whatsapp") == "disconnected"
```

- [ ] **Step 2: Run → FAIL**

- [ ] **Step 3: Implement**

```python
# app/playwright_engine.py
import os
import queue
import threading
from pathlib import Path

LOGIN_URLS = {
    "whatsapp": "https://web.whatsapp.com/",
    "instagram": "https://www.instagram.com/accounts/login/",
}
DATA_DIR = Path(os.environ.get("OUTREACH_BROWSER_DIR", str(Path.home() / ".outreach-tool" / "browser")))

# selectors to decide "connected" (logged in)
_CONNECTED = {
    "whatsapp": "#pane-side",
    "instagram": "svg[aria-label='Home'], a[href='/']",
}
_QR = {
    "whatsapp": "canvas[aria-label*='Scan'], div[data-ref], canvas",
}


class PlaywrightEngine:
    def __init__(self):
        self._q: queue.Queue = queue.Queue()
        self._thread: threading.Thread | None = None
        self._state: dict[str, str] = {}
        self._qr: dict[str, bytes | None] = {}
        self._lock = threading.Lock()

    # ---- worker thread plumbing ----
    def _ensure_thread(self):
        with self._lock:
            if self._thread is None:
                self._thread = threading.Thread(target=self._run, daemon=True)
                self._thread.start()

    def _run(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            self._p = p
            self._ctx: dict[str, object] = {}
            while True:
                fn, args, fut = self._q.get()
                try:
                    fut["result"] = fn(*args)
                except Exception as exc:  # noqa: BLE001
                    fut["error"] = exc
                finally:
                    fut["done"].set()

    def _call(self, fn, *args, timeout=180):
        self._ensure_thread()
        fut = {"done": threading.Event(), "result": None, "error": None}
        self._q.put((fn, args, fut))
        if not fut["done"].wait(timeout):
            raise TimeoutError("browser op timed out")
        if fut["error"]:
            raise fut["error"]
        return fut["result"]

    # ---- ops that run ON the worker thread ----
    def _page(self, channel):
        if channel not in self._ctx:
            prof = DATA_DIR / channel
            prof.mkdir(parents=True, exist_ok=True)
            self._ctx[channel] = self._p.chromium.launch_persistent_context(
                str(prof), headless=False, args=["--window-position=80,80", "--window-size=1100,820"])
        ctx = self._ctx[channel]
        return ctx.pages[0] if ctx.pages else ctx.new_page()

    def _connect_op(self, channel):
        page = self._page(channel)
        page.goto(LOGIN_URLS[channel], wait_until="domcontentloaded", timeout=60000)
        return True

    def _refresh_op(self, channel):
        if channel not in self._ctx:
            return "disconnected"
        page = self._ctx[channel].pages[0]
        try:
            if page.locator(_CONNECTED[channel]).first.is_visible(timeout=2500):
                self._qr[channel] = None
                return "connected"
        except Exception:  # noqa: BLE001
            pass
        # try to grab a QR (whatsapp)
        if channel in _QR:
            try:
                el = page.locator(_QR[channel]).first
                if el.is_visible(timeout=2500):
                    self._qr[channel] = el.screenshot()
                    return "connecting"
            except Exception:  # noqa: BLE001
                pass
        return "connecting"

    # ---- public (thread-safe) API ----
    def status(self, channel: str) -> str:
        if channel not in getattr(self, "_state", {}):
            return self._state.get(channel, "disconnected")
        return self._state[channel]

    def connect(self, channel: str) -> None:
        self._state[channel] = "connecting"
        self._call(self._connect_op, channel)

    def refresh(self, channel: str) -> str:
        st = self._call(self._refresh_op, channel)
        self._state[channel] = st
        return st

    def qr_png(self, channel: str) -> bytes | None:
        return self._qr.get(channel)
```

- [ ] **Step 4: Run → PASS**. **Step 5: Commit** `feat: playwright browser engine (worker thread, headed persistent context)`

---

### Task 3: Channels API

**Files:** Create `backend/app/api/channels.py`; Modify `backend/app/main.py`; Test `backend/tests/test_channels_api.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_channels_api.py
import app.main as main
import app.api.channels as ch
from app.browser_engine import FakeEngine
from fastapi.testclient import TestClient


def _client():
    ch.ENGINE = FakeEngine()
    return TestClient(main.app)


def test_list_and_connect_and_qr():
    c = _client()
    assert c.get("/api/channels").json()["whatsapp"] == "disconnected"
    assert c.post("/api/channels/whatsapp/connect").status_code == 200
    assert c.get("/api/channels").json()["whatsapp"] == "connecting"
    r = c.get("/api/channels/whatsapp/qr")
    assert r.status_code == 200 and r.content == b"FAKEPNG"
    ch.ENGINE.simulate_login("whatsapp")
    assert c.get("/api/channels/whatsapp/status").json()["status"] == "connected"
    assert c.get("/api/channels/whatsapp/qr").status_code == 404


def test_bad_channel():
    assert _client().post("/api/channels/telegram/connect").status_code == 400
```

- [ ] **Step 2: Run → FAIL**

- [ ] **Step 3: Implement**

```python
# app/api/channels.py
from fastapi import APIRouter, HTTPException, Response

from app.browser_engine import CHANNELS
from app.playwright_engine import PlaywrightEngine

router = APIRouter(prefix="/api/channels")

ENGINE = PlaywrightEngine()  # injectable in tests


def _check(channel: str):
    if channel not in CHANNELS:
        raise HTTPException(status_code=400, detail="unknown channel")


@router.get("")
def list_channels():
    return {c: ENGINE.status(c) for c in sorted(CHANNELS)}


@router.post("/{channel}/connect")
def connect(channel: str):
    _check(channel)
    ENGINE.connect(channel)
    return {"status": ENGINE.status(channel)}


@router.get("/{channel}/status")
def status(channel: str):
    _check(channel)
    st = ENGINE.refresh(channel) if hasattr(ENGINE, "refresh") else ENGINE.status(channel)
    return {"status": st}


@router.get("/{channel}/qr")
def qr(channel: str):
    _check(channel)
    png = ENGINE.qr_png(channel)
    if png is None:
        raise HTTPException(status_code=404, detail="no qr")
    return Response(content=png, media_type="image/png")
```

Modify `app/main.py`: `from app.api import channels as channels_api` and `app.include_router(channels_api.router)` (before static mount).

- [ ] **Step 4: Run → PASS** (2). Full suite green. **Step 5: Commit** `feat: channels connection API`

---

### Task 4: ConnectionPanel UI

**Files:** Modify `frontend/src/api.ts`, `frontend/src/types.ts`; Create `frontend/src/components/ConnectionPanel.tsx`; Modify `frontend/src/App.tsx`

- [ ] **Step 1: types.ts (append)** `export type ChannelStatus = Record<string, string>;`

- [ ] **Step 2: api.ts (append)**

```typescript
export async function fetchChannels(): Promise<Record<string, string>> {
  const r = await fetch("/api/channels");
  if (!r.ok) throw new Error(`channels ${r.status}`);
  return r.json();
}
export async function connectChannel(ch: string): Promise<void> {
  const r = await fetch(`/api/channels/${ch}/connect`, { method: "POST" });
  if (!r.ok) throw new Error(`connect ${r.status}`);
}
export async function channelStatus(ch: string): Promise<string> {
  const r = await fetch(`/api/channels/${ch}/status`);
  if (!r.ok) throw new Error(`status ${r.status}`);
  return (await r.json()).status;
}
```

- [ ] **Step 3: Create ConnectionPanel.tsx**

```tsx
import { useEffect, useState } from "react";
import { fetchChannels, connectChannel, channelStatus } from "../api";

const LABELS: Record<string, string> = { whatsapp: "WhatsApp", instagram: "Instagram" };

export function ConnectionPanel() {
  const [status, setStatus] = useState<Record<string, string>>({});
  const [active, setActive] = useState<string | null>(null);
  const [qrTick, setQrTick] = useState(0);

  useEffect(() => { fetchChannels().then(setStatus).catch(() => {}); }, []);

  useEffect(() => {
    if (!active) return;
    const t = setInterval(async () => {
      try {
        const st = await channelStatus(active);
        setStatus((s) => ({ ...s, [active]: st }));
        setQrTick((n) => n + 1);
        if (st === "connected") { clearInterval(t); setActive(null); }
      } catch { /* ignore */ }
    }, 3000);
    return () => clearInterval(t);
  }, [active]);

  async function connect(ch: string) {
    setStatus((s) => ({ ...s, [ch]: "connecting" }));
    setActive(ch);
    await connectChannel(ch).catch(() => {});
  }

  const dot = (st: string) => st === "connected" ? "#3fb950" : st === "connecting" ? "#d29922" : "#8b949e";
  return (
    <div style={{ background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 16, marginBottom: 20 }}>
      <h3 style={{ color: "#e6edf3", marginTop: 0 }}>渠道连接</h3>
      <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
        {Object.keys(LABELS).map((ch) => (
          <div key={ch} style={{ color: "#e6edf3" }}>
            <span style={{ display: "inline-block", width: 10, height: 10, borderRadius: 5, background: dot(status[ch] || "disconnected"), marginRight: 6 }} />
            {LABELS[ch]}：{status[ch] === "connected" ? "已连接" : status[ch] === "connecting" ? "等待登录…" : "未连接"}
            {status[ch] !== "connected" && (
              <button onClick={() => connect(ch)} style={{ marginLeft: 10, background: "#1f6feb", color: "#fff", border: "none", borderRadius: 6, padding: "4px 12px" }}>连接</button>
            )}
          </div>
        ))}
      </div>
      {active === "whatsapp" && status.whatsapp === "connecting" && (
        <div style={{ marginTop: 14, color: "#e6edf3" }}>
          <div style={{ marginBottom: 6 }}>用手机 WhatsApp 扫描下方二维码登录（登录一次长期保持）：</div>
          <img alt="WhatsApp QR" src={`/api/channels/whatsapp/qr?t=${qrTick}`} style={{ width: 260, height: 260, background: "#fff", borderRadius: 8 }} />
        </div>
      )}
      {active === "instagram" && status.instagram === "connecting" && (
        <div style={{ marginTop: 14, color: "#8b949e" }}>已打开 Instagram 登录窗口，请在弹出的浏览器窗口中登录（含验证码）。登录后状态会自动更新。</div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Wire into App.tsx** — import and render `<ConnectionPanel />` right after `{stats && <StatCards .../>}` and before `<DiscoveryPanel .../>`.

- [ ] **Step 5: Typecheck + build.** **Step 6: Commit** `feat: channel connection panel (in-website login + WhatsApp QR)`

---

### Task 5: Setup + smoke + live verify

**Files:** Modify `outreach-tool/setup.bat` (add `python -m playwright install chromium`); Modify `frontend/tests/smoke.spec.ts`

- [ ] **Step 1: setup.bat** — after installing backend deps, add:
```
echo === Installing browser engine (Playwright) ===
python -m playwright install chromium
```

- [ ] **Step 2: smoke assertion (append)**
```typescript
test("connection panel is present", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("渠道连接")).toBeVisible();
});
```

- [ ] **Step 3: Full backend suite** → green. **Step 4: Rebuild + smoke** (start one server) → all pass.

- [ ] **Step 5: LIVE verify (manual, logged-out)** — start server, POST /api/channels/whatsapp/connect, poll status (expect "connecting"), GET /api/channels/whatsapp/qr → confirm a PNG comes back (the real WhatsApp QR). Instagram connect → status "connecting". Document result. Do NOT log in (that's the user's step).

- [ ] **Step 6: Commit** `test: connection panel smoke + setup installs playwright`

---

## Self-Review
- Spec S5 part-1 (in-app connection + login) covered: engine (T1-2), API (T3), UI (T4), setup/verify (T5). ✓
- Seam `channels.ENGINE` mirrors send/discover seams for testability; FakeEngine keeps tests network-free. ✓
- Honest boundary documented; headed requirement validated live. ✓
- Part 2 (send adapters over the connected browser) is a separate plan.
