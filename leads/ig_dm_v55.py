"""
IG DM v55 - USA batch (no warmup, direct send)
Sends Korea project image first when possible, then a casual DM without email-style signature.
"""
import datetime
import json
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CDP = "http://localhost:3456"
BASE = Path(__file__).parent
IG_PIPELINE = BASE / "pipeline/instagram/prospects.json"
TODAY = datetime.date.today().isoformat()
IMAGE_PATH = r"C:\Users\Administrator\Desktop\korea-led-projects-poster-4k.jpg"

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
        "no": 755,
        "username": "colossalproductionsevents",
        "company_en": "Colossal Productions",
        "city": "Knoxville, TN",
        "message": (
            "Hi! I'm from Shenzhen, China. I saw your LED wall and mobile LED trailer work in East Tennessee. "
            "Sharing a few recent LED projects we delivered in Korea. "
            "For watch parties and outdoor events, what screen size is requested most often?"
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


def cdp(path, body=None, timeout=15):
    args = ["curl", "-s", "--max-time", str(timeout)]
    if body is None:
        args.append(f"{CDP}{path}")
    else:
        args += ["-X", "POST", f"{CDP}{path}", "-d", body]
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


def set_files(tid, selector, files, timeout=20):
    body = json.dumps({"selector": selector, "files": files})
    return cdp(f"/setFiles?target={tid}", body=body, timeout=timeout)


def open_tab(url):
    return cdp(f"/new?url={url}", timeout=35).get("targetId", "")


def close_tab(tid):
    cdp(f"/close?target={tid}")


def mark_sent(target, image_sent, text):
    data = json.load(open(IG_PIPELINE, encoding="utf-8"))
    for row in data:
        if row.get("no") == target["no"] or str(row.get("username", "")).lower() == target["username"].lower():
            row.update({
                "status": "messaged",
                "touch_count": max(int(row.get("touch_count") or 0), 1),
                "message_sent_date": TODAY,
                "message_channel": "instagram",
                "message_text": text,
                "image_sent": image_sent,
                "username": target["username"],
            })
            break
    else:
        data.append({
            "no": target["no"],
            "country": "USA",
            "platform": "instagram",
            "username": target["username"],
            "company_en": target["company_en"],
            "city": target["city"],
            "status": "messaged",
            "touch_count": 1,
            "message_sent_date": TODAY,
            "message_channel": "instagram",
            "message_text": text,
            "image_sent": image_sent,
        })
    json.dump(data, open(IG_PIPELINE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def already_sent(target):
    data = json.load(open(IG_PIPELINE, encoding="utf-8"))
    return any(
        (row.get("no") == target["no"] or str(row.get("username", "")).lower() == target["username"].lower())
        and row.get("status") == "messaged"
        for row in data
    )


def try_send_image(tid):
    clicked = eval_js(tid, r"""
(function() {
  const labels = ["Photo", "Image", "Attach a photo or video", "照片", "图片", "文件"];
  for (const label of labels) {
    const el = document.querySelector(`[aria-label="${label}"]`);
    if (el) { el.click(); return JSON.stringify({ok:true,label}); }
  }
  const buttons = Array.from(document.querySelectorAll("[role=button],button"));
  const btn = buttons.find(b => {
    const label = (b.getAttribute("aria-label") || "").toLowerCase();
    return label.includes("photo") || label.includes("image") || label.includes("media");
  });
  if (btn) { btn.click(); return JSON.stringify({ok:true,label:btn.getAttribute("aria-label")}); }
  return JSON.stringify({ok:false});
})()
""")
    try:
        result = json.loads(clicked or "{}")
    except Exception:
        result = {}
    print(f"  image button: {result}", flush=True)
    if not result.get("ok"):
        return False

    time.sleep(2)
    upload = set_files(tid, 'input[type="file"]', [IMAGE_PATH])
    print(f"  setFiles: {upload}", flush=True)
    time.sleep(4)
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
        send_result = json.loads(sent or "{}")
    except Exception:
        send_result = {}
    print(f"  image send: {send_result}", flush=True)
    time.sleep(3)
    return bool(send_result.get("ok"))


def send_dm(target):
    tid = open_tab("https://www.instagram.com/")
    if not tid:
        print("  cannot open tab", flush=True)
        return False, False
    try:
        cdp(f"/navigate?target={tid}&url=https://www.instagram.com/{target['username']}/", timeout=35)
        cdp(f"/activate?target={tid}")
        time.sleep(12)

        msg_click = eval_js(tid, r"""
(function() {
  const buttons = Array.from(document.querySelectorAll("[role=button],button,a"));
  const btn = buttons.find(b => {
    const t = (b.innerText || b.getAttribute("aria-label") || "").trim();
    return t === "Message" || t === "发消息" || t === "消息";
  });
  if (btn) { btn.click(); return JSON.stringify({ok:true,text:(btn.innerText||btn.getAttribute("aria-label")||"").trim()}); }
  return JSON.stringify({ok:false,visible:buttons.map(b=>(b.innerText||b.getAttribute("aria-label")||"").trim()).filter(Boolean).slice(0,12)});
})()
""")
        try:
            msg_result = json.loads(msg_click or "{}")
        except Exception:
            msg_result = {}
        print(f"  message button: {msg_result}", flush=True)
        if not msg_result.get("ok"):
            return False, False

        time.sleep(8)
        eval_js(tid, r"""
(function() {
  const buttons = Array.from(document.querySelectorAll("[role=button],button"));
  const btn = buttons.find(b => {
    const t = (b.innerText || "").trim();
    return t === "Chat" || t === "聊天" || t === "Next" || t === "下一步";
  });
  if (btn) btn.click();
})()
""")
        time.sleep(5)

        image_sent = try_send_image(tid)

        eval_js(tid, r"""
(function() {
  const boxes = Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"));
  const box = boxes.find(e => e.offsetParent !== null) || boxes[boxes.length - 1];
  if (box) { box.focus(); box.click(); }
})()
""")
        time.sleep(0.4)
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
  const box = document.querySelector("[contenteditable=true],[role=textbox]");
  if (box) {
    box.dispatchEvent(new KeyboardEvent("keydown", {key:"Enter", code:"Enter", keyCode:13, bubbles:true}));
    return JSON.stringify({ok:true,method:"enter"});
  }
  return JSON.stringify({ok:false});
})()
""")
        try:
            send_result = json.loads(sent or "{}")
        except Exception:
            send_result = {}
        print(f"  text send: {send_result}", flush=True)
        time.sleep(3)
        return image_sent, bool(send_result.get("ok"))
    finally:
        close_tab(tid)


def main():
    print(f"=== IG DM v55 | {len(TARGETS)} USA targets | {TODAY} ===\n", flush=True)
    ok_count = 0
    for idx, target in enumerate(TARGETS, 1):
        print(f"[{idx}/{len(TARGETS)}] @{target['username']} | no:{target['no']} | {target['company_en']}", flush=True)
        if already_sent(target):
            print("  SKIP: already messaged", flush=True)
            continue
        image_sent, text_sent = send_dm(target)
        if text_sent:
            mark_sent(target, image_sent, target["message"])
            ok_count += 1
            print(f"  SENT | image={image_sent}\n", flush=True)
        else:
            print(f"  FAILED | image={image_sent}\n", flush=True)
        time.sleep(8)
    print(f"=== Done: {ok_count}/{len(TARGETS)} text DMs sent ===", flush=True)


if __name__ == "__main__":
    main()
