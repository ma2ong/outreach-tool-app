"""
IG DM v50 — backlog USA batch (6 warmed-up accounts)
C&H Audio Visual Services (@chaudiovisual) - Louisville, KY
Triangle Media Solutions (@trianglemediasolutions) - Raleigh, NC
Hinckley Productions (@hinckleyproductions) - Madison, WI
NPi Audio Visual Solutions (@npiaudiovisualsolutions) - Cleveland, OH
Concept Pixels (@conceptpixels) - Nashville, TN
A1 Visuals (@a1_visuals_) - San Jose, CA

FORMAT: casual, no company name, "from Shenzhen China"; image sent first
"""
import json, sys, time, random, datetime, subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CDP = "http://localhost:3456"
BASE = Path(__file__).parent
IG_PIPELINE = BASE / "pipeline/instagram/prospects.json"
TODAY = datetime.date.today().isoformat()
IMAGE_PATH = r"C:\Users\Administrator\Desktop\korea-led-projects-poster-4k.jpg"

TARGET_USERNAMES = [
    "chaudiovisual",
    "trianglemediasolutions",
    "hinckleyproductions",
    "npiaudiovisualsolutions",
    "conceptpixels",
    "a1_visuals_",
]

MESSAGES = {
    "chaudiovisual": (
        "Hi! I'm from Shenzhen, China — we make LED display panels for AV companies. "
        "Saw your work in Louisville and thought I'd reach out. Sharing some recent projects "
        "we delivered in Korea — indoor fine-pitch walls and outdoor screens. "
        "If you ever need to source LED panels at factory pricing, feel free to message me!"
    ),
    "trianglemediasolutions": (
        "Hi! I'm from Shenzhen, China — we make LED display panels for media and event companies. "
        "Saw your work in Raleigh. Sharing some recent projects we delivered in Korea — "
        "indoor LED walls and outdoor displays. "
        "If you ever need to source LED panels, feel free to reach out!"
    ),
    "hinckleyproductions": (
        "Hi! I'm from Shenzhen, China — we make LED display panels for event production companies. "
        "Saw your work in Madison. Sharing some recent Korea projects — "
        "indoor LED walls and outdoor screens. "
        "If you ever need LED panels at factory pricing, feel free to message me!"
    ),
    "npiaudiovisualsolutions": (
        "Hi! I'm from Shenzhen, China — we make LED display panels for AV companies. "
        "Saw your solutions work in Cleveland. Sharing some recent Korea projects — "
        "indoor fine-pitch walls and outdoor displays. "
        "Feel free to reach out if you ever need LED panels!"
    ),
    "conceptpixels": (
        "Hi! I'm from Shenzhen, China — we make LED display panels for event and production companies. "
        "Love your work in Nashville. Sharing some recent Korea projects — "
        "indoor LED walls and outdoor billboard screens. "
        "If you ever need to source LED panels, feel free to message me!"
    ),
    "a1_visuals_": (
        "Hi! I'm from Shenzhen, China — we make LED display panels for visual production companies. "
        "Saw your work in San Jose. Sharing some recent Korea projects — "
        "indoor walls and outdoor displays. "
        "If you need LED panels at factory pricing, feel free to reach out!"
    ),
}

DEFAULT_MSG = (
    "Hi! I'm from Shenzhen, China — we make LED display panels for AV and event companies. "
    "Sharing some recent projects we delivered in Korea — indoor fine-pitch walls and outdoor screens. "
    "If you ever need to source LED panels at factory pricing, feel free to message me!"
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


def set_files(tid, selector, file_paths, timeout=20):
    body = json.dumps({"selector": selector, "files": file_paths})
    args = ["curl", "-s", "--max-time", str(timeout), "-X", "POST",
            f"{CDP}/setFiles?target={tid}", "-d", body]
    r = subprocess.run(args, capture_output=True, timeout=timeout + 5)
    try:
        return json.loads(r.stdout.decode("utf-8", "replace"))
    except Exception:
        return {}


def open_tab(url):
    return cdp(f"/new?url={url}", timeout=35).get("targetId", "")


def close_tab(tid):
    cdp(f"/close?target={tid}")


def try_send_image(tid) -> bool:
    """Click media/image button, set file via CDP setFiles, send. Returns True if sent."""
    # Click the media attach button (camera/image icon in DM compose)
    attach_result = eval_js(tid, r"""
(function() {
  var btns = Array.from(document.querySelectorAll("[role=button], button, svg"));
  // Try aria-label first
  var btn = btns.find(b => {
    var label = (b.getAttribute("aria-label") || "").toLowerCase();
    return label.includes("photo") || label.includes("image") || label.includes("media")
        || label.includes("照片") || label.includes("图片") || label.includes("文件");
  });
  if (!btn) {
    // Try parent SVG button
    var svgs = Array.from(document.querySelectorAll("svg"));
    for (var svg of svgs) {
      var p = svg.closest("[role=button]");
      if (p) {
        var label = (p.getAttribute("aria-label") || "").toLowerCase();
        if (label.includes("photo") || label.includes("image") || label.includes("media")
            || label.includes("照片") || label.includes("图片") || label.includes("文件")) {
          btn = p; break;
        }
      }
    }
  }
  if (btn) { btn.click(); return JSON.stringify({ok: true, label: btn.getAttribute("aria-label")}); }
  return JSON.stringify({ok: false});
})()
""")
    try:
        ar = json.loads(attach_result) if attach_result else {}
    except Exception:
        ar = {}
    print(f"  attach btn: {ar}", flush=True)

    if not ar.get("ok"):
        print(f"  ✗ 图片按钮未找到，跳过图片", flush=True)
        return False

    time.sleep(2)

    # Set file on the hidden input[type=file]
    sf_result = set_files(tid, 'input[type="file"]', [IMAGE_PATH])
    print(f"  setFiles: {sf_result}", flush=True)
    time.sleep(3)

    # Check if image preview appeared
    preview_check = eval_js(tid, r"""
(function() {
  var imgs = document.querySelectorAll("img[src*='blob:'], canvas, video");
  var fileInputs = document.querySelectorAll('input[type="file"]');
  return JSON.stringify({previews: imgs.length, fileInputs: fileInputs.length});
})()
""")
    try:
        pc = json.loads(preview_check) if preview_check else {}
    except Exception:
        pc = {}
    print(f"  preview check: {pc}", flush=True)

    time.sleep(1)

    # Send the image
    send_result = eval_js(tid, r"""
(function() {
  var btns = Array.from(document.querySelectorAll("[role=button],button"));
  var sendBtn = btns.find(b => {
    var label = b.getAttribute("aria-label") || "";
    return label === "发送" || label === "Send";
  });
  if (sendBtn) { sendBtn.click(); return JSON.stringify({ok: true}); }
  // Try Enter key fallback
  var inp = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"))
              .find(e => (e.getAttribute("aria-placeholder") || "").length > 0);
  if (inp) {
    inp.dispatchEvent(new KeyboardEvent("keydown", {key: "Enter", bubbles: true}));
    return JSON.stringify({ok: true, method: "enter"});
  }
  return JSON.stringify({ok: false, reason: "no send btn"});
})()
""")
    try:
        sr = json.loads(send_result) if send_result else {}
    except Exception:
        sr = {}
    print(f"  image send: {sr}", flush=True)

    time.sleep(3)
    return sr.get("ok", False)


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

    # Send image first
    print(f"  → 发送图片...", flush=True)
    img_ok = try_send_image(tid)
    print(f"  图片发送: {'✓' if img_ok else '✗ 跳过'}", flush=True)
    time.sleep(3)

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
        close_tab(tid)
        return False

    click_r = clickAt(tid, '[contenteditable][aria-placeholder="发消息"],[contenteditable][aria-placeholder="Message"],[contenteditable=true]')
    print(f"  clickAt: {click_r}", flush=True)

    eval_js(tid, """
(function() {
  var el = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"))
            .find(e => (e.getAttribute("aria-placeholder") || "").length > 0);
  if (el) { el.focus(); el.click(); }
})()
""")
    time.sleep(0.3)

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
        eval_js(tid, """
(function() {
  var el = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"))
            .find(e => (e.getAttribute("aria-placeholder") || "").length > 0);
  if (el) { el.focus(); el.click(); }
})()
""")
        time.sleep(0.3)
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

    print(f"=== IG DM v50 | {len(queue)} accounts | {TODAY} ===\n", flush=True)

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
