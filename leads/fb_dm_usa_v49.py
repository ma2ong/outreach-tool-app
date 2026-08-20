"""
FB DM USA v49 — sends Korea projects message to @AmericanLedDisplays (no=110)
via Facebook Messenger using CDP.
"""
import json, sys, time, random, datetime, subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CDP = "http://localhost:3456"
BASE = Path(__file__).parent
FB_PIPELINE = BASE / "pipeline/facebook/prospects.json"
TODAY = datetime.date.today().isoformat()

TARGETS = [
    {
        "no": 110,
        "company_en": "American LED Display Solutions",
        "facebook": "AmericanLedDisplays",
        "city": "USA",
        "msg": (
            "Hi, I'd like to share some recent LED display projects we delivered in Korea — "
            "P1.86 fine-pitch indoor walls, P2.5 commercial installs, and P3.91/P10 outdoor screens. "
            "If you have any upcoming LED projects, feel free to contact me anytime. "
            "We'd be happy to recommend suitable products and provide competitive pricing. "
            "Hope we can have a good opportunity to work together!"
        ),
    },
]


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


def send_fb_dm(fb_handle: str, message: str) -> bool:
    # Open Facebook page
    page_url = f"https://www.facebook.com/{fb_handle}"
    print(f"  → Opening FB page: {page_url}", flush=True)
    tid = open_tab(page_url)
    if not tid:
        print("  ✗ Could not create tab", flush=True)
        return False
    time.sleep(8)

    info = cdp(f"/info?target={tid}")
    url = info.get("url", "")
    print(f"  URL: {url[:70]}", flush=True)

    # Click "Send Message" button on FB page
    msg_result = eval_js(tid, r"""
(function() {
  var btns = Array.from(document.querySelectorAll("a,button,[role=button]"));
  var btn = btns.find(b => {
    var t = (b.innerText || b.getAttribute("aria-label") || "").trim().toLowerCase();
    return t.includes("send message") || t.includes("message");
  });
  if (btn) { btn.click(); return JSON.stringify({ok: true, text: btn.innerText.trim()}); }
  return JSON.stringify({ok: false, btns: btns.map(b => (b.innerText||"").trim()).filter(t=>t).slice(0,10)});
})()
""")
    try:
        mr = json.loads(msg_result) if msg_result else {}
    except Exception:
        mr = {}
    print(f"  send btn: {mr}", flush=True)

    if not mr.get("ok"):
        # Try Messenger direct URL as fallback
        print(f"  → Trying Messenger direct URL", flush=True)
        close_tab(tid)
        tid = open_tab(f"https://www.facebook.com/messages/t/{fb_handle}")
        time.sleep(8)

    time.sleep(5)
    cdp(f"/activate?target={tid}")
    time.sleep(3)

    # Find message input box
    inp_check = eval_js(tid, r"""
(function() {
  var els = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"));
  var inp = els.find(e => (e.getAttribute("aria-placeholder") || e.placeholder || "").length > 0);
  if (!inp && els.length > 0) inp = els[els.length - 1];
  if (inp) return "found:" + (inp.getAttribute("aria-placeholder") || "no-ph");
  return "not found:" + els.length;
})()
""")
    print(f"  input check: {inp_check}", flush=True)

    if "not found" in inp_check:
        print(f"  ✗ Message input not found", flush=True)
        close_tab(tid)
        return False

    # Focus and type
    eval_js(tid, r"""
(function() {
  var els = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"));
  var el = els.find(e => (e.getAttribute("aria-placeholder") || e.placeholder || "").length > 0);
  if (!el && els.length > 0) el = els[els.length - 1];
  if (el) { el.focus(); el.click(); }
})()
""")
    time.sleep(0.3)

    tr = type_text(tid, message)
    print(f"  type: {tr}", flush=True)
    time.sleep(1)

    # Check typed length
    typed_len_str = eval_js(tid, r"""
(function() {
  var els = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"));
  var el = els.find(e => (e.getAttribute("aria-placeholder") || e.placeholder || "").length > 0);
  if (!el && els.length > 0) el = els[els.length - 1];
  return el ? String(el.innerText.trim().length) : "0";
})()
""")
    typed_len = int(typed_len_str or "0")
    print(f"  input len: {typed_len}", flush=True)

    if typed_len < 10:
        eval_js(tid, r"""
(function() {
  var els = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"));
  var el = els.find(e => (e.getAttribute("aria-placeholder") || e.placeholder || "").length > 0);
  if (!el && els.length > 0) el = els[els.length - 1];
  if (el) { el.focus(); el.click(); }
})()
""")
        time.sleep(0.5)
        type_text(tid, message)
        time.sleep(1)
        typed_len_str = eval_js(tid, r"""
(function() {
  var els = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"));
  var el = els.find(e => (e.getAttribute("aria-placeholder") || e.placeholder || "").length > 0);
  if (!el && els.length > 0) el = els[els.length - 1];
  return el ? String(el.innerText.trim().length) : "0";
})()
""")
        typed_len = int(typed_len_str or "0")
        print(f"  input len (retry): {typed_len}", flush=True)

    if typed_len < 10:
        print(f"  ✗ Input failed", flush=True)
        close_tab(tid)
        return False

    # Send
    send_result = eval_js(tid, r"""
(function() {
  var btns = Array.from(document.querySelectorAll("[role=button],button"));
  var sb = btns.find(b => {
    var label = (b.getAttribute("aria-label") || b.innerText || "").trim().toLowerCase();
    return label === "send" || label === "发送" || label === "press enter to send";
  });
  if (!sb) return JSON.stringify({ok: false, reason: "send btn not found"});
  sb.click();
  return JSON.stringify({ok: true});
})()
""")
    try:
        sr = json.loads(send_result) if send_result else {}
    except Exception:
        sr = {}

    if not sr.get("ok"):
        # Try pressing Enter
        eval_js(tid, r"""
(function() {
  var els = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"));
  var el = els.find(e => (e.getAttribute("aria-placeholder") || "").length > 0);
  if (!el && els.length > 0) el = els[els.length - 1];
  if (el) {
    var ev = new KeyboardEvent("keydown", {key:"Enter",code:"Enter",keyCode:13,bubbles:true});
    el.dispatchEvent(ev);
  }
})()
""")
        print(f"  sent via Enter key", flush=True)
    else:
        print(f"  send btn: {sr}", flush=True)

    time.sleep(2)
    close_tab(tid)
    return True


def mark_sent(no: int, handle: str):
    data = json.load(open(FB_PIPELINE, encoding="utf-8"))
    for p in data:
        if p.get("no") == no:
            p["status"] = "messaged"
            p["touch_count"] = p.get("touch_count", 0) + 1
            p["message_sent_date"] = TODAY
            p["message_channel"] = "facebook"
            with open(FB_PIPELINE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  → pipeline updated: no={no} @{handle}", flush=True)
            return
    print(f"  ⚠ not in pipeline: no={no}", flush=True)


def main():
    print(f"=== FB DM USA v49 | {len(TARGETS)} targets | {TODAY} ===\n", flush=True)
    sent = 0
    for i, t in enumerate(TARGETS, 1):
        print(f"[{i}/{len(TARGETS)}] {t['company_en']} (@{t['facebook']})", flush=True)
        ok = send_fb_dm(t["facebook"], t["msg"])
        if ok:
            mark_sent(t["no"], t["facebook"])
            sent += 1
            print(f"  ✓ SENT\n", flush=True)
        else:
            print(f"  ✗ FAILED\n", flush=True)
        if i < len(TARGETS):
            wait = random.randint(60, 90)
            print(f"  waiting {wait}s...\n", flush=True)
            time.sleep(wait)
    print(f"=== Done: {sent}/{len(TARGETS)} FB DMs sent ===")


if __name__ == "__main__":
    main()
