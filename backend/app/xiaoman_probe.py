"""Open Xiaoman in a persistent browser profile and report what the customer list looks like.

Step one of pulling Allen's existing customers across. The sub-account cannot use the
export button, but it can see the records — so this opens the same kind of persistent
profile the social channels already use (`~/.outreach-tool/browser/<name>`), waits for
Allen to sign in once, and then reports the page structure and the XHR calls the list
page makes.

It reads. It writes nothing to Xiaoman and nothing to the lead book: this pass exists to
find out whether the data can be taken from the page's own API (reliable) or has to come
off the rendered table (fragile), before writing the code that does it.

Run:  python -m app.xiaoman_probe
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

PROFILE = Path.home() / ".outreach-tool" / "browser" / "xiaoman"
HOME = "https://crm.xiaoman.cn/pro/customer"
LOGIN_TIMEOUT_SECONDS = 420

# "小满客户管理-登录" contains the word 客户, so looking for that word was enough to
# mistake the login page for the customer list. Look for the login form itself instead.
LOGIN_MARKERS = ("扫码登录", "密码登录", "忘记密码", "7天内自动登录")
# A URL is not automatically safe to print. A password-reset link carries a token in its
# query string, and this probe printed one to the terminal and wrote it to a file before
# anyone noticed. Anything that could be a credential is masked before it is shown or
# stored — the URL is here to identify a page, and the path alone does that.
SECRET_PARAMS = ("token", "code", "password", "pwd", "secret", "key", "sign",
                 "access_token", "session", "ticket", "auth")


def safe_url(url: str) -> str:
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

    parts = urlsplit(url)
    if not parts.query:
        return url
    kept = [(k, "***" if any(s in k.lower() for s in SECRET_PARAMS) else v)
            for k, v in parse_qsl(parts.query, keep_blank_values=True)]
    return urlunsplit(parts._replace(query=urlencode(kept)))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from playwright.sync_api import sync_playwright

    PROFILE.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), headless=False,
            args=["--window-position=60,60", "--window-size=1400,900"])
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        calls: list[dict] = []

        def note(response) -> None:
            if "/api" in response.url or response.request.resource_type == "xhr":
                calls.append({"url": safe_url(response.url), "status": response.status,
                              "method": response.request.method})

        page.on("response", note)

        print("打开 " + HOME)
        page.goto(HOME, wait_until="domcontentloaded")
        print("请在弹出的浏览器窗口里登录小满（扫码或密码都行）。登录一次就够，之后会记住。")
        print("等待中，最多 7 分钟…")

        deadline = time.time() + LOGIN_TIMEOUT_SECONDS
        signed_in = False
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
            signed_in = True
            print("已登录，当前页面：" + safe_url(page.url))
            break
        if not signed_in:
            print("等待超时：还停在登录页。重新运行一次，并在窗口里完成登录。")
            ctx.close()
            return

        time.sleep(6)  # let the list finish loading
        print("页面标题：" + page.title())

        print("\n=== 这个页面调用的接口（数据可能就从这里来）===")
        seen = set()
        for call in calls:
            key = call["url"].split("?")[0]
            if key in seen or call["status"] >= 400:
                continue
            seen.add(key)
            print(f"  [{call['method']} {call['status']}] {call['url'][:160]}")

        print("\n=== 表格结构 ===")
        for selector in ("table", "[class*=table]", "[class*=grid]", "[role=grid]",
                         "[class*=list]"):
            count = page.locator(selector).count()
            if count:
                print(f"  {selector}: {count} 个")

        print("\n=== 页面前 1200 字 ===")
        print(page.inner_text("body")[:1200])

        out = Path("xiaoman_probe.json")
        out.write_text(json.dumps(
            {"url": safe_url(page.url), "title": page.title(),
             "api_calls": [c for c in calls if c["status"] < 400]},
            ensure_ascii=False, indent=2), encoding="utf-8")
        print("\n接口清单已存到 " + str(out.resolve()))
        # The session lives in the profile directory, so the next run will not ask again.
        ctx.close()
        print("登录已保存到浏览器档案，下次抓取不用再登录。")


if __name__ == "__main__":
    main()
