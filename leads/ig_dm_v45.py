"""
IG DM v45 — 8 accounts (after warmup_v45)
Uses JS el.focus() + el.click() before Input.insertText to fix focus issue (v44 lesson)
"""
import json, sys, time, random, datetime, subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CDP = "http://localhost:3456"
BASE = Path(__file__).parent
IG_PIPELINE = BASE / "pipeline/instagram/prospects.json"
TODAY = datetime.date.today().isoformat()

TARGET_USERNAMES = [
    "thepenn.group",
    "conceptpixels",
    "supreme_av",
    "moonmendjs",
    "a1_visuals_",
    "myxproductions",
    "dizplayinc",
    "corysconnects",
]

MESSAGES = {
    "thepenn.group": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV and integration companies in Ohio. Your audio, video, lighting integration services across Columbus and Cincinnati look great. We supply P1.5–P3.9 indoor fine-pitch and outdoor LED panels at factory-direct pricing. If you're sourcing LED panels for client installs, happy to share specs and pricing."
    ),
    "conceptpixels": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV production companies in Nashville. Your LED video wall rental services using ROE panels for corporate and live events look impressive. We supply P1.5–P3.9 indoor fine-pitch and outdoor LED panels at factory-direct pricing. If you're looking to expand your LED inventory, happy to connect."
    ),
    "supreme_av": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV rental companies in New England. Your full-service AV production and LED video wall rentals across Boston, Worcester, and Providence look great. We supply P2–P5 indoor and outdoor LED panels at factory-direct pricing. If you're sourcing LED panels, happy to share specs and pricing."
    ),
    "moonmendjs": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for virtual production studios in Birmingham. Your LED Volume virtual production studio with Unreal Engine environments looks impressive. We supply P1.5–P2.5 fine-pitch LED panels for LED volumes and studio installations at factory-direct pricing. If you're looking to expand your LED Volume, happy to share specs."
    ),
    "a1_visuals_": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV rental companies in San Jose and the Bay Area. Your LED video wall rental services across Northern and Southern California look great. We supply P1.5–P3.9 indoor fine-pitch and outdoor LED panels at factory-direct pricing. If you're sourcing LED panels, happy to connect."
    ),
    "myxproductions": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV production companies in Oklahoma City. Your LED video wall rental and event production services across OKC look great. We supply P2–P5 indoor and outdoor LED panels at factory-direct pricing. If you're expanding your LED inventory, happy to share specs and pricing."
    ),
    "dizplayinc": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV rental companies in Detroit and across the US. Your LED video wall rental, sales, and installation services across Detroit, LA, Las Vegas, and Phoenix look impressive. We supply P1.5–P5 indoor and outdoor LED panels at factory-direct pricing. If you're sourcing panels, happy to connect."
    ),
    "corysconnects": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV companies in Oklahoma. Your full-service AV solutions and mobile LED screen rentals across Oklahoma look great. We supply P2–P5 indoor and outdoor LED panels at factory-direct pricing. If you're expanding your LED inventory, happy to share specs and pricing."
    ),
}


def cdp(path, body=None, timeout=15):
    args = ["curl", "-s", "--max-time", str(timeout)]
    if body is not None:
        args += ["-X", "POST", f"{CDP}{path}", "-d", body]
    else:
        args += [f"{CDP}{path}"]
    r = subprocess.run(args, capture_output=True, timeout=timeout + 5)
    try:
        return json.loads(r.stdout.decode("utf-8", "replace"))
    except Exception:
        return {}


def eval_js(tid, js, timeout=12):
    return cdp(f"/eval?target={tid}", js, timeout=timeout).get("value", "")


def type_text(tid, text, timeout=30):
    args = ["curl", "-s", "--max-time", str(timeout), "-X", "POST",
            f"{CDP}/type?target={tid}", "--data-binary", text.encode("utf-8")]
    r = subprocess.run(args, capture_output=True, timeout=timeout + 5)
    try:
        return json.loads(r.stdout.decode("utf-8", "replace"))
    except Exception:
        return {}


def open_tab(url):
    return cdp(f"/new?url={url}", timeout=35).get("targetId", "")


def close_tab(tid):
    cdp(f"/close?target={tid}")


FIND_INPUT_JS = r"""
(function() {
  var els = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"));
  var el = els.find(e => (e.getAttribute("aria-placeholder") || e.placeholder || "").length > 0);
  if (el) return "found:" + (el.getAttribute("aria-placeholder") || el.placeholder || "no-ph");
  return "not found:" + els.length;
})()
"""

FOCUS_JS = r"""
(function() {
  var els = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"));
  var el = els.find(e => (e.getAttribute("aria-placeholder") || e.placeholder || "").length > 0);
  if (!el && els.length > 0) el = els[els.length - 1];
  if (!el) return JSON.stringify({ok: false, count: els.length});
  el.focus(); el.click();
  return JSON.stringify({ok: true, tag: el.tagName, ph: el.getAttribute("aria-placeholder") || "", isFocused: document.activeElement === el});
})()
"""

GET_LEN_JS = r"""
(function() {
  var els = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"));
  var el = els.find(e => (e.getAttribute("aria-placeholder") || e.placeholder || "").length > 0);
  if (!el && els.length > 0) el = els[els.length - 1];
  return el ? String(el.innerText.trim().length) : "0";
})()
"""

SEND_JS = r"""
(function() {
  var btns = Array.from(document.querySelectorAll("[role=button],button"));
  var s = btns.find(b => {
    var l = b.getAttribute("aria-label") || "";
    return l === "发送" || l === "Send";
  });
  if (!s) return JSON.stringify({ok: false, reason: "send btn not found"});
  s.click();
  return JSON.stringify({ok: true});
})()
"""


def get_input_len(tid):
    try:
        return int(eval_js(tid, GET_LEN_JS) or "0")
    except Exception:
        return 0


def send_dm(username: str, message: str) -> bool:
    tid = open_tab("https://www.instagram.com/")
    if not tid:
        print("  ✗ 无法创建 tab", flush=True)
        return False
    time.sleep(3)

    print(f"  → 导航到 @{username} 主页", flush=True)
    cdp(f"/navigate?target={tid}&url=https://www.instagram.com/{username}/", timeout=35)
    cdp(f"/activate?target={tid}")
    time.sleep(12)

    info = cdp(f"/info?target={tid}")
    print(f"  URL: {info.get('url', '')[:70]}", flush=True)

    page_err = eval_js(tid, "document.body.innerText.includes('无法访问此页面') || document.body.innerText.includes('not available')")
    if page_err == "true":
        print(f"  ✗ 账号不存在", flush=True)
        close_tab(tid)
        return False

    # Click message button
    msg_r = eval_js(tid, r"""
(function() {
  var all = Array.from(document.querySelectorAll("[role=button], button"));
  var btn = all.find(b => {
    var t = (b.innerText || "").trim();
    return t === "发消息" || t === "消息" || t === "Message";
  });
  if (btn) { btn.click(); return JSON.stringify({ok: true, text: btn.innerText.trim()}); }
  return JSON.stringify({ok: false, available: all.map(b=>(b.innerText||"").trim()).filter(t=>t).slice(0,10)});
})()
""")
    try:
        mr = json.loads(msg_r) if msg_r else {}
    except Exception:
        mr = {}
    print(f"  msg btn: {mr}", flush=True)
    if not mr.get("ok"):
        close_tab(tid)
        return False

    # Poll for contenteditable (up to 25s)
    inp_check = "not found:0"
    for w in range(25):
        time.sleep(1)
        inp_check = eval_js(tid, FIND_INPUT_JS)
        if inp_check.startswith("found:"):
            print(f"  input appeared after {w+1}s: {inp_check}", flush=True)
            break
    else:
        all_btns = eval_js(tid, "Array.from(document.querySelectorAll('[role=button],button')).map(b=>b.innerText.trim()).filter(t=>t).slice(0,8).join('|')")
        print(f"  input check: {inp_check} | btns: {all_btns[:120]}", flush=True)
        close_tab(tid)
        return False

    # Focus + type (up to 3 attempts)
    typed = False
    for attempt in range(1, 4):
        focus_r = json.loads(eval_js(tid, FOCUS_JS) or "{}")
        print(f"  focus({attempt}): {focus_r}", flush=True)
        if not focus_r.get("ok"):
            break
        time.sleep(0.3)
        tr = type_text(tid, message)
        print(f"  type({attempt}): {tr}", flush=True)
        time.sleep(0.5)
        l = get_input_len(tid)
        print(f"  input len: {l}", flush=True)
        if l >= 10:
            typed = True
            break
        time.sleep(2)

    if not typed:
        print(f"  ✗ 输入失败", flush=True)
        close_tab(tid)
        return False

    time.sleep(1)
    sr = json.loads(eval_js(tid, SEND_JS) or "{}")
    if not sr.get("ok"):
        print(f"  ✗ 发送按钮未找到: {sr}", flush=True)
        close_tab(tid)
        return False

    time.sleep(2)
    verify = json.loads(eval_js(tid, r"""
(function() {
  var els = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"));
  var el = els.find(e => (e.getAttribute("aria-placeholder") || "").length > 0);
  if (!el && els.length > 0) el = els[els.length - 1];
  return JSON.stringify({inputEmpty: el ? el.innerText.trim().length <= 1 : true});
})()
""") or "{}")
    print(f"  verify: {verify}", flush=True)
    close_tab(tid)
    return verify.get("inputEmpty", False)


def mark_sent(username: str, message: str):
    data = json.load(open(IG_PIPELINE, encoding="utf-8"))
    for p in data:
        if p.get("username") == username or p.get("instagram") == username:
            p["status"] = "messaged"
            p["touch_count"] = p.get("touch_count", 0) + 1
            p["dm_sent_date"] = TODAY
            p["message_sent_date"] = TODAY
            p["dm_message_preview"] = message[:120]
            break
    with open(IG_PIPELINE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  → pipeline 已更新: @{username}", flush=True)


def main():
    data = json.load(open(IG_PIPELINE, encoding="utf-8"))
    prospects = {(p.get("username") or p.get("instagram", "")): p for p in data}
    queue = [u for u in TARGET_USERNAMES
             if u in prospects
             and prospects[u].get("status") == "prospect"
             and prospects[u].get("warmup_done")]

    print(f"=== IG DM v45 | {len(queue)} accounts | {TODAY} ===\n", flush=True)

    if not queue:
        print("无待发账号 (status=prospect AND warmup_done=True)")
        for u in TARGET_USERNAMES:
            if u in prospects:
                p = prospects[u]
                print(f"  @{u}: status={p.get('status')} warmup={p.get('warmup_done')}")
        return

    sent = 0
    for i, username in enumerate(queue, 1):
        msg = MESSAGES.get(username, "")
        p = prospects[username]
        print(f"[{i}/{len(queue)}] @{username} | {p.get('company_en', '')} | {p.get('city', '')}", flush=True)
        print(f"  消息 ({len(msg.split())} 词): {msg[:80]}...", flush=True)
        ok = send_dm(username, msg)
        if ok:
            mark_sent(username, msg)
            sent += 1
            print(f"  ✓ SENT\n", flush=True)
        else:
            print(f"  ✗ FAILED\n", flush=True)
        if i < len(queue):
            wait = random.randint(90, 150)
            print(f"  waiting {wait}s...\n", flush=True)
            time.sleep(wait)

    print(f"=== Done: {sent}/{len(queue)} DMs sent ===")


if __name__ == "__main__":
    main()
