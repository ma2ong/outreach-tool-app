"""
IG DM v58 - verified USA LED display targets only.
Follows first, sends latest case image, then sends casual DM text.
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
PIPELINE = BASE / "pipeline/instagram/prospects.json"
TODAY = datetime.date.today().isoformat()
IMAGE_PATH = r"C:\Users\Administrator\Desktop\Recent-led-projects-poster-4k.jpg"

TARGETS = [
    {
        "no": 775,
        "username": "hvallinsolutions",
        "company_en": "HV ALL IN SOLUTIONS",
        "city": "Miami, FL",
        "message": (
            "Hi! I'm from Shenzhen, China. I saw your LED screen installation, repair and rental work in Miami. "
            "Sharing a recent Korea LED installation reference. For Miami projects, do clients ask more for indoor fine-pitch walls or outdoor high-brightness screens?"
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


def set_files(tid, timeout=20):
    body = json.dumps({"selector": 'input[type="file"][multiple]', "files": [IMAGE_PATH]})
    return cdp(f"/setFiles?target={tid}", body=body, timeout=timeout)


def open_tab(url):
    return cdp(f"/new?url={url}", timeout=35).get("targetId", "")


def close_tab(tid):
    cdp(f"/close?target={tid}")


def load_pipeline():
    return json.load(open(PIPELINE, encoding="utf-8"))


def save_pipeline(data):
    json.dump(data, open(PIPELINE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def already_sent(target):
    return any(
        (row.get("no") == target["no"] or str(row.get("username", "")).lower() == target["username"])
        and row.get("status") == "messaged"
        and row.get("image_sent") is True
        for row in load_pipeline()
    )


def mark_result(target, text_sent, image_sent, followed, reason=""):
    data = load_pipeline()
    payload = {
        "no": target["no"],
        "country": "USA",
        "platform": "instagram",
        "username": target["username"],
        "company_en": target["company_en"],
        "city": target["city"],
        "target_fit": "verified_led_display",
        "do_not_contact": False,
        "followed": followed,
        "image_sent": image_sent,
        "attachment": IMAGE_PATH,
    }
    if text_sent:
        payload.update({
            "status": "messaged",
            "touch_count": 1,
            "message_sent_date": TODAY,
            "message_channel": "instagram",
            "message_text": target["message"],
        })
    else:
        payload.update({"status": "prospect", "last_attempt_date": TODAY, "last_attempt_result": reason})
    if image_sent:
        payload["image_sent_date"] = TODAY
    else:
        payload["image_last_attempt_date"] = TODAY
        payload["image_last_attempt_result"] = reason or "image_not_sent"
    for row in data:
        if row.get("no") == target["no"] or str(row.get("username", "")).lower() == target["username"]:
            row.update(payload)
            break
    else:
        data.append(payload)
    save_pipeline(data)


def click_by_text(tid, labels):
    labels_json = json.dumps(labels)
    return eval_js(tid, f"""
(function(){{
  const labels={labels_json}.map(x=>String(x).toLowerCase());
  const buttons=Array.from(document.querySelectorAll("[role=button],button,a"));
  const b=buttons.find(x=>labels.includes((x.innerText||x.getAttribute("aria-label")||"").trim().toLowerCase()));
  if(b){{b.click(); return JSON.stringify({{ok:true,text:(b.innerText||b.getAttribute("aria-label")||"").trim()}});}}
  return JSON.stringify({{ok:false}});
}})()
""")


def try_follow(tid):
    result = click_by_text(tid, ["Follow", "关注"])
    try:
        return bool(json.loads(result or "{}").get("ok"))
    except Exception:
        return False


def send_image(tid):
    upload = set_files(tid)
    print(f"  setFiles multiple: {upload}", flush=True)
    if not upload.get("success"):
        return False
    time.sleep(5)
    preview = eval_js(tid, r"""
(function(){
  const remove = Array.from(document.querySelectorAll('[aria-label]')).some(x => {
    const a=(x.getAttribute('aria-label')||'').toLowerCase();
    return a.includes('remove attachment') || a.includes('移除附件');
  });
  const blobs = document.querySelectorAll('img[src^="blob:"]').length;
  return JSON.stringify({remove, blobs});
})()
""")
    print(f"  preview: {preview}", flush=True)
    sent = eval_js(tid, r"""
(function(){
  const buttons=Array.from(document.querySelectorAll("[role=button],button"));
  const b=buttons.find(x=>{
    const t=(x.getAttribute("aria-label")||x.innerText||"").trim();
    return t==="Send" || t==="发送";
  });
  if(b){b.click(); return JSON.stringify({ok:true});}
  return JSON.stringify({ok:false});
})()
""", timeout=20)
    try:
        return bool(json.loads(sent or "{}").get("ok"))
    except Exception:
        return False


def send_text(tid, text):
    eval_js(tid, r"""
(function(){
  const boxes=Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"));
  const box=boxes.find(e=>e.offsetParent!==null)||boxes[boxes.length-1];
  if(box){box.focus();box.click();}
})()
""")
    time.sleep(0.5)
    type_text(tid, text)
    time.sleep(1)
    typed = eval_js(tid, r"""
(function(){
  const boxes=Array.from(document.querySelectorAll("[contenteditable=true],[role=textbox]"));
  const box=boxes.find(e=>e.offsetParent!==null)||boxes[boxes.length-1];
  return box ? String(box.innerText.trim().length) : "0";
})()
""")
    print(f"  input len: {typed}", flush=True)
    if int(typed or "0") < 10:
        return False
    sent = eval_js(tid, r"""
(function(){
  const buttons=Array.from(document.querySelectorAll("[role=button],button"));
  const b=buttons.find(x=>{
    const t=(x.getAttribute("aria-label")||x.innerText||"").trim();
    return t==="Send" || t==="发送";
  });
  if(b){b.click(); return JSON.stringify({ok:true});}
  return JSON.stringify({ok:false});
})()
""")
    try:
        return bool(json.loads(sent or "{}").get("ok"))
    except Exception:
        return False


def send_dm(target):
    tid = open_tab(f"https://www.instagram.com/{target['username']}/")
    if not tid:
        return False, False, False, "open_tab_failed"
    try:
        time.sleep(10)
        url = cdp(f"/info?target={tid}").get("url", "")
        print(f"  url: {url[:90]}", flush=True)
        if f"/{target['username']}" not in url.lower():
            return False, False, False, "profile_url_mismatch"
        followed = try_follow(tid)
        print(f"  followed: {followed}", flush=True)
        time.sleep(2)
        msg_click = click_by_text(tid, ["Message", "发消息", "消息"])
        print(f"  message button: {msg_click}", flush=True)
        try:
            if not json.loads(msg_click or "{}").get("ok"):
                return followed, False, False, "message_button_not_found"
        except Exception:
            return followed, False, False, "message_button_not_found"
        time.sleep(8)
        image_sent = send_image(tid)
        time.sleep(3)
        text_sent = send_text(tid, target["message"])
        return followed, image_sent, text_sent, "sent" if text_sent else "text_not_sent"
    finally:
        close_tab(tid)


def main():
    print(f"=== IG DM v58 | {len(TARGETS)} targets | {TODAY} ===", flush=True)
    sent = 0
    for target in TARGETS:
        print(f"\n@{target['username']} | no:{target['no']} | {target['company_en']}", flush=True)
        if already_sent(target):
            print("  SKIP: already sent with image", flush=True)
            continue
        followed, image_sent, text_sent, reason = send_dm(target)
        mark_result(target, text_sent, image_sent, followed, reason)
        if text_sent:
            sent += 1
            print(f"  SENT | followed={followed} | image={image_sent}", flush=True)
        else:
            print(f"  FAILED | followed={followed} | image={image_sent} | reason={reason}", flush=True)
    print(f"\n=== Done: {sent}/{len(TARGETS)} IG DMs sent ===", flush=True)


if __name__ == "__main__":
    main()
