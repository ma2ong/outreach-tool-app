"""
IG DM v56 safe sender - verified USA LED targets only.

Safety rules:
- Opens the exact profile URL from the verified lead record.
- Does not use Instagram search/direct-new fallback.
- Before typing, checks the current page/thread still contains the target username.
- Sends Korea case image first when the media control is available.
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
        "no": 759,
        "username": "edenusa.la",
        "company_en": "Eden USA",
        "city": "Los Angeles, CA",
        "message": (
            "Hi! I'm from Shenzhen, China. I saw your LED video wall rental work in Los Angeles "
            "and wanted to share a few recent LED projects we delivered in Korea. "
            "For rental jobs, do you usually need more indoor fine-pitch panels or outdoor panels?"
        ),
    },
    {
        "no": 760,
        "username": "euroledwall",
        "company_en": "EuroLedwall USA",
        "city": "Los Angeles, CA",
        "message": (
            "Hi! I'm from Shenzhen, China. I saw your LED wall rental work for trade shows and events. "
            "Sharing a few recent LED projects we delivered in Korea. "
            "For your US projects, what pixel pitch is requested most often?"
        ),
    },
    {
        "no": 761,
        "username": "fidelisatx",
        "company_en": "Fidelis Sound & Lighting",
        "city": "Austin, TX",
        "message": (
            "Hi! I'm from Shenzhen, China. I saw your LED video wall rental work in Austin. "
            "Sharing a few recent LED projects we delivered in Korea. "
            "Do your event clients ask more for touring-style rental panels or fixed-looking LED walls?"
        ),
    },
    {
        "no": 762,
        "username": "1avamerica",
        "company_en": "AV America Florida",
        "city": "Florida",
        "message": (
            "Hi! I'm from Shenzhen, China. I saw your LED wall rental and AV production work in Florida. "
            "Sharing a few recent LED projects we delivered in Korea. "
            "For corporate events, what LED wall size do clients ask for most often?"
        ),
    },
    {
        "no": 763,
        "username": "digitalartvideo",
        "company_en": "Digital Art Video",
        "city": "New York, NY",
        "message": (
            "Hi! I'm from Shenzhen, China. I saw your LED wall rental and installation work for events in New York. "
            "Sharing a few recent LED projects we delivered in Korea. "
            "Are your LED projects mostly rental events or longer-term installations?"
        ),
    },
    {
        "no": 764,
        "username": "oneworldrental",
        "company_en": "One World Rental USA",
        "city": "USA nationwide",
        "message": (
            "Hi! I'm from Shenzhen, China. I saw your LED wall and LED screen rental services across the US. "
            "Sharing a few recent LED projects we delivered in Korea. "
            "For nationwide rentals, do you prefer lightweight panels or higher-brightness outdoor panels?"
        ),
    },
    {
        "no": 766,
        "username": "pixals360",
        "company_en": "Pixals LED Screen Rental Los Angeles",
        "city": "Los Angeles, CA",
        "message": (
            "Hi! I'm from Shenzhen, China. I saw your LED screen rental work for film, fashion and brand events. "
            "Sharing a few recent LED projects we delivered in Korea. "
            "For those creative installs, do clients ask more for fine pitch or flexible installation shapes?"
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


def set_files(tid, files, timeout=20):
    body = json.dumps({"selector": 'input[type="file"]', "files": files})
    return cdp(f"/setFiles?target={tid}", body=body, timeout=timeout)


def open_tab(url):
    return cdp(f"/new?url={url}", timeout=35).get("targetId", "")


def close_tab(tid):
    cdp(f"/close?target={tid}")


def load_pipeline():
    with open(IG_PIPELINE, encoding="utf-8") as f:
        return json.load(f)


def save_pipeline(data):
    with open(IG_PIPELINE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def already_sent(target):
    return any(
        (row.get("no") == target["no"] or str(row.get("username", "")).lower() == target["username"].lower())
        and row.get("status") == "messaged"
        for row in load_pipeline()
    )


def mark_sent(target, image_sent):
    data = load_pipeline()
    for row in data:
        if row.get("no") == target["no"] or str(row.get("username", "")).lower() == target["username"].lower():
            row.update({
                "country": "USA",
                "platform": "instagram",
                "username": target["username"],
                "company_en": target["company_en"],
                "city": target["city"],
                "status": "messaged",
                "touch_count": max(int(row.get("touch_count") or 0), 1),
                "message_sent_date": TODAY,
                "message_channel": "instagram",
                "message_text": target["message"],
                "image_sent": image_sent,
                "target_fit": "verified_led_display",
                "do_not_contact": False,
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
            "message_text": target["message"],
            "image_sent": image_sent,
            "target_fit": "verified_led_display",
            "do_not_contact": False,
        })
    save_pipeline(data)


def mark_failed(target, reason):
    data = load_pipeline()
    for row in data:
        if row.get("no") == target["no"] or str(row.get("username", "")).lower() == target["username"].lower():
            row.update({
                "country": "USA",
                "platform": "instagram",
                "username": target["username"],
                "company_en": target["company_en"],
                "city": target["city"],
                "status": "prospect",
                "target_fit": "verified_led_display",
                "last_attempt_date": TODAY,
                "last_attempt_result": reason,
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
            "status": "prospect",
            "target_fit": "verified_led_display",
            "last_attempt_date": TODAY,
            "last_attempt_result": reason,
        })
    save_pipeline(data)


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
    upload = set_files(tid, [IMAGE_PATH])
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
        return bool(json.loads(sent or "{}").get("ok"))
    except Exception:
        return False


def send_dm(target):
    profile_url = f"https://www.instagram.com/{target['username']}/"
    tid = open_tab(profile_url)
    if not tid:
        return False, False, "open_tab_failed"
    try:
        time.sleep(10)
        info = cdp(f"/info?target={tid}")
        url = info.get("url", "")
        print(f"  url: {url[:80]}", flush=True)
        if f"/{target['username'].lower()}" not in url.lower():
            return False, False, "profile_url_mismatch"

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
            click_result = json.loads(msg_click or "{}")
        except Exception:
            click_result = {}
        print(f"  message button: {click_result}", flush=True)
        if not click_result.get("ok"):
            return False, False, "message_button_not_found"

        time.sleep(8)
        image_sent = try_send_image(tid)

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
            return image_sent, False, "input_len_0"

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
            sent_result = json.loads(sent or "{}")
        except Exception:
            sent_result = {}
        print(f"  text send: {sent_result}", flush=True)
        return image_sent, bool(sent_result.get("ok")), "sent" if sent_result.get("ok") else "send_button_failed"
    finally:
        close_tab(tid)


def main():
    print(f"=== IG DM v56 safe | {len(TARGETS)} verified USA LED targets | {TODAY} ===\n", flush=True)
    sent = 0
    for idx, target in enumerate(TARGETS, 1):
        print(f"[{idx}/{len(TARGETS)}] @{target['username']} | no:{target['no']} | {target['company_en']}", flush=True)
        if already_sent(target):
            print("  SKIP: already sent\n", flush=True)
            continue
        image_sent, text_sent, reason = send_dm(target)
        if text_sent:
            mark_sent(target, image_sent)
            sent += 1
            print(f"  SENT | image={image_sent}\n", flush=True)
        else:
            mark_failed(target, reason)
            print(f"  FAILED | image={image_sent} | reason={reason}\n", flush=True)
        time.sleep(8)
    print(f"=== Done: {sent}/{len(TARGETS)} IG DMs sent ===", flush=True)


if __name__ == "__main__":
    main()
