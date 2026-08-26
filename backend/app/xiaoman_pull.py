"""Sign in to Xiaoman once, then find and capture whatever history it will show us.

The sub-account cannot use the export button, so this reads the same records through the
pages Allen can already see. Two earlier passes each needed their own sign-in — Xiaoman
does not seem to keep the session across browser launches — so everything happens in one
run: sign in, walk the candidate pages, and keep the JSON the page's own API returned.

Capturing the API response rather than the rendered table is deliberate. A table read off
the DOM breaks when their frontend changes and silently loses columns that were only
shown on hover; the response behind it is the same data the page received.

Nothing is written back to Xiaoman, and nothing enters the lead book here. The captured
JSON lands in `xiaoman_raw/` for `app.import_customers` to work from, so the import is
still a separate, previewable step.

Run:  python -m app.xiaoman_pull
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

from app.xiaoman_probe import LOGIN_MARKERS, PROFILE, safe_url

OUT_DIR = Path("xiaoman_raw")
LOGIN_TIMEOUT_SECONDS = 420
START = "https://crm.xiaoman.cn/crm/customer/list"

PAGES = [
    ("我的客户", "https://crm.xiaoman.cn/crm/customer/list"),
    ("公海客户", "https://crm.xiaoman.cn/crm/customer/open-sea"),
    ("线索", "https://crm.xiaoman.cn/crm/lead/list"),
    ("已发送邮件", "https://crm.xiaoman.cn/pro/mail/sent"),
    ("收件箱", "https://crm.xiaoman.cn/pro/mail/inbox"),
]

_COUNT = re.compile(r"共\s*([\d,]+)\s*条|([\d,]+)\s*个客户|共\s*([\d,]+)\s*封")
# The calls worth keeping the body of: a list, a search, or a mailbox page.
_DATA_CALL = ("list", "search", "page", "mail", "customer", "company", "lead", "client")


def _reported_count(text: str) -> str:
    hits = [next(g for g in m.groups() if g) for m in _COUNT.finditer(text)]
    return "、".join(dict.fromkeys(hits)) if hits else "(页面没写总数)"


def _wait_for_login(page) -> bool:
    print("请在弹出的浏览器窗口里登录小满 —— 建议扫码，最省事。")
    print("等待中，最多 7 分钟…")
    deadline = time.time() + LOGIN_TIMEOUT_SECONDS
    while time.time() < deadline:
        time.sleep(3)
        try:
            text = page.inner_text("body")[:3000]
        except Exception:  # noqa: BLE001 — mid-navigation
            continue
        if any(marker in text for marker in LOGIN_MARKERS) or "login" in page.url.lower():
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

    OUT_DIR.mkdir(exist_ok=True)
    PROFILE.mkdir(parents=True, exist_ok=True)
    captured: list[dict] = []
    summary: list[dict] = []

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), headless=False,
            args=["--window-position=60,60", "--window-size=1400,900"])
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        def note(response) -> None:
            url = response.url
            if "/api/" not in url or response.status >= 400:
                return
            if not any(word in url.lower() for word in _DATA_CALL):
                return
            try:
                body = response.json()
            except Exception:  # noqa: BLE001 — not every call answers JSON
                return
            captured.append({"url": safe_url(url), "method": response.request.method,
                             "body": body})

        page.on("response", note)
        page.goto(START, wait_until="domcontentloaded")
        if not _wait_for_login(page):
            print("等待超时，没有完成登录。")
            ctx.close()
            return

        for label, url in PAGES:
            print(f"\n=== {label} ===")
            before = len(captured)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                time.sleep(8)  # the list loads after the shell
                text = page.inner_text("body")
            except Exception as exc:  # noqa: BLE001
                print("  打不开：" + str(exc)[:90])
                continue
            if any(m in text for m in LOGIN_MARKERS):
                print("  登录掉了，后面的页面读不到了")
                break
            rows = max(page.locator("tbody tr").count(),
                       page.locator("[class*=row]:not([class*=header])").count())
            count = _reported_count(text)
            new_calls = captured[before:]
            print(f"  页面报告：{count}   可见行数：{rows}   抓到 {len(new_calls)} 个接口响应")
            for call in new_calls[:5]:
                size = len(json.dumps(call["body"], ensure_ascii=False))
                print(f"    [{call['method']}] {call['url'][:110]}  ({size} 字节)")
            summary.append({"page": label, "count": count, "rows": rows,
                            "captures": len(new_calls)})

        ctx.close()

    raw = OUT_DIR / "captures.json"
    raw.write_text(json.dumps(captured, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n抓到 {len(captured)} 个接口响应，已存到 {raw.resolve()}")
    print("下一步：确认里面有客户数据后，再决定怎么映射成客户记录。")


if __name__ == "__main__":
    main()
