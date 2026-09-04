import os
import queue
import re
import subprocess
import threading
import time
import urllib.parse
from pathlib import Path

LOGIN_URLS = {
    "whatsapp": "https://web.whatsapp.com/",
    "instagram": "https://www.instagram.com/accounts/login/",
    "facebook": "https://www.facebook.com/login/",
}
DATA_DIR = Path(os.environ.get("OUTREACH_BROWSER_DIR", str(Path.home() / ".outreach-tool" / "browser")))

# selector that indicates a logged-in (connected) session
_CONNECTED = {
    "whatsapp": "#pane-side",
    "instagram": "svg[aria-label='Home'], a[href='/']",
    "facebook": "div[role='navigation'], a[aria-label='Home'], a[href*='/me/']",
}
# selector for the login QR / code (whatsapp only)
_QR = {
    "whatsapp": "canvas[aria-label*='Scan'], div[data-ref], canvas",
}


class PlaywrightEngine:
    """Owns a worker thread running the sync Playwright API (which must stay on one
    thread). Public methods are thread-safe and block on the worker via a future."""

    def __init__(self):
        self._q: queue.Queue = queue.Queue()
        self._thread: threading.Thread | None = None
        self._state: dict[str, str] = {}
        self._qr: dict[str, bytes | None] = {}
        self._error: dict[str, str] = {}
        self._lock = threading.Lock()

    # ---- worker-thread plumbing ----
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
                    # Fire-and-forget callers are not waiting to be told, so the
                    # failure has to be recorded here or it vanishes.
                    if fut.get("on_error"):
                        try:
                            fut["on_error"](exc)
                        except Exception:  # noqa: BLE001
                            pass
                finally:
                    fut["done"].set()

    def _call_async(self, fn, *args, on_error=None):
        """Run on the worker thread without waiting for the result."""
        self._ensure_thread()
        fut = {"done": threading.Event(), "result": None, "error": None,
               "on_error": on_error}
        self._q.put((fn, args, fut))

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
    def _kill_stale_browser(self, prof: Path) -> int:
        """Kill a leftover Playwright browser still holding this profile directory.

        Killing the server (crash, taskkill, closing the window) does NOT kill the
        chromium it launched; the orphan keeps the profile locked and every later
        launch dies with exitCode=21 — which is exactly what "Instagram won't connect"
        looked like. Chrome's renderer children quote the path (--user-data-dir="C:\\...")
        while the parent doesn't, and they hold the lock too, so match the bare path.
        Matching requires BOTH the profile path and the ms-playwright install dir,
        so Allen's own Chrome is never touched.
        """
        if os.name != "nt":
            return 0
        ps = (
            "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
            "Where-Object { $_.CommandLine -like '*" + str(prof) + "*' "
            "-and $_.ExecutablePath -like '*ms-playwright*' } | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force; $_.ProcessId }"
        )
        try:
            out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                                 capture_output=True, text=True, timeout=25)
        except Exception:  # noqa: BLE001
            return 0
        return len([line for line in out.stdout.split() if line.strip()])

    def _launch(self, prof: Path):
        args = ["--window-position=80,80", "--window-size=1100,820"]
        try:
            return self._p.chromium.launch_persistent_context(str(prof), headless=False, args=args)
        except Exception:  # noqa: BLE001
            if not self._kill_stale_browser(prof):
                raise
            time.sleep(2)
            return self._p.chromium.launch_persistent_context(str(prof), headless=False, args=args)

    def _page(self, channel):
        """A live page for this channel, relaunching the browser if the cached one died.

        `ctx.pages` is not a liveness probe: on a closed context Playwright returns an
        empty list rather than raising, so the old check passed and the very next line
        failed with "Target page, context or browser has been closed" — and it failed
        again on every retry, because the dead context stayed in the cache. Instagram
        was stuck that way. Actually using the context is the only honest test, so the
        work is attempted and a failure costs one relaunch.
        """
        last: Exception | None = None
        for attempt in (1, 2):
            ctx = self._ctx.get(channel)
            if ctx is None:
                prof = DATA_DIR / channel
                prof.mkdir(parents=True, exist_ok=True)
                ctx = self._ctx[channel] = self._launch(prof)
            try:
                live = [p for p in ctx.pages if not p.is_closed()]
                return live[0] if live else ctx.new_page()
            except Exception as exc:  # noqa: BLE001 — a dead context must not persist
                last = exc
                self._ctx.pop(channel, None)
        raise last  # type: ignore[misc]

    # Playwright's wording when the context died under a page that still reports itself
    # open. `_page` cannot see this: it returns a cached page without testing anything,
    # and `page.is_closed()` is False (docs/102 R2).
    _DEAD_CONTEXT = re.compile(
        r"Target (page|closed)|context or browser has been closed|"
        r"Target closed|browser has been closed", re.I)

    def _open(self, channel, url, timeout=60000):
        """Navigate, and treat the navigation itself as the liveness test.

        `_page`'s docstring already says using the context is the only honest test, but
        it only ever reaches that test when there is no cached page: with one, it returns
        `live[0]` untested, and the next `goto` raises. That is what stopped a WhatsApp
        send on 09-04.

        Retrying here is safe because nothing has been typed yet — a failed `goto` means
        nothing reached the customer. Nothing after this point is ever retried.
        """
        page = self._page(channel)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            return page
        except Exception as exc:  # noqa: BLE001
            if not self._DEAD_CONTEXT.search(str(exc)):
                raise
            self._ctx.pop(channel, None)     # a dead context must not be cached
        page = self._page(channel)
        page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        return page

    def _connect_op(self, channel):
        page = self._page(channel)
        page.goto(LOGIN_URLS[channel], wait_until="domcontentloaded", timeout=60000)
        return True

    def _refresh_op(self, channel):
        if channel not in self._ctx:
            return "disconnected"
        pages = self._ctx[channel].pages
        if not pages:
            return "disconnected"
        page = pages[0]
        try:
            if page.locator(_CONNECTED[channel]).first.is_visible(timeout=2500):
                self._qr[channel] = None
                return "connected"
        except Exception:  # noqa: BLE001
            pass
        if channel in _QR:
            try:
                el = page.locator(_QR[channel]).first
                if el.is_visible(timeout=2500):
                    self._qr[channel] = el.screenshot()
                    return "connecting"
            except Exception:  # noqa: BLE001
                pass
        return "connecting"

    def _send_op(self, channel, target, message, image=None):
        if channel == "whatsapp":
            url = f"https://web.whatsapp.com/send?phone={target}&text={urllib.parse.quote(message)}"
            page = self._open(channel, url)
            # invalid/unregistered number surfaces a dialog instead of a chat
            try:
                if page.get_by_text(re.compile("invalid|not.*valid|isn't on whatsapp|无效", re.I)).first.is_visible(timeout=4000):
                    raise RuntimeError("number not on WhatsApp")
            except RuntimeError:
                raise
            except Exception:  # noqa: BLE001
                pass
            box = page.locator("footer div[contenteditable='true']").first
            box.wait_for(state="visible", timeout=45000)
            page.wait_for_timeout(1500)
            page.keyboard.press("Enter")
            page.wait_for_timeout(2500)
            if image:
                self._wa_attach_image(page, image)
            return True
        if channel == "instagram":
            page = self._open(channel, f"https://www.instagram.com/{target}/")
            btn = page.get_by_role("button", name=re.compile("message|发消息|发送消息|信息", re.I)).first
            btn.click(timeout=20000)
            box = self._dm_composer(page, target)
            box.click()
            page.wait_for_timeout(400)
            page.keyboard.insert_text(message)  # Input.insertText: works with React contenteditable (Chrome 130+)
            page.wait_for_timeout(800)
            page.keyboard.press("Enter")
            page.wait_for_timeout(2000)
            if image:
                self._ig_attach_image(page, image)
            return True
        if channel == "facebook":
            # Page inbox lives on the page itself; the Message button opens the chat dock.
            page = self._open(channel, f"https://www.facebook.com/{target}")
            page.wait_for_timeout(2500)
            btn = page.get_by_role("button", name=re.compile("^(message|发消息|发送消息|send message)$", re.I)).first
            try:
                btn.click(timeout=20000)
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError("no Message button on this page (not a business page, or DMs off)") from exc
            box = self._dm_composer(page, target)
            box.click()
            page.wait_for_timeout(400)
            page.keyboard.insert_text(message)
            page.wait_for_timeout(800)
            page.keyboard.press("Enter")
            page.wait_for_timeout(2500)
            if image:
                page.locator("input[type='file']").last.set_input_files(image)
                page.wait_for_timeout(2000)
                page.keyboard.press("Enter")
                page.wait_for_timeout(4000)
            return True
        raise ValueError(f"unsupported channel {channel}")

    # ---- reading one conversation (opens the thread; marks it read on the phone) ----
    # The scan below stays list-only on purpose. This is the opt-in exception: without
    # the real message text a DM reply would be written from half a preview line, which
    # is worse than not replying at all.

    def _direction_by_geometry(self, page, rows) -> list[bool]:
        """Own messages sit on the right in every DM client. Class names churn; layout
        does not, so geometry is the fallback that keeps working after a redesign."""
        try:
            width = page.viewport_size["width"]
        except Exception:  # noqa: BLE001
            width = 1280
        out = []
        for row in rows:
            try:
                box = row.bounding_box()
                out.append(bool(box and (box["x"] + box["width"] / 2) > width * 0.55))
            except Exception:  # noqa: BLE001
                out.append(False)
        return out

    def _read_thread_op(self, channel, target, limit=20):
        page = self._page(channel)
        if channel == "whatsapp":
            page.goto(f"https://web.whatsapp.com/send?phone={target}",
                      wait_until="domcontentloaded", timeout=60000)
            page.locator("#main").first.wait_for(state="visible", timeout=45000)
            page.wait_for_timeout(2500)
            rows = page.locator("#main div.message-in, #main div.message-out").all()[-limit:]
            msgs = []
            for row in rows:
                try:
                    cls = row.get_attribute("class") or ""
                    text = row.inner_text(timeout=2000)
                except Exception:  # noqa: BLE001
                    continue
                msgs.append({"text": text, "outgoing": "message-out" in cls})
            if msgs:
                return msgs
            # markup moved: fall back to generic rows + geometry rather than returning nothing
            rows = page.locator("#main div[role='row']").all()[-limit:]
        elif channel in ("instagram", "facebook"):
            if channel == "instagram":
                page.goto(f"https://www.instagram.com/{target}/",
                          wait_until="domcontentloaded", timeout=60000)
                name = re.compile("message|发消息|发送消息|信息", re.I)
            else:
                page.goto(f"https://www.facebook.com/{target}",
                          wait_until="domcontentloaded", timeout=60000)
                name = re.compile("^(message|发消息|发送消息|send message)$", re.I)
            page.wait_for_timeout(2000)
            page.get_by_role("button", name=name).first.click(timeout=20000)
            page.locator("div[contenteditable='true'][role='textbox'], textarea[placeholder]"
                         ).first.wait_for(state="visible", timeout=30000)
            page.wait_for_timeout(2500)
            rows = page.locator("div[role='row']").all()[-limit:]
        else:
            raise ValueError(f"unsupported channel {channel}")

        directions = self._direction_by_geometry(page, rows)
        msgs = []
        for row, outgoing in zip(rows, directions):
            try:
                text = row.inner_text(timeout=2000)
            except Exception:  # noqa: BLE001
                continue
            if text and text.strip():
                msgs.append({"text": text.strip(), "outgoing": outgoing})
        return msgs

    # ---- inbound scanning (read-only: never opens a thread) ----
    # A session that quietly expired looks exactly like "no replies", so say so instead.
    _LOGGED_OUT = {
        "whatsapp": "WhatsApp 登录已过期（页面停在扫码界面）。到「渠道」页重新扫码后再扫描——"
                    "发送同样会失败，建议顺手确认一下。",
        "instagram": "Instagram 登录已过期。到「渠道」页重新登录后再扫描。",
    }
    # Logged in but no list: the markup moved, or the inbox really is empty. Blaming the
    # login here would send Allen to re-scan a QR code that was never the problem.
    _NO_LIST = "{name}已登录，但页面上找不到会话列表——可能是它改版了（需要更新选择器），也可能收件箱是空的。"
    _LOGIN_MARKER = {
        "whatsapp": "canvas[aria-label*='Scan'], canvas",
        "instagram": "input[name='username']",
    }

    def _scan_op(self, channel):
        page = self._page(channel)
        if channel == "whatsapp":
            page.goto("https://web.whatsapp.com/", wait_until="domcontentloaded", timeout=60000)
            self._wait_list(page, channel, "#pane-side", "WhatsApp")
            return self._wa_threads(page)
        if channel == "instagram":
            page.goto("https://www.instagram.com/direct/inbox/",
                      wait_until="domcontentloaded", timeout=60000)
            self._wait_list(page, channel, self._IG_ROW, "Instagram")
            return self._ig_threads(page)
        raise ValueError(f"unsupported channel {channel}")

    # Read a public profile and leave. No like, no follow, no comment — anything that
    # shows up on their side is a trace, and docs/61 already taught what one stray
    # public action costs (docs/71 R3).
    _PROFILE_SCROLLS = 2

    def _read_profile_op(self, channel, handle):
        page = self._page(channel)
        handle = str(handle or "").strip().lstrip("@")
        if not handle:
            raise ValueError("没有账号名")
        url = (f"https://www.instagram.com/{handle}/" if channel == "instagram"
               else f"https://www.facebook.com/{handle}")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)

        body = page.inner_text("body")[:6000]
        # A login wall or a missing account is an answer, not a reason to try again
        # from another angle (docs/71 R6).
        low = body.lower()
        if not body.strip():
            raise RuntimeError("页面是空的")
        if "page isn't available" in low or "user not found" in low or "找不到" in body:
            raise RuntimeError("主页不存在或已改名")
        if "log in" in low[:400] or "登录" in body[:400]:
            raise RuntimeError("需要登录才能看")

        for _ in range(self._PROFILE_SCROLLS):
            page.mouse.wheel(0, 1400)
            page.wait_for_timeout(1200)
        body = page.inner_text("body")[:12000]

        links = page.eval_on_selector_all(
            "a[href^='http']",
            "els => els.map(e => e.href).slice(0, 120)")
        return {"handle": handle, "channel": channel, "url": url,
                "text": body, "links": links}

    # The only write action added to profile browsing (docs/72 R2). Following is one
    # click; liking and commenting stay out, because a comment is public and whether it
    # gets deleted is the other company's decision, not ours (docs/61).
    _FOLLOW_LABEL = re.compile(r"^(follow|关注|팔로우|seguir|segui)$", re.I)
    _ALREADY_FOLLOWING = re.compile(
        r"following|已关注|正在关注|팔로잉|siguiendo", re.I)

    def _follow_op(self, channel, handle):
        page = self._page(channel)
        handle = str(handle or "").strip().lstrip("@")
        url = (f"https://www.instagram.com/{handle}/" if channel == "instagram"
               else f"https://www.facebook.com/{handle}")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)

        if self._ALREADY_FOLLOWING.search(page.inner_text("body")[:3000]):
            return {"handle": handle, "already": True}

        button = page.get_by_role("button", name=self._FOLLOW_LABEL).first
        try:
            button.click(timeout=15000)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"点不到关注按钮：{str(exc)[:80]}") from exc
        page.wait_for_timeout(2500)

        # Confirm it took. A click that silently did nothing, counted as a follow, would
        # spend the day's budget on nothing and hide a rate limit.
        if not self._ALREADY_FOLLOWING.search(page.inner_text("body")[:3000]):
            raise RuntimeError("点了关注但状态没变 —— 可能被限流了")
        return {"handle": handle, "already": False}

    def _wait_list(self, page, channel, selector, name, timeout=25000):
        try:
            page.wait_for_selector(selector, timeout=timeout)
        except Exception as exc:  # noqa: BLE001
            try:
                out = page.locator(self._LOGIN_MARKER[channel]).first.is_visible(timeout=2000)
            except Exception:  # noqa: BLE001
                out = False
            raise RuntimeError(
                self._LOGGED_OUT[channel] if out else self._NO_LIST.format(name=name)) from exc
        page.wait_for_timeout(2500)

    # One evaluate per pass instead of a handful of locator round-trips per row: with
    # ~200 threads the per-row version took minutes. Leaf textContent survives a row
    # scrolling out of the viewport, which innerText does not.
    _ROWS_JS = """(sel) => [...document.querySelectorAll(sel)].map(r => ({
        leaves: [...r.querySelectorAll('*')]
            .filter(e => e.children.length === 0 && (e.textContent || '').trim())
            .map(e => e.textContent.trim().slice(0, 600)),
        title: r.querySelector('span[title]')
            ? r.querySelector('span[title]').getAttribute('title') : null,
        outgoing: !!r.querySelector("span[data-icon^='msg-']"),
        unread: !!r.querySelector("span[aria-label*='unread'], span[aria-label*='未读']")
    }))"""

    def _raw_rows(self, page, selector):
        try:
            return page.evaluate(self._ROWS_JS, selector)
        except Exception:  # noqa: BLE001 — a re-render mid-read is not an error
            return []

    def _scroll_list(self, page, row_selector, collect, deadline=None, patience=3):
        """Both thread lists are virtualised: only what is on screen exists in the DOM.

        Stop after `patience` consecutive passes that add nothing — the lists load
        lazily, so a single slow pass is normal and quitting on the first one cut a
        193-thread inbox down to 121.

        Depth is bounded by a wall-clock `deadline` rather than a pass count. It has to
        reach the bottom at least once: replies that were never processed sit at their
        own last-message time, so on the first scan the ones worth finding are weeks
        deep, not at the top. Later scans hit the patience exit within seconds."""
        rows, seen = [], set()
        idle = 0
        while deadline is None or time.monotonic() < deadline:
            before = len(rows)
            collect(rows, seen)
            try:  # the wheel goes wherever the pointer is, so put it over the list
                page.locator(row_selector).last.hover(timeout=2500)
            except Exception:  # noqa: BLE001
                pass
            page.mouse.wheel(0, 1400)
            page.wait_for_timeout(1000)
            idle = idle + 1 if len(rows) == before else 0
            if idle >= patience:
                break
        return rows

    _WA_ROW = "#pane-side div[role='listitem']"
    # Wall-clock budget per channel; Instagram splits it across its three tabs.
    SCAN_BUDGET = 240

    def _wa_threads(self, page):
        """Read the chat list only. A thread whose last message is ours carries a
        delivery-status icon (msg-check / msg-dblcheck); its absence is what marks the
        last message as inbound."""
        from app import inbound

        def collect(rows, seen):
            for raw in self._raw_rows(page, self._WA_ROW):
                t = inbound.whatsapp_thread(raw["leaves"], raw["title"],
                                            raw["outgoing"], raw["unread"])
                if t and t["sender"] not in seen:
                    seen.add(t["sender"])
                    rows.append(t)

        return self._scroll_list(page, self._WA_ROW, collect,
                                 time.monotonic() + self.SCAN_BUDGET)

    # Cold replies from strangers never land in 主要 — they queue in 一般 and 陌生消息,
    # so scanning only the default tab would miss almost all of them.
    _IG_TABS = ("主要", "一般", "陌生消息", "Primary", "General", "Requests")
    _IG_ROW = "div[role='button'][tabindex]:has(img[alt='user-profile-picture'])"

    def _ig_threads(self, page):
        from app import inbound
        seen: set[str] = set()
        rows: list[dict] = []
        # Split the budget across the tabs so one crowded tab cannot starve the others —
        # 陌生消息 is where cold replies land and it is scanned last.
        share = self.SCAN_BUDGET / len(self._IG_TABS)

        def per_tab():
            return time.monotonic() + share

        def collect(acc, _seen):
            for raw in self._raw_rows(page, self._IG_ROW):
                t = inbound.instagram_thread(raw["leaves"])
                if t and t["sender"] not in seen:
                    seen.add(t["sender"])
                    acc.append(t)

        opened = 0
        for tab in self._IG_TABS:
            try:
                el = page.get_by_text(tab, exact=True).first
                if not el.is_visible(timeout=1200):
                    continue
                el.click(timeout=4000)
                page.wait_for_timeout(2500)
            except Exception:  # noqa: BLE001 — a tab this account doesn't have
                continue
            opened += 1
            rows.extend(self._scroll_list(page, self._IG_ROW, collect, per_tab()))
        if not opened:  # locale changed the tab labels — read the default view at least
            rows.extend(self._scroll_list(page, self._IG_ROW, collect, per_tab()))
        return rows

    # Probed against a live page (docs/61): the comment box calls itself
    # "以 Allen Ma 的身份评论" and the chat composer calls itself "发消息给Jaws Audio".
    # Their ancestors are plain DIVs with no role at all, so container-scoping finds
    # nothing — the label is the only thing that tells them apart.
    _DM_LABELS = re.compile(r"messag|发消息|发送消息|메시지|mensaje", re.I)
    _COMMENT_LABELS = re.compile(r"comment|评论|留言|댓글|reply|回复", re.I)

    # Probed 09-04 against both live sites: Instagram's composer carries no aria-label
    # and no placeholder at all, only `aria-placeholder="发消息..."` — which is why six
    # boxes came back "(无标签)" and nothing went out for six days. Facebook's comment
    # box repeats itself in the same attribute, so reading it makes the guard stricter
    # in the direction that matters too (docs/99 R1).
    _LABEL_ATTRS = ("aria-label", "placeholder", "aria-placeholder")

    @classmethod
    def _box_label(cls, box) -> str:
        parts = []
        for attr in cls._LABEL_ATTRS:
            try:
                value = box.get_attribute(attr)
            except Exception:  # noqa: BLE001 — element went away mid-scan
                continue
            if value and value not in parts:
                parts.append(value)
        return " ".join(parts)

    @classmethod
    def _is_comment_box(cls, label: str) -> bool:
        """A box that names itself a comment is never a private message box."""
        return bool(cls._COMMENT_LABELS.search(label or ""))

    @classmethod
    def _is_dm_box(cls, label: str) -> bool:
        return bool(cls._DM_LABELS.search(label or "")) and not cls._is_comment_box(label)

    @staticmethod
    def _slug(text: str) -> str:
        return re.sub(r"[^a-z0-9]", "", (text or "").lower())

    @classmethod
    def _addresses(cls, label: str, target: str) -> bool:
        """True when this composer is aimed at the company we meant to write to.

        The probe found two chat docks open at once — Jaws Audio and PRI Productions —
        so "the last message box on the page" is not the same thing as "this customer's
        message box". Sending into the wrong one writes a stranger's pitch to a company
        that never heard from us.
        """
        return cls._slug(target) in cls._slug(label) if target else True

    def _dm_composer(self, page, target: str = "", timeout=30000):
        """This customer's private message box, or an error — never a fallback.

        Refusing costs a day. Typing into the wrong box publishes a cold pitch as a
        public comment, or delivers it to a different company entirely (docs/61 R1).

        What identifies "this customer's" box changed under us twice, so it is no longer
        the label (docs/99 R2). Facebook writes the display name — "发消息给Rentex Audio
        Visual & Computer Rentals" — while the handle we hold is `rentexrentals`, a
        contraction that is not a substring of it; Instagram writes nothing at all.
        The fact underneath both is that `_send_op` navigated to this company's own page
        and clicked the button on it, and a real navigation destroys every dock that was
        open before. So the single message box on the page is the one we just opened.
        Two of them is the docs/61 case and is still refused.
        """
        deadline = time.time() + timeout / 1000
        seen: list[str] = []
        while True:
            candidates = []
            seen = []
            for box in page.locator(
                    "div[contenteditable='true'][role='textbox'], textarea[placeholder]").all():
                try:
                    if not box.is_visible():
                        continue
                    label = self._box_label(box)
                except Exception:  # noqa: BLE001 — element went away mid-scan
                    continue
                seen.append(label or "(无标签)")
                # A box that calls itself a comment is never a candidate, however many
                # boxes are left and however much today's queue wants to go out.
                if self._is_dm_box(label):
                    candidates.append((label, box))
            named = [b for label, b in candidates if target and self._addresses(label, target)]
            if len(named) == 1:
                return named[0]
            if len(named) > 1:
                raise RuntimeError(
                    f"several message boxes match {target!r}: {seen} — refusing to guess")
            if len(candidates) == 1:
                return candidates[0][1]
            if len(candidates) > 1:
                raise RuntimeError(
                    f"{len(candidates)} message boxes are open and none names {target!r}:"
                    f" {seen} — refusing to guess which company this would reach")
            if time.time() >= deadline:
                break
            page.wait_for_timeout(1000)
        raise RuntimeError(
            "could not confirm this customer's private message box — refusing to type,"
            f" because the box on this page would post a public comment. saw: {seen[:6]}")

    def _ig_attach_image(self, page, image):
        """Attach and actually send. Instagram parks the photo in the composer.

        The old code selected the file, waited four seconds and reported success, so the
        text went out, the picture sat in the box, and the send log said both had gone
        (docs/61 R2).
        """
        page.locator("input[type='file']").last.set_input_files(image)
        send = page.locator(
            "div[role='button'][aria-label*='Send'], div[role='button'][aria-label*='发送'],"
            " button[type='submit'], svg[aria-label*='Send']").last
        send.wait_for(state="visible", timeout=20000)
        send.click(timeout=15000)
        # Waiting is not confirmation: the preview leaving the composer is (docs/61 R2.1).
        try:
            page.locator("div[role='button'][aria-label*='Remove'],"
                         " div[aria-label*='移除']").last.wait_for(state="hidden", timeout=20000)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("image stayed in the Instagram composer — not sent") from exc
        page.wait_for_timeout(1500)

    def _wa_attach_image(self, page, image):
        page.locator("div[title='Attach'], button[aria-label*='Attach'], span[data-icon='plus'], span[data-icon='clip'], span[data-icon='plus-rounded']").first.click(timeout=15000)
        page.wait_for_timeout(800)
        page.locator("input[type='file'][accept*='image']").first.set_input_files(image)
        send = page.locator("span[data-icon='send'], span[data-icon='wds-ic-send-filled'], div[role='button'][aria-label*='Send']").first
        send.wait_for(state="visible", timeout=30000)
        send.click()
        page.wait_for_timeout(3000)

    # ---- public thread-safe API ----
    def status(self, channel: str) -> str:
        return self._state.get(channel, "disconnected")

    def send_message(self, channel: str, target: str, message: str, image: str | None = None) -> None:
        self._call(self._send_op, channel, target, message, image, timeout=150)

    def read_thread(self, channel: str, target: str, limit: int = 20) -> list[dict]:
        return self._call(self._read_thread_op, channel, target, limit, timeout=180)

    def follow(self, channel: str, handle: str) -> dict:
        """Follow one account. The only write action on a profile."""
        return self._call(self._follow_op, channel, handle, timeout=120)

    def read_profile(self, channel: str, handle: str) -> dict:
        """Open one public profile, read it, leave. Never writes anything."""
        return self._call(self._read_profile_op, channel, handle, timeout=120)

    def scan_threads(self, channel: str) -> list[dict]:
        # Instagram alone walks three tabs; 210s was cutting scans off mid-scroll.
        return self._call(self._scan_op, channel, timeout=420)

    def connect(self, channel: str) -> None:
        """Queue the launch and return; the caller polls status for the outcome.

        Waiting here made the request hang for as long as the browser took to come up,
        and through the Cloudflare tunnel that meant a gateway 502 at 100s — a failure
        page for a connection that was in fact succeeding, with none of our own error
        text in it. The panel already polls, so the answer arrives either way.
        """
        self._state[channel] = "connecting"
        self._error[channel] = ""
        self._call_async(self._connect_op, channel, on_error=self._note_error(channel))

    def _note_error(self, channel: str):
        def record(exc: Exception) -> None:
            self._error[channel] = str(exc)
            self._state[channel] = "disconnected"
        return record

    def last_error(self, channel: str) -> str:
        return self._error.get(channel, "")

    def refresh(self, channel: str) -> str:
        st = self._call(self._refresh_op, channel)
        # A launch still in flight has no context yet, so _refresh_op says
        # "disconnected". Reporting that would blink the channel grey mid-connect and
        # lose the only signal that something is happening. Failures do land here,
        # because the error callback flips the state itself.
        if st == "disconnected" and self._state.get(channel) == "connecting"                 and not self._error.get(channel):
            return "connecting"
        self._state[channel] = st
        return st

    def qr_png(self, channel: str) -> bytes | None:
        return self._qr.get(channel)
