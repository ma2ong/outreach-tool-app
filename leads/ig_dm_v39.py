"""
IG DM v39 - USA pending batch (7 accounts, warmup already done)
ATH Productions (@audiotekhouston), Event Smart Technology (@event_technology_services),
DPC Event Services (@dpcevents), FireFly AV Design (@fireflyclt),
Mathes Event Productions (@eventsmathes), Worship Productions (@worshipproductions),
Palm Productions and Events (@palmproductionsandevents)
"""
import json, sys, time, random, datetime, subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CDP = "http://localhost:3456"
BASE = Path(__file__).parent
IG_PIPELINE = BASE / "pipeline/instagram/prospects.json"
TODAY = datetime.date.today().isoformat()

TARGET_USERNAMES = [
    "audiotekhouston",
    "event_technology_services",
    "dpcevents",
    "fireflyclt",
    "eventsmathes",
    "worshipproductions",
    "palmproductionsandevents",
]

MESSAGES = {
    "audiotekhouston": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV production companies in Houston. "
        "Your production services across Texas look great. "
        "We supply P2–P5 indoor and outdoor LED panels at factory-direct pricing. "
        "If you're sourcing LED panels for upcoming events, happy to share specs and pricing."
    ),
    "event_technology_services": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for event technology companies in Las Vegas. "
        "Your event tech services look impressive. "
        "We supply P2–P5 indoor and outdoor LED panels at factory-direct pricing for rental and permanent installs. "
        "If you have upcoming LED projects, happy to connect."
    ),
    "dpcevents": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for event companies in San Antonio. "
        "Your full-service event production looks great. "
        "We supply P2–P5 indoor and outdoor LED panels at factory-direct pricing. "
        "If you're sourcing LED panels, happy to share specs and pricing."
    ),
    "fireflyclt": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV design companies in Charlotte. "
        "Your AV design and integration work looks professional. "
        "We supply P1.5–P5 indoor and outdoor LED panels at factory-direct pricing. "
        "If you're specifying LED for upcoming projects, happy to connect."
    ),
    "eventsmathes": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for event production companies in Atlanta. "
        "Your event production services in the Southeast look great. "
        "We supply P2–P5 indoor and outdoor LED panels at factory-direct pricing. "
        "If you're sourcing LED panels for events, happy to share specs."
    ),
    "worshipproductions": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for church AV companies in Southern California. "
        "Church LED installs are one of our strongest segments — P1.8 and P2.5 indoor fine pitch are popular for worship environments. "
        "We supply panels at factory-direct pricing with full technical support. "
        "If you're sourcing LED for upcoming church projects, happy to share specs."
    ),
    "palmproductionsandevents": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for event production companies in Tampa. "
        "Your LED video wall and full-service event production in South Florida looks great. "
        "We supply P2–P5 indoor and outdoor LED panels at factory-direct pricing. "
        "If you're looking to expand your LED inventory, happy to connect."
    ),
}

DEFAULT_MSG = (
    "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV rental companies in the US. "
    "We supply P2–P5 indoor and outdoor LED panels at factory-direct pricing. "
    "If you're looking to expand your LED inventory, happy to connect."
)


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


def type_keys(tid, text, timeout=60):
    """Type character-by-character via CDP rawKeyDown+insertText+keyUp — triggers React search."""
    args = ["curl", "-s", "--max-time", str(timeout), "-X", "POST",
            f"{CDP}/typekeys?target={tid}", "--data-binary", text.encode("utf-8")]
    r = subprocess.run(args, capture_output=True, timeout=timeout + 5)
    try:
        return json.loads(r.stdout.decode("utf-8", "replace"))
    except Exception:
        return {}


def set_input_value(tid, text, timeout=12):
    """Set value on a regular <input> field and trigger React's onChange via native setter."""
    js = r"""
(function(val) {
  var inp = document.querySelector('input[placeholder*="搜索"]') ||
            document.querySelector('input[placeholder*="Search"]') ||
            document.querySelector('[role="combobox"] input') ||
            document.querySelector('[role="combobox"]') ||
            document.querySelector('input[type="text"]');
  if (!inp) return JSON.stringify({ok: false, reason: "input not found"});
  var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
  setter.call(inp, val);
  inp.dispatchEvent(new Event("input", {bubbles: true, cancelable: true}));
  inp.dispatchEvent(new Event("change", {bubbles: true, cancelable: true}));
  return JSON.stringify({ok: true, len: inp.value.length});
})(PLACEHOLDER_VAL)
""".replace("PLACEHOLDER_VAL", json.dumps(text))
    return eval_js(tid, js, timeout=timeout)


def open_tab(url):
    # Instagram pages take ~15s to reach readyState=complete; use 35s timeout to avoid race
    return cdp(f"/new?url={url}", timeout=35).get("targetId", "")


def close_tab(tid):
    cdp(f"/close?target={tid}")


def send_dm(username: str, message: str) -> bool:
    # Strategy: open homepage first (forces React app init), then navigate to profile,
    # then activate tab (Chrome renders React content when tab is foreground).
    # This bypasses the broken compose-dialog search (Instagram's React search
    # handler doesn't fire via CDP's rawKeyDown events).
    print(f"  → 打开 IG 主页", flush=True)
    tid = open_tab("https://www.instagram.com/")
    if not tid:
        print("  ✗ 无法创建 tab", flush=True)
        return False
    # open_tab already waits for readyState=complete; small extra buffer
    time.sleep(3)

    print(f"  → 导航到 @{username} 主页", flush=True)
    cdp(f"/navigate?target={tid}&url=https://www.instagram.com/{username}/", timeout=35)
    cdp(f"/activate?target={tid}")  # bring to foreground so React renders fully
    time.sleep(12)

    # Check URL and detect 404 page
    info = cdp(f"/info?target={tid}")
    url = info.get("url", "")
    print(f"  URL: {url[:70]}", flush=True)

    page_err = eval_js(tid, "document.body.innerText.includes('无法访问此页面') || document.body.innerText.includes('not available')")
    if page_err == "true":
        print(f"  ✗ 账号不存在或已删除", flush=True)
        close_tab(tid); return False

    # Find and click "发消息" / "Message" button on profile
    msg_result = eval_js(tid, r"""
(function() {
  var all = Array.from(document.querySelectorAll("[role=button], button"));
  var btn = all.find(b => {
    var t = (b.innerText || "").trim();
    return t === "发消息" || t === "Message";
  });
  if (btn) { btn.click(); return JSON.stringify({ok: true, text: btn.innerText.trim()}); }
  return JSON.stringify({ok: false, available: all.map(b=>(b.innerText||b.getAttribute("aria-label")||"").trim()).filter(t=>t).slice(0,15)});
})()
""")
    try:
        mr = json.loads(msg_result) if msg_result else {}
    except Exception:
        mr = {}
    print(f"  msg btn: {mr}", flush=True)
    if not mr.get("ok"):
        print(f"  ✗ Message 按钮未找到", flush=True)
        close_tab(tid); return False

    # Wait for DM view to load after clicking Message
    time.sleep(10)
    cdp(f"/activate?target={tid}")  # re-activate in case it navigated away

    info2 = cdp(f"/info?target={tid}")
    url2 = info2.get("url", "")
    print(f"  URL after msg click: {url2[:70]}", flush=True)

    time.sleep(5)

    # For new contacts, Instagram shows a compose dialog requiring 聊天/Chat confirmation.
    # For existing threads it skips straight to the DM input — click Chat if present.
    chat_result = eval_js(tid, r"""
(function() {
  var btns = Array.from(document.querySelectorAll("[role=button], button"));
  var btn = btns.find(b => {
    var t = b.innerText.trim();
    return (t === "聊天" || t === "Chat" || t === "Next" || t === "下一步") &&
           b.getAttribute("aria-disabled") !== "true";
  });
  if (btn) { btn.click(); return JSON.stringify({ok: true, text: btn.innerText.trim()}); }
  return JSON.stringify({ok: false, btns: btns.map(b => b.innerText.trim()).filter(t => t).slice(0, 15)});
})()
""")
    try:
        chatr = json.loads(chat_result) if chat_result else {}
    except Exception:
        chatr = {}
    print(f"  chat btn: {chatr}", flush=True)

    # Wait for DM thread to load
    time.sleep(10)

    # Find DM message input — broader search, no strict placeholder filter
    def find_msg_input():
        return eval_js(tid, r"""
(function() {
  var els = Array.from(document.querySelectorAll("[contenteditable=true], [role=textbox]"));
  var inp = els.find(e => (e.getAttribute("aria-placeholder") || e.placeholder || "").length > 0);
  if (!inp && els.length > 0) inp = els[els.length - 1];
  if (inp) return "found:" + (inp.getAttribute("aria-placeholder") || inp.placeholder || "no-ph");
  return "not found:" + els.length;
})()
""")

    inp_check = find_msg_input()
    print(f"  input check: {inp_check}", flush=True)

    if "not found" in inp_check:
        debug_info = eval_js(tid, r"""
JSON.stringify({url: document.location.href, ce: Array.from(document.querySelectorAll("[contenteditable]")).map(e => e.getAttribute("aria-placeholder") || e.getAttribute("contenteditable") || "").slice(0, 5), tb: Array.from(document.querySelectorAll("[role=textbox]")).map(e => e.getAttribute("aria-placeholder") || "").slice(0, 5)})
""")
        print(f"  debug: {debug_info}", flush=True)
        close_tab(tid)
        return False

    # Focus message input
    eval_js(tid, r"""
(function() {
  var els = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"));
  var el = els.find(e => (e.getAttribute("aria-placeholder") || e.placeholder || "").length > 0);
  if (!el && els.length > 0) el = els[els.length - 1];
  if (el) { el.focus(); el.click(); }
})()
""")
    time.sleep(1.5)

    tr = type_text(tid, message)
    print(f"  type: {tr}", flush=True)
    time.sleep(1)

    def get_input_len():
        r = eval_js(tid, r"""
(function() {
  var els = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"));
  var el = els.find(e => (e.getAttribute("aria-placeholder") || e.placeholder || "").length > 0);
  if (!el && els.length > 0) el = els[els.length - 1];
  return el ? String(el.innerText.trim().length) : "0";
})()
""")
        try:
            return int(r or "0")
        except Exception:
            return 0

    typed_len = get_input_len()
    print(f"  input len: {typed_len}", flush=True)

    if typed_len < 10:
        print(f"  ↻ 重试...", flush=True)
        eval_js(tid, r"""
(function() {
  var els = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"));
  var el = els.find(e => (e.getAttribute("aria-placeholder") || e.placeholder || "").length > 0);
  if (!el && els.length > 0) el = els[els.length - 1];
  if (el) { el.focus(); el.click(); }
})()
""")
        time.sleep(2)
        type_text(tid, message)
        time.sleep(1)
        typed_len = get_input_len()
        print(f"  input len after retry: {typed_len}", flush=True)

    if typed_len < 10:
        print(f"  ✗ 输入失败", flush=True)
        close_tab(tid)
        return False

    time.sleep(1)

    send_result = eval_js(tid, r"""
(function() {
  var btns = Array.from(document.querySelectorAll("[role=button],button"));
  var sendBtn = btns.find(b => {
    var label = b.getAttribute("aria-label") || "";
    return label === "发送" || label === "Send";
  });
  if (!sendBtn) {
    sendBtn = btns.find(b => {
      var chars = Array.from((b.getAttribute("aria-label") || "")).map(c => c.codePointAt(0).toString(16));
      return chars.length === 2 && chars[0] === "53d1" && chars[1] === "9001";
    });
  }
  if (!sendBtn) return JSON.stringify({ok: false, reason: "send btn not found"});
  sendBtn.click();
  return JSON.stringify({ok: true});
})()
""")
    try:
        sr = json.loads(send_result) if send_result else {}
    except Exception:
        sr = {}
    if not sr.get("ok"):
        print(f"  ✗ 发送按钮未找到: {sr}", flush=True)
        close_tab(tid)
        return False

    time.sleep(2)
    verify = eval_js(tid, r"""
(function() {
  var els = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"));
  var el = els.find(e => (e.getAttribute("aria-placeholder") || e.placeholder || "").length > 0);
  if (!el && els.length > 0) el = els[els.length - 1];
  return JSON.stringify({inputEmpty: el ? el.innerText.trim().length <= 1 : true});
})()
""")
    try:
        vr = json.loads(verify) if verify else {}
    except Exception:
        vr = {}
    sent = vr.get("inputEmpty", False)
    print(f"  verify: {vr}", flush=True)
    close_tab(tid)
    return sent


def mark_sent(username: str, message: str):
    data = json.load(open(IG_PIPELINE, encoding="utf-8"))
    for p in data:
        if p.get("username") == username:
            p["status"] = "messaged"
            p["touch_count"] = p.get("touch_count", 0) + 1
            p["dm_sent_date"] = TODAY
            p["dm_message_preview"] = message[:120]
            break
    with open(IG_PIPELINE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  → pipeline 已更新: @{username}", flush=True)


def main():
    data = json.load(open(IG_PIPELINE, encoding="utf-8"))
    prospects = {p["username"]: p for p in data}
    queue = [u for u in TARGET_USERNAMES
             if u in prospects
             and prospects[u].get("status") == "prospect"
             and prospects[u].get("warmup_done")]

    print(f"=== IG DM v39 | {len(queue)} USA pending accounts | {TODAY} ===\n", flush=True)

    if not queue:
        print("无待发账号")
        for u in TARGET_USERNAMES:
            if u in prospects:
                p = prospects[u]
                print(f"  @{u}: status={p.get('status')} warmup={p.get('warmup_done')}")
        return

    sent = 0
    for i, username in enumerate(queue, 1):
        msg = MESSAGES.get(username, DEFAULT_MSG)
        p = prospects[username]
        print(f"[{i}/{len(queue)}] @{username} | {p.get('company_en', '')}", flush=True)
        print(f"  消息 ({len(msg.split())} 词): {msg[:80]}...", flush=True)
        ok = send_dm(username, msg)
        if ok:
            mark_sent(username, msg)
            sent += 1
            print(f"  ✓ SENT\n", flush=True)
        else:
            print(f"  ✗ FAILED\n", flush=True)
        if i < len(queue):
            wait = random.randint(300, 480)
            print(f"  waiting {wait}s ({wait//60}min)...\n", flush=True)
            time.sleep(wait)

    print(f"=== Done: {sent}/{len(queue)} DMs sent ===")


if __name__ == "__main__":
    main()
