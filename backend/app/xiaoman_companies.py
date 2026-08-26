"""Page through the Xiaoman customer list by driving the page, not by guessing its API.

Two earlier attempts replayed `customerV3Read/companyList` with a page number we picked
ourselves. The API ignored it: 25 requests came back, every one of them page one, and
"500 companies" turned out to be 20 companies repeated 25 times. Guessing a private
API's pagination is not a shortcut, it is a way to produce data that looks right.

So this drives the list the way a person would — the page number lives in the URL's
`query` blob, so we set it and let the page issue its own request — and captures the
response it receives. It verifies as it goes: if page two returns the same company ids
as page one, it stops rather than collecting the same rows again.

Run:  python -m app.xiaoman_companies
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from urllib.parse import quote

from app.xiaoman_probe import LOGIN_MARKERS, PROFILE, safe_url

OUT = Path("xiaoman_raw") / "companies.json"
LOGIN_TIMEOUT_SECONDS = 420
BASE = "https://crm.xiaoman.cn/crm/customer/list"
MAX_PAGES = 40


def _query(page_no: int) -> str:
    # A timestamp so navigating to "the same" page still reloads: after login the browser
    # already sits on page one's URL, and goto() to an identical URL fires no request.
    blob = {"curPage": page_no, "pageSize": 20,
            "show_field_key": "company.private.list.field",
            "user_num": ["1", "2"], "sort_scene": "setting",
            "show_all": 0, "_p_swarm_id": "1", "swarm_id": "1"}
    return (BASE + "?query=" + quote(json.dumps(blob, separators=(",", ":")))
            + "&_ts=" + str(int(time.time() * 1000)))


def _wait_for_login(page) -> bool:
    print("请在弹出的窗口里登录小满（扫码最省事）。等待中，最多 7 分钟…")
    deadline = time.time() + LOGIN_TIMEOUT_SECONDS
    while time.time() < deadline:
        time.sleep(3)
        try:
            text = page.inner_text("body")[:3000]
        except Exception:  # noqa: BLE001
            continue
        if any(m in text for m in LOGIN_MARKERS) or "login" in page.url.lower():
            continue
        if "重新设置" in text or "retrieve" in page.url.lower():
            print("停在密码重置页 —— 先完成重设，或退回去用扫码登录。")
            continue
        print("已登录：" + safe_url(page.url))
        return True
    return False


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from playwright.sync_api import sync_playwright

    OUT.parent.mkdir(exist_ok=True)
    inbox: list[list] = []

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), headless=False,
            args=["--window-position=60,60", "--window-size=1400,900"])
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        def note(response) -> None:
            if "customerV3Read/companyList" not in response.url or response.status >= 400:
                return
            try:
                rows = (response.json().get("data") or {}).get("list") or []
            except Exception:  # noqa: BLE001
                return
            if rows:
                inbox.append(rows)

        page.on("response", note)
        page.goto(_query(1), wait_until="domcontentloaded")
        if not _wait_for_login(page):
            print("等待超时，没有完成登录。")
            ctx.close()
            return

        collected: dict[int, dict] = {}
        previous_ids: set[int] = set()
        for page_no in range(1, MAX_PAGES + 1):
            inbox.clear()
            # goto() alone is not enough: this is a single-page app, so navigating to
            # another URL on the same origin is handled by its router and may not refetch.
            # reload() forces the page to ask the server again.
            page.goto(_query(page_no), wait_until="domcontentloaded")
            page.reload(wait_until="domcontentloaded")
            deadline = time.time() + 25
            while not inbox and time.time() < deadline:
                time.sleep(1)
            if not inbox:
                print(f"  第 {page_no} 页没有响应，停止")
                break
            rows = inbox[-1]
            ids = {r.get("company_id") for r in rows}
            if ids and ids == previous_ids:
                # The page number did not take effect; collecting more would just repeat.
                print(f"  第 {page_no} 页和上一页完全相同，停止翻页")
                break
            previous_ids = ids
            for row in rows:
                collected[row.get("company_id")] = row
            print(f"  第 {page_no} 页：{len(rows)} 条，累计 {len(collected)} 家")
            if len(rows) < 20:
                break
            time.sleep(1)

        ctx.close()

    OUT.write_text(json.dumps(list(collected.values()), ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(f"\n去重后 {len(collected)} 家 -> {OUT}")


if __name__ == "__main__":
    main()
