"""
IG DM v40 — v39 warmup-done batch (4 accounts) + v40 batch (8 accounts after warmup)
CMG Visuals LED, Boston Audio Rentals, New Image Event Productions, A.V. Rental Services,
Insane Impact, Rocket Productions USA, Meyer Pro Inc, Limitless Lights and Sound,
Illuminated Mobile, C West Entertainment, Sifi Entertainment, Master Sound Pro
"""
import json, sys, time, random, datetime, subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CDP = "http://localhost:3456"
BASE = Path(__file__).parent
IG_PIPELINE = BASE / "pipeline/instagram/prospects.json"
TODAY = datetime.date.today().isoformat()

TARGET_USERNAMES = [
    # v39 warmup-done, pending DM
    "cmgvisualsled",
    "bostonaudiorentals",
    "nie_nyc",
    "philly_audio_visual",
    # v40 batch (run after ig_warmup_v40.py)
    "insaneimpact",
    "rocketprousa",
    "meyerproinc",
    "limitlesslightsandsound",
    "illuminatedmobile",
    "cwestent",
    "sifientertainment",
    "mastersoundpro",
    # dpcevents — warmup done, was missing from original list
    "dpcevents",
]

MESSAGES = {
    "cmgvisualsled": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV production companies in Dallas. "
        "Your LED video wall work looks great. "
        "We supply P2–P5 indoor and outdoor LED panels at factory-direct pricing with full tech support. "
        "If you're looking to expand your LED inventory, happy to share specs and pricing."
    ),
    "bostonaudiorentals": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV rental companies in Boston. "
        "Your event production and AV rental services look solid. "
        "We supply P2–P5 indoor and outdoor LED panels at factory-direct pricing. "
        "If you're sourcing LED panels for events, happy to connect."
    ),
    "nie_nyc": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for event production companies in New York. "
        "Your event production portfolio in NYC looks impressive. "
        "We supply P1.5–P5 indoor fine-pitch and outdoor LED panels at factory-direct pricing. "
        "If you're specifying LED video walls for upcoming events, happy to share specs."
    ),
    "philly_audio_visual": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV rental companies in Philadelphia. "
        "Your AV rental services look great. "
        "We supply P2–P5 indoor and outdoor LED panels at factory-direct pricing with full tech support. "
        "If you're looking to add LED to your inventory, happy to connect."
    ),
    "insaneimpact": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV production companies across the US. "
        "Your LED screen rental network across Nashville, Atlanta, and multiple cities is impressive. "
        "We supply P2–P5 indoor and outdoor LED panels at factory-direct pricing. "
        "If you're expanding your LED fleet, happy to share specs and pricing."
    ),
    "rocketprousa": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV production companies in Atlanta. "
        "Your live event production and LED wall work in the Southeast looks great — Atlanta United and concert production are big markets. "
        "We supply P2–P5 indoor and outdoor LED panels at factory-direct pricing. "
        "If you're sourcing LED panels, happy to connect."
    ),
    "meyerproinc": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV production companies in Portland and Seattle. "
        "Your LED video wall production for corporate and nonprofit events in the Pacific Northwest looks great. "
        "We supply P2–P5 indoor and outdoor LED panels at factory-direct pricing. "
        "If you're adding to your LED inventory, happy to share specs."
    ),
    "limitlesslightsandsound": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for event production companies in Houston. "
        "Your video wall and full-service AV production across Houston and San Antonio looks impressive. "
        "We supply P2–P5 indoor and outdoor LED panels at factory-direct pricing. "
        "If you're looking to expand your LED wall inventory, happy to connect."
    ),
    "illuminatedmobile": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for mobile LED companies in Chicago. "
        "Your mobile LED billboard trucks and trailer rental operation is a great business model. "
        "We supply outdoor P4–P8 LED modules and full panels for mobile displays at factory-direct pricing. "
        "If you're upgrading or expanding your fleet, happy to share specs."
    ),
    "cwestent": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV production companies in Phoenix. "
        "Your LED video wall rental and full-service AV production for events in Arizona looks great. "
        "We supply P2–P5 indoor and outdoor LED panels at factory-direct pricing. "
        "If you're looking to expand your LED inventory, happy to connect."
    ),
    "sifientertainment": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV and event companies in Atlanta. "
        "Your LED screen rental and AV services for corporate events and weddings look great. "
        "We supply P1.8–P3.9 indoor fine-pitch LED panels at factory-direct pricing. "
        "If you're sourcing LED screens, happy to share specs and pricing."
    ),
    "mastersoundpro": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV production companies in South Florida. "
        "Your LED video wall and full-service event production in Miami and Fort Lauderdale looks great. "
        "We supply P2–P5 indoor and outdoor LED panels at factory-direct pricing. "
        "If you're sourcing LED panels, happy to connect."
    ),
    "dpcevents": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV production companies in San Antonio. "
        "Your LED video wall rental and corporate AV event production in San Antonio looks impressive. "
        "We supply P2–P5 indoor and outdoor LED panels at factory-direct pricing with full tech support. "
        "If you're looking to expand your LED video wall inventory, happy to share specs and pricing."
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


def clickAt(tid, selector, timeout=15):
    args = ["curl", "-s", "--max-time", str(timeout), "-X", "POST",
            f"{CDP}/clickAt?target={tid}", "--data-binary", selector.encode("utf-8")]
    r = subprocess.run(args, capture_output=True, timeout=timeout + 5)
    try:
        return json.loads(r.stdout.decode("utf-8", "replace"))
    except Exception:
        return {}


def typekeys(tid, text, timeout=120):
    args = ["curl", "-s", "--max-time", str(timeout), "-X", "POST",
            f"{CDP}/typekeys?target={tid}", "--data-binary", text.encode("utf-8")]
    r = subprocess.run(args, capture_output=True, timeout=timeout + 5)
    try:
        return json.loads(r.stdout.decode("utf-8", "replace"))
    except Exception:
        return {}


def open_tab(url):
    return cdp(f"/new?url={url}", timeout=35).get("targetId", "")


def close_tab(tid):
    cdp(f"/close?target={tid}")


def send_dm(username: str, message: str) -> bool:
    print(f"  → 打开 IG 主页", flush=True)
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
    url = info.get("url", "")
    print(f"  URL: {url[:70]}", flush=True)

    page_err = eval_js(tid, "document.body.innerText.includes('无法访问此页面') || document.body.innerText.includes('not available')")
    if page_err == "true":
        print(f"  ✗ 账号不存在或已删除", flush=True)
        close_tab(tid)
        return False

    msg_result = eval_js(tid, r"""
(function() {
  var all = Array.from(document.querySelectorAll("[role=button], button"));
  var btn = all.find(b => {
    var t = (b.innerText || "").trim();
    return t === "发消息" || t === "消息" || t === "Message";
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
        close_tab(tid)
        return False

    time.sleep(10)
    cdp(f"/activate?target={tid}")

    info2 = cdp(f"/info?target={tid}")
    url2 = info2.get("url", "")
    print(f"  URL after msg click: {url2[:70]}", flush=True)

    time.sleep(5)

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

    time.sleep(10)

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

    # CDP /clickAt dispatches real mouse events — sets native browser focus for Input.insertText
    click_r = clickAt(tid, '[contenteditable][aria-placeholder="发消息"],[contenteditable][aria-placeholder="Message"],[contenteditable=true]')
    print(f"  clickAt: {click_r}", flush=True)
    time.sleep(1.5)

    tr = type_text(tid, message)
    print(f"  type: {tr}", flush=True)
    time.sleep(2)

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
        clickAt(tid, '[contenteditable][aria-placeholder="发消息"],[contenteditable][aria-placeholder="Message"],[contenteditable=true]')
        time.sleep(2)
        type_text(tid, message)
        time.sleep(2)
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
            p["message_sent_date"] = TODAY
            p["dm_message_preview"] = message[:120]
            break
    with open(IG_PIPELINE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  → pipeline 已更新: @{username}", flush=True)


def mark_excluded(username: str, reason: str):
    data = json.load(open(IG_PIPELINE, encoding="utf-8"))
    for p in data:
        if p.get("username") == username:
            p["status"] = "excluded"
            p["exclude_reason"] = reason
            break
    with open(IG_PIPELINE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    data = json.load(open(IG_PIPELINE, encoding="utf-8"))
    prospects = {p["username"]: p for p in data}
    queue = [u for u in TARGET_USERNAMES
             if u in prospects
             and prospects[u].get("status") == "prospect"
             and prospects[u].get("warmup_done")]

    print(f"=== IG DM v40 | {len(queue)} accounts | {TODAY} ===\n", flush=True)

    if not queue:
        print("无待发账号 (status=prospect AND warmup_done=True)")
        for u in TARGET_USERNAMES:
            if u in prospects:
                p = prospects[u]
                print(f"  @{u}: status={p.get('status')} warmup={p.get('warmup_done')}")
        return

    sent = 0
    for i, username in enumerate(queue, 1):
        msg = MESSAGES.get(username, DEFAULT_MSG)
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
            wait = random.randint(60, 120)
            print(f"  waiting {wait}s...\n", flush=True)
            time.sleep(wait)

    print(f"=== Done: {sent}/{len(queue)} DMs sent ===")


if __name__ == "__main__":
    main()
