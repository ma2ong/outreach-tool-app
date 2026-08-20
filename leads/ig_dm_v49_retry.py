"""
IG DM v49 retry — @soflostudio only (focus fix: JS focus before type, no 1.5s sleep)
"""
import json, sys, time, random, datetime, subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CDP = "http://localhost:3456"
BASE = Path(__file__).parent
IG_PIPELINE = BASE / "pipeline/instagram/prospects.json"
TODAY = datetime.date.today().isoformat()

TARGET_USERNAMES = ["soflostudio", "vegaseventgroup"]

MESSAGES = {
    "soflostudio": (
        "Hi, I'd like to share some recent LED display projects we delivered in Korea — "
        "P1.86 fine-pitch indoor walls, P2.5 commercial installs, and P3.91/P10 outdoor screens. "
        "Your LED screen rental and production work across South Florida looks great. "
        "If you have any upcoming projects, feel free to contact me — happy to provide specs and pricing."
    ),
    "vegaseventgroup": (
        "Hi, I'd like to share some recent LED display projects we delivered in Korea — "
        "P1.86 indoor LED walls, P2.5 commercial screens, and P3.91/P10 outdoor displays. "
        "Your award-winning LED video wall rentals in San Antonio look impressive. "
        "If you have any upcoming projects, happy to recommend suitable products and provide competitive pricing."
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


def js_focus_and_type(tid, message):
    """JS force-focus → immediate type (0.3s window, no focus stealing)"""
    eval_js(tid, r"""
(function() {
  var el = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"))
            .find(e => (e.getAttribute("aria-placeholder") || "").length > 0);
  if (el) { el.focus(); el.click(); }
})()
""")
    time.sleep(0.3)
    return type_text(tid, message)


def get_input_len(tid):
    r = eval_js(tid, r"""
(function() {
  var els = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"));
  var el = els.find(e => (e.getAttribute("aria-placeholder") || "").length > 0);
  if (!el && els.length > 0) el = els[els.length - 1];
  return el ? String(el.innerText.trim().length) : "0";
})()
""")
    try:
        return int(r or "0")
    except Exception:
        return 0


def send_dm(username: str, message: str) -> bool:
    tid = open_tab("https://www.instagram.com/")
    if not tid:
        print("  ✗ 无法创建 tab", flush=True)
        return False
    time.sleep(3)

    cdp(f"/navigate?target={tid}&url=https://www.instagram.com/{username}/", timeout=35)
    cdp(f"/activate?target={tid}")
    time.sleep(12)

    info = cdp(f"/info?target={tid}")
    print(f"  URL: {info.get('url','')[:70]}", flush=True)

    msg_result = eval_js(tid, r"""
(function() {
  var all = Array.from(document.querySelectorAll("[role=button], button"));
  var btn = all.find(b => {
    var t = (b.innerText || "").trim();
    return t === "发消息" || t === "消息" || t === "Message";
  });
  if (btn) { btn.click(); return JSON.stringify({ok: true, text: btn.innerText.trim()}); }
  return JSON.stringify({ok: false});
})()
""")
    try:
        mr = json.loads(msg_result) if msg_result else {}
    except Exception:
        mr = {}
    print(f"  msg btn: {mr}", flush=True)
    if not mr.get("ok"):
        close_tab(tid)
        return False

    time.sleep(10)
    cdp(f"/activate?target={tid}")
    time.sleep(5)

    inp_check = eval_js(tid, r"""
(function() {
  var els = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"));
  var inp = els.find(e => (e.getAttribute("aria-placeholder") || "").length > 0);
  if (inp) return "found:" + inp.getAttribute("aria-placeholder");
  return "not found:" + els.length;
})()
""")
    print(f"  input check: {inp_check}", flush=True)
    if "not found" in inp_check:
        close_tab(tid)
        return False

    # KEY FIX: JS focus → type within 0.3s (no 1.5s sleep)
    tr = js_focus_and_type(tid, message)
    print(f"  type: {tr}", flush=True)
    time.sleep(1)

    typed_len = get_input_len(tid)
    print(f"  input len: {typed_len}", flush=True)

    if typed_len < 10:
        print(f"  ↻ retry...", flush=True)
        tr2 = js_focus_and_type(tid, message)
        print(f"  type retry: {tr2}", flush=True)
        time.sleep(1)
        typed_len = get_input_len(tid)
        print(f"  input len after retry: {typed_len}", flush=True)

    if typed_len < 10:
        print(f"  ✗ 输入失败", flush=True)
        close_tab(tid)
        return False

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
    print(f"  send btn: {sr}", flush=True)
    if not sr.get("ok"):
        close_tab(tid)
        return False

    time.sleep(2)
    verify = eval_js(tid, r"""
(function() {
  var els = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"));
  var el = els.find(e => (e.getAttribute("aria-placeholder") || "").length > 0);
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
        if p.get("username") == username or p.get("instagram") == username:
            p["status"] = "messaged"
            p["touch_count"] = p.get("touch_count", 0) + 1
            p["dm_sent_date"] = TODAY
            p["message_sent_date"] = TODAY
            p["dm_message_preview"] = message[:120]
            break
    with open(IG_PIPELINE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  → pipeline updated: @{username}", flush=True)


def main():
    data = json.load(open(IG_PIPELINE, encoding="utf-8"))
    prospects = {(p.get("username") or p.get("instagram", "")): p for p in data}

    queue = [u for u in TARGET_USERNAMES
             if u in prospects and prospects[u].get("status") != "messaged"]

    print(f"=== IG DM v49 retry | {len(queue)} accounts | {TODAY} ===\n", flush=True)
    if not queue:
        print("All already messaged.")
        return

    sent = 0
    for i, username in enumerate(queue, 1):
        msg = MESSAGES.get(username, "")
        p = prospects[username]
        print(f"[{i}/{len(queue)}] @{username} | {p.get('company_en', '')} | {p.get('city', '')}", flush=True)
        ok = send_dm(username, msg)
        if ok:
            mark_sent(username, msg)
            sent += 1
            print(f"  ✓ SENT\n", flush=True)
        else:
            print(f"  ✗ FAILED\n", flush=True)

    print(f"=== Done: {sent}/{len(queue)} DMs sent ===")


if __name__ == "__main__":
    main()
