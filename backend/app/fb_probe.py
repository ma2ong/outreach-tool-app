"""Look at a Facebook page's chat dock without sending anything (docs/61).

A cold pitch went out as a public comment because the composer was picked with `.first`,
and the fix refuses to type unless it can confirm the box is private. That refusal is the
safe direction, but it is only useful if the confirmation actually recognises Facebook's
chat dock — and the dock's placeholder is literally "Aa", which proves nothing on its own.

So this opens a page, clicks Message, and reports what the dock is made of. It types
nothing and presses nothing: the point is to learn the shape, not to send.

Run:  python -m app.fb_probe <page-name-or-url>
"""
from __future__ import annotations

import json
import pathlib
import sys

from app.playwright_engine import DATA_DIR

DUMP = "fb_dock.json"

# What each candidate box tells us about itself.
_DESCRIBE = """
(el) => {
  const path = [];
  let node = el;
  for (let i = 0; node && i < 6; i++) {
    path.push({
      tag: node.tagName,
      role: node.getAttribute('role'),
      label: (node.getAttribute('aria-label') || '').slice(0, 60),
      testid: (node.getAttribute('data-testid') || '').slice(0, 40),
    });
    node = node.parentElement;
  }
  const r = el.getBoundingClientRect();
  return {
    label: el.getAttribute('aria-label') || '',
    placeholder: el.getAttribute('placeholder') || '',
    testid: el.getAttribute('data-testid') || '',
    visible: r.width > 0 && r.height > 0,
    x: Math.round(r.x), y: Math.round(r.y),
    ancestors: path,
  };
}
"""


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) < 2:
        print("用法：python -m app.fb_probe <主页名或 URL>")
        return
    target = sys.argv[1].rstrip("/").split("/")[-1]

    # The live service holds the real profile open, and a probe has no business
    # evicting it. A copy carries the same cookies, so we stay signed in without
    # touching the session the sender is using.
    import shutil
    import tempfile

    from playwright.sync_api import sync_playwright

    scratch = pathlib.Path(tempfile.mkdtemp(prefix="fbprobe-"))
    shutil.copytree(DATA_DIR / "facebook", scratch / "profile",
                    ignore=shutil.ignore_patterns("Singleton*", "lockfile", "*.lock"),
                    dirs_exist_ok=True)
    print(f"用 profile 副本探测（不影响正在跑的发送）：{scratch}")

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            str(scratch / "profile"), headless=False,
            args=["--window-position=80,80", "--window-size=1200,900"])
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            _probe(page, target)
        finally:
            ctx.close()
            shutil.rmtree(scratch, ignore_errors=True)


def _probe(page, target: str) -> None:
    import re

    page.goto(f"https://www.facebook.com/{target}", wait_until="domcontentloaded",
              timeout=60000)
    page.wait_for_timeout(3000)

    print(f"已打开 {target}。正在找「发消息」按钮…")
    try:
        page.get_by_role("button", name=re.compile(
            "^(message|发消息|发送消息|send message)$", re.I)).first.click(timeout=20000)
    except Exception as exc:  # noqa: BLE001
        print(f"点不到发消息按钮：{str(exc)[:120]}")
        print("（这本身也是结论：这个主页关了私信，发送时应当中止）")
        return
    page.wait_for_timeout(3500)

    boxes = page.locator(
        "div[contenteditable='true'][role='textbox'], textarea[placeholder]").all()
    found = []
    for box in boxes:
        try:
            found.append(box.evaluate(_DESCRIBE))
        except Exception:  # noqa: BLE001
            continue

    print(f"\n页面上一共有 {len(found)} 个可输入框：\n")
    for i, box in enumerate(found, 1):
        own = box["label"] or box["placeholder"] or "(没有标签)"
        print(f"[{i}] {own}   位置 y={box['y']}  可见={box['visible']}")
        for a in box["ancestors"]:
            bits = [a["tag"]]
            if a["role"]:
                bits.append(f"role={a['role']}")
            if a["label"]:
                bits.append(f"aria-label={a['label']}")
            if a["testid"]:
                bits.append(f"testid={a['testid']}")
            print("      " + " ".join(bits))
        print()

    with open(DUMP, "w", encoding="utf-8") as handle:
        json.dump(found, handle, ensure_ascii=False, indent=2)
    print(f"完整结构已存到 {DUMP}")
    print("没有输入任何文字，也没有按回车。")


if __name__ == "__main__":
    main()
