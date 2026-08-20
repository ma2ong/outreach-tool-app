import datetime
import json
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

TODAY = datetime.date.today().isoformat()
CDP = "http://localhost:3456"
BASE = Path(__file__).parent
PIPELINE = BASE / "pipeline/whatsapp/prospects.json"
IMAGE_PATH = r"C:\Users\Administrator\Desktop\Recent-led-projects-poster-4k.jpg"

TARGETS = [
    {"no": 792, "company_en": "Easy Audio Rental", "phone": "+1 913 219 7475", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Kansas City LED video wall rental work and wanted to share a recent Korea LED installation reference. For KC events, do clients ask more for turn-key 12ft LED walls or larger custom video walls?"},
    {"no": 793, "company_en": "Full Swing Productions", "phone": "+1 316 641 8913", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your high-resolution LED panels, video walls and custom LED installation work. Sharing a recent Korea LED installation reference. Are your projects mostly rental walls or fixed LED installs?"},
    {"no": 794, "company_en": "Queen City Screens", "phone": "+1 513 275 8550", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Queen City Screens' LED screen trailers and video wall work in Cincinnati. Sharing a recent Korea LED installation reference. Are your events mostly outdoor mobile screens or modular LED video walls?"},
    {"no": 795, "company_en": "Livestream Media Network", "phone": "+1 210 993 9500", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your LED video wall rental and livestream production work in San Antonio. Sharing a recent Korea LED installation reference. For live events, do you use more 3.9mm rental walls or finer indoor LED walls?"},
    {"no": 796, "company_en": "OVOMEDIA Audio / Video Services", "phone": "+1 813 545 3312", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your 1.9 pixel LED video wall rental work in Florida. Sharing a recent Korea LED installation reference. Do your clients usually ask for fine-pitch indoor walls or larger outdoor screens?"},
    {"no": 797, "company_en": "One Way Event Productions", "phone": "+1 914 770 7786", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your NYC LED video wall and LED rental work. Sharing a recent Korea LED installation reference. For corporate events, what pixel pitch or cabinet size do clients request most?"},
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


def open_tab(url):
    return cdp(f"/new?url={urllib.parse.quote(url, safe='')}", timeout=35).get("targetId", "")


def close_tab(tid):
    cdp(f"/close?target={tid}")


def clean_phone(phone):
    return "".join(c for c in phone if c.isdigit())


def load_pipeline():
    return json.load(open(PIPELINE, encoding="utf-8"))


def save_pipeline(data):
    json.dump(data, open(PIPELINE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def already_sent(no):
    return any(row.get("no") == no and row.get("status") == "messaged" for row in load_pipeline())


def mark_result(target, text_sent, image_sent=False, reason=""):
    data = load_pipeline()
    payload = {
        "no": target["no"],
        "country": "USA",
        "company_en": target["company_en"],
        "phone": target["phone"],
        "platform": "whatsapp",
        "username": target["phone"],
        "target_fit": "verified_led_display",
        "whatsapp_verified": target.get("verified", False),
        "do_not_contact": False,
    }
    if text_sent:
        payload.update({
            "status": "messaged",
            "touch_count": 1,
            "message_sent_date": TODAY,
            "message_channel": "whatsapp",
            "message_text": target["message"],
            "image_sent": image_sent,
            "attachment": IMAGE_PATH,
            "last_attempt_result": None,
            "last_attempt_date": None,
        })
        if image_sent:
            payload["image_sent_date"] = TODAY
    else:
        payload.update({"status": "prospect", "last_attempt_date": TODAY, "last_attempt_result": reason})
    for row in data:
        if row.get("no") == target["no"]:
            row.update(payload)
            break
    else:
        data.append(payload)
    save_pipeline(data)


def click_send(tid):
    result = eval_js(tid, r"""
(function(){
  const s=document.querySelector('span[data-icon="wds-ic-send-filled"]')||document.querySelector('span[data-icon="send"]');
  if(!s)return JSON.stringify({ok:false});
  let el=s;
  for(let i=0;i<8;i++){
    if(el.tagName==='BUTTON'||el.getAttribute('role')==='button'){el.click();return JSON.stringify({ok:true});}
    if(!el.parentElement)break;
    el=el.parentElement;
  }
  s.click();
  return JSON.stringify({ok:true});
})()
""")
    try:
        return bool(json.loads(result or "{}").get("ok"))
    except Exception:
        return False


def send_image(tid):
    eval_js(tid, r"""
(function(){
  const els=Array.from(document.querySelectorAll('[role=button],button,span,[aria-label]'));
  const b=els.find(x=>{
    const a=(x.getAttribute('aria-label')||'').toLowerCase();
    const d=(x.getAttribute('data-icon')||'').toLowerCase();
    return a.includes('attach') || d.includes('attach') || d.includes('clip');
  });
  if(b)b.click();
})()
""")
    time.sleep(2)
    body = json.dumps({"selector": 'input[type="file"]', "files": [IMAGE_PATH]})
    upload = cdp(f"/setFiles?target={tid}", body=body, timeout=20)
    print(f"  image setFiles: {upload}", flush=True)
    if not upload.get("success"):
        return False
    time.sleep(4)
    return click_send(tid)


def send_target(target):
    query = urllib.parse.urlencode({"phone": clean_phone(target["phone"]), "text": target["message"]})
    tid = open_tab(f"https://web.whatsapp.com/send?{query}")
    if not tid:
        return False, False, "open_tab_failed"
    try:
        time.sleep(10)
        current = cdp(f"/info?target={tid}").get("url", "")
        print(f"  url: {current[:100]}", flush=True)
        text_sent = False
        for _ in range(70):
            if click_send(tid):
                text_sent = True
                break
            time.sleep(0.2)
        image_sent = False
        if text_sent:
            time.sleep(2)
            image_sent = send_image(tid)
        return text_sent, image_sent, "sent" if text_sent else "text_not_sent"
    finally:
        close_tab(tid)


def main():
    print(f"=== WA Sender v25 | {len(TARGETS)} USA LED targets | {TODAY} ===", flush=True)
    sent = 0
    for target in TARGETS:
        print(f"\nno:{target['no']} {target['company_en']} -> {target['phone']}", flush=True)
        if already_sent(target["no"]):
            print("  SKIP: already sent", flush=True)
            continue
        text_sent, image_sent, reason = send_target(target)
        mark_result(target, text_sent, image_sent, reason)
        if text_sent:
            sent += 1
            print(f"  SENT | image={image_sent}", flush=True)
        else:
            print(f"  FAILED | reason={reason}", flush=True)
    print(f"\n=== Done: {sent}/{len(TARGETS)} WA sent ===", flush=True)


if __name__ == "__main__":
    main()
