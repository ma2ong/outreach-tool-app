"""Find where Allen's history actually lives in Xiaoman before writing anything that reads it.

The customer list showed "0 个客户" on his sub-account, which does not mean there is no
history — it means this list is not where it is. Xiaoman keeps records in several places
(私海/公海 customers, leads, and the mailbox), and the sub-account may see some and not
others.

So this visits each candidate page on the saved session, reports how many records it can
see and which API call produced them, and stops. Nothing is written anywhere: the point
is to choose a source deliberately rather than scrape the first page that renders.

Run:  python -m app.xiaoman_survey
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

from app.xiaoman_probe import PROFILE, safe_url

PAGES = [
    ("我的客户", "https://crm.xiaoman.cn/crm/customer/list"),
    ("公海客户", "https://crm.xiaoman.cn/crm/customer/open-sea"),
    ("线索", "https://crm.xiaoman.cn/crm/lead/list"),
    ("已发送邮件", "https://crm.xiaoman.cn/pro/mail/sent"),
    ("收件箱", "https://crm.xiaoman.cn/pro/mail/inbox"),
]

# "共 1234 条" / "1234 个客户" — how these lists report their own size.
_COUNT = re.compile(r"共\s*([\d,]+)\s*条|([\d,]+)\s*个客户|共\s*([\d,]+)\s*封")


def _reported_count(text: str) -> str:
    hits = [next(g for g in m.groups() if g) for m in _COUNT.finditer(text)]
    return "、".join(dict.fromkeys(hits)) if hits else "(页面没写总数)"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from playwright.sync_api import sync_playwright

    findings = []
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), headless=False,
            args=["--window-position=60,60", "--window-size=1400,900"])
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        for label, url in PAGES:
            calls: list[dict] = []

            def note(response, sink=calls) -> None:
                if "/api/" in response.url and response.request.resource_type == "xhr":
                    sink.append({"url": safe_url(response.url), "status": response.status,
                                 "method": response.request.method})

            page.on("response", note)
            print(f"\n=== {label} ===")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                time.sleep(7)  # the list loads after the shell
                text = page.inner_text("body")
            except Exception as exc:  # noqa: BLE001
                print(f"  打不开：{str(exc)[:100]}")
                page.remove_listener("response", note)
                continue
            page.remove_listener("response", note)

            if any(m in text for m in ("扫码登录", "密码登录")):
                print("  登录已失效，需要重新登录")
                break
            if "无权限" in text or "没有权限" in text:
                print("  这个账号没有权限看这个页面")

            count = _reported_count(text)
            rows = max(page.locator("tbody tr").count(),
                       page.locator("[class*=row]:not([class*=header])").count())
            print(f"  页面报告：{count}   可见行数：{rows}")
            interesting = [c for c in calls
                           if any(w in c["url"].lower()
                                  for w in ("list", "search", "page", "mail", "customer",
                                            "company", "lead"))]
            for call in interesting[:6]:
                print(f"    [{call['method']} {call['status']}] {call['url'][:130]}")
            snippet = " ".join(text.split())[:220]
            print(f"  页面片段：{snippet}")
            findings.append({"page": label, "url": url, "count": count, "rows": rows,
                             "api": [c["url"] for c in interesting[:6]]})

        ctx.close()

    out = Path("xiaoman_survey.json")
    out.write_text(json.dumps(findings, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n结果已存到 " + str(out.resolve()))


if __name__ == "__main__":
    main()
