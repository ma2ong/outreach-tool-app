"""
IG DM v55 retry - uses Instagram direct/new composer for accounts where profile Message opens an existing-thread shell.
"""
from ig_dm_v55 import (
    CDP,
    IG_PIPELINE,
    IMAGE_PATH,
    TODAY,
    cdp,
    eval_js,
    set_files,
    type_text,
    mark_sent,
)
import json
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

TARGETS = [
    {
        "no": 752,
        "username": "freedomfunusa",
        "company_en": "Freedom Fun USA Oklahoma City",
        "city": "Oklahoma City, OK",
        "message": (
            "Hi! I'm from Shenzhen, China. I saw your LED screen rentals for Oklahoma City events "
            "and wanted to share a few recent LED projects we delivered in Korea. "
            "For your outdoor event screens, what pixel pitch do you usually prefer?"
        ),
    },
    {
        "no": 753,
        "username": "kear_media_boise",
        "company_en": "KEAR Media",
        "city": "Boise, ID",
        "message": (
            "Hi! I'm from Shenzhen, China. Your mobile video wall work around Boise caught my eye. "
            "Sharing a few recent LED projects we delivered in Korea. "
            "For your mobile truck setup, do you usually need lightweight outdoor panels or fixed cabinets?"
        ),
    },
    {
        "no": 757,
        "username": "anytime_party_machines_usa_",
        "company_en": "Anytime Party Machines USA",
        "city": "Atlanta / Knoxville / Nashville",
        "message": (
            "Hi! I'm from Shenzhen, China. I saw your indoor and outdoor LED wall rentals for events. "
            "Sharing a few recent LED projects we delivered in Korea. "
            "Do your clients ask more for quick rental setups or larger fixed-looking LED walls?"
        ),
    },
]


def open_tab(url):
    return cdp(f"/new?url={url}", timeout=35).get("targetId", "")


def close_tab(tid):
    cdp(f"/close?target={tid}")


def already_sent(target):
    data = json.load(open(IG_PIPELINE, encoding="utf-8"))
    return any(
        (row.get("no") == target["no"] or str(row.get("username", "")).lower() == target["username"].lower())
        and row.get("status") == "messaged"
        for row in data
    )


def try_image_direct(tid):
    upload = set_files(tid, 'input[type="file"]', [IMAGE_PATH])
    print(f"  direct setFiles: {upload}", flush=True)
    time.sleep(3)
    sent = eval_js(tid, r"""
(function() {
  const buttons = Array.from(document.querySelectorAll("[role=button],button"));
  const btn = buttons.find(b => {
    const label = (b.getAttribute("aria-label") || b.innerText || "").trim();
    return label === "Send" || label === "发送";
  });
  if (btn) { btn.click(); return JSON.stringify({ok:true}); }
  return JSON.stringify({ok:false});
})()
""")
    try:
        return bool(json.loads(sent or "{}").get("ok"))
    except Exception:
        return False


def send_via_new_composer(target):
    tid = open_tab("https://www.instagram.com/direct/new/")
    if not tid:
        return False, False
    try:
        time.sleep(10)
        cdp(f"/activate?target={tid}")
        time.sleep(2)

        focus = eval_js(tid, r"""
(function() {
  const inputs = Array.from(document.querySelectorAll("input"));
  const inp = inputs.find(i => {
    const ph = (i.getAttribute("placeholder") || i.getAttribute("aria-label") || "").toLowerCase();
    return ph.includes("search") || ph.includes("搜索");
  }) || inputs[0];
  if (inp) { inp.focus(); inp.click(); return JSON.stringify({ok:true,ph:inp.placeholder||inp.getAttribute("aria-label")||""}); }
  return JSON.stringify({ok:false,inputs:inputs.length});
})()
""")
        print(f"  search focus: {focus}", flush=True)
        type_text(tid, target["username"])
        time.sleep(5)

        selected = eval_js(tid, rf"""
(function() {{
  const username = "{target['username']}".toLowerCase();
  const nodes = Array.from(document.querySelectorAll("[role=button],button,div,span"));
  const hit = nodes.find(n => (n.innerText || "").toLowerCase().includes(username));
  if (hit) {{
    let el = hit;
    for (let i = 0; i < 6; i++) {{
      if (el.getAttribute && (el.getAttribute("role") === "button" || el.tagName === "BUTTON")) break;
      if (!el.parentElement) break;
      el = el.parentElement;
    }}
    el.click();
    return JSON.stringify({{ok:true,text:(hit.innerText||"").slice(0,80)}});
  }}
  return JSON.stringify({{ok:false,body:document.body.innerText.slice(0,200)}});
}})()
""")
        print(f"  select user: {selected}", flush=True)
        time.sleep(2)

        chat = eval_js(tid, r"""
(function() {
  const buttons = Array.from(document.querySelectorAll("[role=button],button"));
  const btn = buttons.find(b => {
    const t = (b.innerText || b.getAttribute("aria-label") || "").trim();
    return t === "Chat" || t === "聊天" || t === "Next" || t === "下一步";
  });
  if (btn) { btn.click(); return JSON.stringify({ok:true,text:(btn.innerText||btn.getAttribute("aria-label")||"").trim()}); }
  return JSON.stringify({ok:false,buttons:buttons.map(b=>(b.innerText||b.getAttribute("aria-label")||"").trim()).filter(Boolean).slice(0,15)});
})()
""")
        print(f"  chat button: {chat}", flush=True)
        time.sleep(8)

        image_sent = try_image_direct(tid)

        eval_js(tid, r"""
(function() {
  const boxes = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"));
  const box = boxes.find(e => e.offsetParent !== null) || boxes[boxes.length - 1];
  if (box) { box.focus(); box.click(); }
})()
""")
        time.sleep(0.5)
        type_text(tid, target["message"])
        time.sleep(1)
        typed = eval_js(tid, r"""
(function() {
  const boxes = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"));
  const box = boxes.find(e => e.offsetParent !== null) || boxes[boxes.length - 1];
  return box ? String(box.innerText.trim().length) : "0";
})()
""")
        print(f"  input len: {typed}", flush=True)
        if int(typed or "0") < 10:
            return image_sent, False

        sent = eval_js(tid, r"""
(function() {
  const buttons = Array.from(document.querySelectorAll("[role=button],button"));
  const btn = buttons.find(b => {
    const label = (b.getAttribute("aria-label") || b.innerText || "").trim();
    return label === "Send" || label === "发送";
  });
  if (btn) { btn.click(); return JSON.stringify({ok:true}); }
  return JSON.stringify({ok:false});
})()
""")
        print(f"  text send: {sent}", flush=True)
        try:
            return image_sent, bool(json.loads(sent or "{}").get("ok"))
        except Exception:
            return image_sent, False
    finally:
        close_tab(tid)


def main():
    print(f"=== IG DM v55 retry | {len(TARGETS)} targets | {TODAY} ===", flush=True)
    sent = 0
    for target in TARGETS:
        print(f"\n@{target['username']} | no:{target['no']}", flush=True)
        if already_sent(target):
            print("  SKIP: already sent", flush=True)
            continue
        image_sent, text_sent = send_via_new_composer(target)
        if text_sent:
            mark_sent(target, image_sent, target["message"])
            sent += 1
            print(f"  SENT | image={image_sent}", flush=True)
        else:
            print(f"  FAILED | image={image_sent}", flush=True)
        time.sleep(6)
    print(f"\n=== Done: {sent}/{len(TARGETS)} sent ===", flush=True)


if __name__ == "__main__":
    main()
