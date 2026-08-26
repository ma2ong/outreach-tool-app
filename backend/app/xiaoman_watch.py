"""Record the customer list while Allen pages through it himself.

Four attempts to drive Xiaoman's pager failed in four different ways — URL routing, a
replayed API call, a clicked arrow, a filled jump box — and each one cost another QR
scan. Driving someone else's single-page app is not where this project's effort belongs.

So the split goes the other way round: clicking is the part a person does in seconds, and
recording every row that arrives is the part a person cannot do at all. The browser opens,
Allen pages through the list, and this keeps every company the page loads — deduplicated,
counted out loud, and saved when he closes the window.

What gets kept is the reason for the trouble: the tag he filed each customer under
(工程商 / 租赁客户), the contact's name and job title (이창훈 대표), and the notes he
typed into the names — (成交客户), （有回复), (已加微信). Those exist nowhere else.

Run:  python -m app.xiaoman_watch
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from app.xiaoman_probe import LOGIN_MARKERS, PROFILE, safe_url

OUT = Path("xiaoman_raw") / "customers.json"
LOGIN_TIMEOUT_SECONDS = 420
WATCH_MINUTES = 25
START = "https://crm.xiaoman.cn/crm/customer/list"


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
    collected: dict[int, dict] = {}
    # Anything already pulled in an earlier run stays; this only ever adds.
    if OUT.exists():
        for row in json.loads(OUT.read_text(encoding="utf-8")):
            collected[row.get("company_id")] = row
        print(f"本地已有 {len(collected)} 家，这次继续往上加")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), headless=False,
            args=["--window-position=40,40", "--window-size=1600,1000"])
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        def note(response) -> None:
            if "customerV3Read/companyList" not in response.url or response.status >= 400:
                return
            try:
                rows = (response.json().get("data") or {}).get("list") or []
            except Exception:  # noqa: BLE001
                return
            before = len(collected)
            for row in rows:
                collected[row.get("company_id")] = row
            if len(collected) > before:
                print(f"  收到 {len(rows)} 条，累计 {len(collected)} 家")

        page.on("response", note)
        page.goto(START, wait_until="domcontentloaded")
        if not _wait_for_login(page):
            print("等待超时，没有完成登录。")
            ctx.close()
            return

        print("\n" + "=" * 62)
        print("现在请你自己在窗口里翻页，我会把每一页自动收下来。")
        print("最快的做法：右下角把「20 条/页」改成 100，然后点 5 次下一页。")
        print("左侧点「全部客户」(489) 能拿到最全的一批。")
        print("翻完直接关掉浏览器窗口，或者等它自己结束。")
        print("=" * 62 + "\n")

        deadline = time.time() + WATCH_MINUTES * 60
        while time.time() < deadline:
            time.sleep(3)
            try:
                if not ctx.pages:  # Allen closed the window: he is done
                    break
                page.title()
            except Exception:  # noqa: BLE001 — window gone
                break
        try:
            ctx.close()
        except Exception:  # noqa: BLE001
            pass

    OUT.write_text(json.dumps(list(collected.values()), ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(f"\n收到 {len(collected)} 家 -> {OUT}")
    print("下一步：python -m app.xiaoman_import_customers  （先预览，不写库）")


if __name__ == "__main__":
    main()
