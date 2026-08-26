"""Pull Allen's Xiaoman history through the pages his sub-account can already see.

The export button is disabled on a sub-account, so this reads the same records the UI
reads: sign in once, then call the list APIs from inside the signed-in page, paging until
they are exhausted.

Two sources, and the difference between them matters:

- `customerV3Read/companyList` — 489 companies. Many carry `origin: OKKI Leads`, which
  means Xiaoman's own prospecting tool found them. Those are leads, not relationships.
- `mailRead/list` — 3031 sent and 1040 received. **This is the evidence of who was
  actually written to**, when, and whether they answered (`reply_flag`, `reply_time`).

Keeping them apart is the whole point. Importing a scraped lead as "already contacted"
would quietly retire a company nobody ever wrote to; importing a real customer as
"untouched" sends them a self-introduction three years into the relationship. The mail
log is what tells the two apart, so it is fetched rather than assumed (`docs/54` R1).

Nothing is written to Xiaoman and nothing enters the lead book here — the raw JSON lands
in `xiaoman_raw/` for a separate, previewable import step.

Run:  python -m app.xiaoman_fetch
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from app.xiaoman_probe import LOGIN_MARKERS, PROFILE, safe_url

OUT_DIR = Path("xiaoman_raw")
LOGIN_TIMEOUT_SECONDS = 420
START = "https://crm.xiaoman.cn/crm/customer/list"
PAGE_SIZE = 20  # the server caps it here anyway
MAX_PAGES = 200  # 6000 records per source is well past what is there

# The list page issues its POST before a listener attached after login can see it, so the
# filters are also kept here — read off the URL the page itself builds. Capturing the live
# request is still preferred; this is what makes the run work when we miss it.
DEFAULT_COMPANY_PAYLOAD = {
    "curPage": 1, "pageSize": 20,
    "show_field_key": "company.private.list.field",
    "user_num": ["1", "2"], "sort_scene": "setting",
    "show_all": 0, "_p_swarm_id": "1", "swarm_id": "1",
}


def _wait_for_login(page) -> bool:
    print("请在弹出的窗口里登录小满（扫码最省事）。等待中，最多 7 分钟…")
    deadline = time.time() + LOGIN_TIMEOUT_SECONDS
    while time.time() < deadline:
        time.sleep(3)
        try:
            text = page.inner_text("body")[:3000]
        except Exception:  # noqa: BLE001 — mid-navigation
            continue
        if any(m in text for m in LOGIN_MARKERS) or "login" in page.url.lower():
            continue
        if "重新设置" in text or "retrieve" in page.url.lower():
            print("停在密码重置页 —— 先完成重设，或退回去用扫码登录。")
            continue
        print("已登录：" + safe_url(page.url))
        return True
    return False


_MAIL_JS = """
async ([type, folder, size, maxPages]) => {
  const out = [];
  for (let page = 1; page <= maxPages; page++) {
    const url = `/api/mailRead/list?type=${type}&page=${page}&tag_id=0`
      + `&folder_id=${folder}&todo_completed_flag=0&page_size=${size}&user_mail_id=0`;
    const r = await fetch(url, {credentials: 'include'});
    if (!r.ok) break;
    const body = await r.json();
    const rows = (body.data && (body.data.list || body.data.rows)) || [];
    out.push(...rows);
    // An empty page is the end. "Fewer than asked for" is not: the server caps a page
    // at its own size, which would stop the loop after page one.
    if (rows.length === 0) break;
    const total = (body.data && body.data.count) || 0;
    if (total && out.length >= total) break;
    await new Promise(s => setTimeout(s, 400));
  }
  return out;
}
"""

# The company list is a POST whose body the page builds itself, so the request the UI
# just made is replayed with the page number swapped rather than reconstructed here.
_COMPANY_JS = """
async ([payload, size, maxPages]) => {
  const out = [];
  for (let page = 1; page <= maxPages; page++) {
    // Whatever this API calls its page number, the captured body already has it —
    // overwrite every plausible spelling rather than assuming one.
    const body = {...payload};
    for (const k of ['curPage', 'cur_page', 'page', 'pageNo', 'page_no', 'pageNum']) {
      if (k in body) body[k] = page;
    }
    if (!['curPage','cur_page','page','pageNo','page_no','pageNum'].some(k => k in body)) {
      body.curPage = page;
    }
    const r = await fetch('/api/customerV3Read/companyList', {
      method: 'POST', credentials: 'include',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body),
    });
    if (!r.ok) break;
    const data = await r.json();
    const rows = (data.data && data.data.list) || [];
    out.push(...rows);
    // The server caps a page at its own size, so "fewer than asked for" is true every
    // time and would end the loop after page one. An empty page is the real end.
    if (rows.length === 0) break;
    const total = (data.data && data.data.totalItem) || 0;
    if (total && out.length >= total) break;
    await new Promise(s => setTimeout(s, 400));
  }
  return out;
}
"""


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from playwright.sync_api import sync_playwright

    OUT_DIR.mkdir(exist_ok=True)
    PROFILE.mkdir(parents=True, exist_ok=True)
    payloads: dict[str, dict] = {}

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), headless=False,
            args=["--window-position=60,60", "--window-size=1400,900"])
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        def note(request) -> None:
            if "customerV3Read/companyList" in request.url and request.method == "POST":
                try:
                    payloads["company"] = json.loads(request.post_data or "{}")
                except Exception:  # noqa: BLE001
                    pass

        page.on("request", note)
        page.goto(START, wait_until="domcontentloaded")
        if not _wait_for_login(page):
            print("等待超时，没有完成登录。")
            ctx.close()
            return
        # Reload the list now that we are signed in, so its POST is definitely observed.
        # Guessing the body from the URL produced a payload whose page parameter the API
        # ignored: 25 pages came back, all of them page one.
        payloads.clear()
        page.goto(START, wait_until="domcontentloaded")
        time.sleep(10)

        results: dict[str, list] = {}

        payload = payloads.get("company")
        if payload is None:
            print("\n没抓到客户列表的请求体，跳过客户（邮件照抓）。")
        else:
            print("\n抓客户列表（用页面自己的筛选条件）…")
            print("  请求体字段：" + ", ".join(sorted(payload)))
            rows = page.evaluate(_COMPANY_JS, [payload, PAGE_SIZE, MAX_PAGES])
            unique = len({r.get("company_id") for r in rows})
            results["companies"] = rows
            print(f"  拿到 {len(rows)} 条，去重后 {unique} 家")

        # No separate contact fetch: the company record already carries its main
        # contact's address at customer.email_info.

        for label, key, mail_type, folder in (("已发送", "sent", "send", 2),
                                              ("收件箱", "received", "receive", 1)):
            if (OUT_DIR / f"{key}.json").exists():
                print(f"{label}邮件已在本地，跳过")
                continue
            print(f"抓{label}邮件…")
            rows = page.evaluate(_MAIL_JS, [mail_type, folder, PAGE_SIZE, MAX_PAGES])
            results[key] = rows
            print(f"  拿到 {len(rows)} 封")

        ctx.close()

    for name, rows in results.items():
        out = OUT_DIR / f"{name}.json"
        out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{name}: {len(rows)} 条 -> {out}")
    print("\n下一步：python -m app.xiaoman_import  （先预览，不写库）")


if __name__ == "__main__":
    main()
