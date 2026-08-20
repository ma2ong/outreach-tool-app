"""
IG DM Sender v29 - USA batch (nos 562-567)
Sends personalized English DM via CDP after warmup
"""
import json, sys, time, random, datetime, subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CDP = "http://localhost:3456"
BASE = Path(__file__).parent
IG_PIPELINE = BASE / "pipeline/instagram/prospects.json"
TODAY = datetime.date.today().isoformat()

TARGET_USERNAMES = [
    "ariatechnologyrentals",
    "rentforeventus",
    "led_rentals_la",
    "rentexavrentals",
    "bigbangmn",
    "4wall",
]

# Personalized messages keyed by username
MESSAGES = {
    "ariatechnologyrentals": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV rental companies. "
        "Your multi-city rental footprint caught my attention. "
        "If you're sourcing LED tiles or video wall panels, we'd love to discuss specs and pricing. "
        "Do you have any upcoming deployments we could support?"
    ),
    "rentforeventus": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for event rental companies in the US. "
        "Saw your LED screen rental services across multiple cities. "
        "We supply P2.5–P4 outdoor and indoor LED panels to rental houses. "
        "Happy to share pricing — are you looking to expand your LED inventory?"
    ),
    "led_rentals_la": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we make LED video wall panels for rental companies in Southern California. "
        "Your setup looks sharp. "
        "We offer competitive pricing on P2–P3 indoor and P4–P5 outdoor LED panels with fast shipping to LA. "
        "Would love to connect if you're evaluating new panel sources."
    ),
    "rentexavrentals": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED tiles and video wall panels for the AV rental industry. "
        "Noticed your cross-rental focus and multi-warehouse setup. "
        "We work with production companies needing consistent inventory across locations. "
        "Are you adding any LED tile stock this year?"
    ),
    "bigbangmn": (
        "Hi Brandon, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED video wall panels for rental companies. "
        "Your nationwide LED rental service is impressive. "
        "We supply modular indoor/outdoor LED panels with flexible MOQ. "
        "If you're looking to grow your LED inventory, happy to share a quote."
    ),
    "4wall": (
        "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED video wall panels for production and rental companies. "
        "Your multi-city operation and event portfolio are impressive. "
        "We supply LED tiles to US AV companies — P1.9 to P5, indoor and outdoor. "
        "Would you be open to a quick spec comparison?"
    ),
}

DEFAULT_MSG = (
    "Hi, I'm Allen from Shenzhen Maxcolor Visual — we manufacture LED display panels for AV rental companies in the US. "
    "We supply P2–P5 indoor and outdoor LED panels. "
    "If you're looking to expand your LED inventory or source panels at competitive prices, happy to connect."
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


def type_text(tid, text, timeout=30):
    """Use CDP-level Input.insertText via /type endpoint (bypasses execCommand deprecation)"""
    args = ["curl", "-s", "--max-time", str(timeout), "-X", "POST",
            f"{CDP}/type?target={tid}", "--data-binary", text.encode("utf-8")]
    r = subprocess.run(args, capture_output=True, timeout=timeout + 5)
    try:
        return json.loads(r.stdout.decode("utf-8", "replace"))
    except Exception:
        return {}


def eval_js(tid, js, timeout=12):
    return cdp(f"/eval?target={tid}", js, timeout=timeout).get("value", "")


def open_tab(url):
    return cdp(f"/new?url={url}").get("targetId", "")


def close_tab(tid):
    cdp(f"/close?target={tid}")


def send_dm(username: str, message: str) -> bool:
    url = f"https://www.instagram.com/{username}/"
    msg_js = json.dumps(message)

    print(f"  → 打开主页: @{username}", flush=True)
    tid = open_tab(url)
    if not tid:
        print("  ✗ 无法创建 tab", flush=True)
        return False

    time.sleep(6)

    info = cdp(f"/info?target={tid}")
    if "instagram.com" not in info.get("url", ""):
        print(f"  ✗ 页面未加载", flush=True)
        close_tab(tid)
        return False

    # Click 发消息 / Message button
    click_result = eval_js(tid, r"""
(function() {
  var btns = Array.from(document.querySelectorAll("[role=button]"));
  var btn = btns.find(b => {
    var t = b.innerText.trim();
    return t === "发消息" || t === "Message";
  });
  if (!btn) return JSON.stringify({ok: false, reason: "Message button not found", count: btns.length});
  btn.click();
  return JSON.stringify({ok: true});
})()
""")
    try:
        cr = json.loads(click_result) if click_result else {}
    except Exception:
        cr = {}

    if not cr.get("ok"):
        print(f"  ✗ 发消息按钮未找到: {cr}", flush=True)
        close_tab(tid)
        return False

    time.sleep(4)

    # Find DM input
    input_check = eval_js(tid, r"""
(function() {
  var els = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"));
  var inp = els.find(e => (e.getAttribute("aria-placeholder") || e.placeholder || "").length > 0);
  return inp ? "found" : "not found";
})()
""")
    if input_check != "found":
        print(f"  ✗ 输入框未出现: {input_check}", flush=True)
        close_tab(tid)
        return False

    # Focus the DM input element
    eval_js(tid, r"""
(function() {
  var el = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]")).find(e => {
    return (e.getAttribute("aria-placeholder") || e.placeholder || "").length > 0;
  });
  if (el) { el.focus(); el.click(); }
})()
""")
    time.sleep(0.5)

    # Type via CDP Input.insertText (bypasses JS execCommand restrictions in Chrome 130+)
    tr = type_text(tid, message)
    print(f"  type: {tr}", flush=True)

    # Verify text was inserted
    check_len = eval_js(tid, r"""
(function() {
  var el = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]")).find(e => {
    return (e.getAttribute("aria-placeholder") || e.placeholder || "").length > 0;
  });
  return el ? String(el.innerText.trim().length) : "0";
})()
""")
    try:
        typed_len = int(check_len or "0")
    except Exception:
        typed_len = 0
    print(f"  input len after type: {typed_len}", flush=True)

    if typed_len < 10:
        print(f"  ✗ 输入失败: len={typed_len}", flush=True)
        close_tab(tid)
        return False

    time.sleep(1)

    # Click send
    send_result = eval_js(tid, r"""
(function() {
  var btns = Array.from(document.querySelectorAll("[role=button],button"));
  var sendBtn = btns.find(b => {
    var label = b.getAttribute("aria-label") || "";
    return label === "发送" || label === "Send";
  });
  if (!sendBtn) {
    // Try codepoint match
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

    # Verify sent
    verify = eval_js(tid, r"""
(function() {
  var el = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]")).find(e => {
    return (e.getAttribute("aria-placeholder") || e.placeholder || "").length > 0;
  });
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
    print(f"  → pipeline 已更新: @{username} status=messaged", flush=True)


def main():
    data = json.load(open(IG_PIPELINE, encoding="utf-8"))
    prospects = {p["username"]: p for p in data}

    queue = [u for u in TARGET_USERNAMES
             if u in prospects
             and prospects[u].get("status") == "prospect"
             and prospects[u].get("warmup_done")]

    print(f"=== IG DM v29 | {len(queue)} USA accounts | {TODAY} ===\n", flush=True)

    if not queue:
        print("无待发账号（warmup 未完成或已发送）")
        all_q = [u for u in TARGET_USERNAMES if u in prospects]
        for u in all_q:
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
            wait = random.randint(300, 480)  # 5-8 min between DMs
            print(f"  waiting {wait}s ({wait//60}min) before next...\n", flush=True)
            time.sleep(wait)

    print(f"=== Done: {sent}/{len(queue)} DMs sent ===")


if __name__ == "__main__":
    main()
