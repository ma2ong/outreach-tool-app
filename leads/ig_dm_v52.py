"""
IG DM v52 — v51 batch IG accounts (no warmup, direct send)
@relevant_av (Relevant Audio + Visual, Wichita KS)
@documentsolutionsinc (Document Solutions Inc, Albuquerque NM)

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

TARGETS = [
    {"no": 724, "username": "relevant_av",          "company_en": "Relevant Audio + Visual",         "city": "Wichita, KS"},
    {"no": 729, "username": "documentsolutionsinc",  "company_en": "Document Solutions Inc (DSI NM)", "city": "Albuquerque, NM"},
]

MESSAGES = {
    "relevant_av": (
        "Hi! I'm from Shenzhen, China — we manufacture LED display panels for AV and rental companies. "
        "Saw your LED video wall work in Wichita and wanted to reach out. "
        "Sharing some recent projects we delivered in Korea — indoor fine-pitch walls and outdoor screens. "
        "We supply P0.7–P10 indoor and outdoor LED panels at factory-direct pricing. "
        "If you're ever looking to source or expand your LED inventory, feel free to message me!"
    ),
    "documentsolutionsinc": (
        "Hi! I'm from Shenzhen, China — we manufacture LED display panels and video walls. "
        "Noticed your LED video wall installations across New Mexico and wanted to connect. "
        "Sharing some recent projects we delivered in Korea — indoor fine-pitch walls and outdoor screens. "
        "We supply P0.7–P10 indoor and outdoor LED panels at factory-direct pricing. "
        "If you're looking for a reliable manufacturer for your next project, feel free to message me!"
    ),
}

DEFAULT_MSG = (
    "Hi! I'm from Shenzhen, China — we make LED display panels for AV and event companies. "
    "Sharing some recent projects we delivered in Korea — indoor fine-pitch walls and outdoor screens. "
    "We supply P0.7–P10 indoor and outdoor LED panels at factory-direct pricing. "
    "If you ever need to source LED panels, feel free to message me!"
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
    attach_result = eval_js(tid, r"""
(function() {
  var btns = Array.from(document.querySelectorAll("[role=button], button, svg"));
  var btn = btns.find(b => {
    var label = (b.getAttribute("aria-label") || "").toLowerCase();
    return label.includes("photo") || label.includes("image") || label.includes("media")
        || label.includes("照片") || label.includes("图片") || label.includes("文件");
  });
  if (!btn) {
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

    sf_result = set_files(tid, 'input[type="file"]', [IMAGE_PATH])
    print(f"  setFiles: {sf_result}", flush=True)
    time.sleep(3)

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

    send_result = eval_js(tid, r"""
(function() {
  var btns = Array.from(document.querySelectorAll("[role=button],button"));
  var sendBtn = btns.find(b => {
    var label = b.getAttribute("aria-label") || "";
    return label === "发送" || label === "Send";
  });
  if (sendBtn) { sendBtn.click(); return JSON.stringify({ok: true}); }
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

    clickAt(tid, '[contenteditable][aria-placeholder="发消息"],[contenteditable][aria-placeholder="Message"],[contenteditable=true]')

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


def mark_sent(username: str, no: int, message: str):
    data = json.load(open(IG_PIPELINE, encoding="utf-8"))
    for p in data:
        if p.get("username") == username or p.get("instagram") == username:
            p["status"] = "messaged"
            p["dm_sent_date"] = TODAY
            p["message_sent_date"] = TODAY
            p["dm_message_preview"] = message[:120]
            json.dump(data, open(IG_PIPELINE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            print(f"  → pipeline 已更新: @{username}", flush=True)
            return
    data.append({
        "no": no, "username": username, "instagram": username,
        "status": "messaged", "dm_sent_date": TODAY,
        "message_sent_date": TODAY, "dm_message_preview": message[:120]
    })
    json.dump(data, open(IG_PIPELINE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"  → pipeline 新增: @{username}", flush=True)


def main():
    print(f"=== IG DM v52 | {len(TARGETS)} accounts | {TODAY} ===\n", flush=True)

    sent = 0
    for i, t in enumerate(TARGETS, 1):
        username = t["username"]
        msg = MESSAGES.get(username, DEFAULT_MSG)
        print(f"[{i}/{len(TARGETS)}] @{username} | {t['company_en']} | {t['city']}", flush=True)
        print(f"  消息 ({len(msg.split())} 词): {msg[:80]}...", flush=True)
        ok = send_dm(username, msg)
        if ok:
            mark_sent(username, t["no"], msg)
            sent += 1
            print(f"  ✓ SENT\n", flush=True)
        else:
            print(f"  ✗ FAILED\n", flush=True)
        if i < len(TARGETS):
            wait = random.randint(60, 120)
            print(f"  waiting {wait}s...\n", flush=True)
            time.sleep(wait)

    print(f"=== Done: {sent}/{len(TARGETS)} DMs sent ===")


if __name__ == "__main__":
    main()
