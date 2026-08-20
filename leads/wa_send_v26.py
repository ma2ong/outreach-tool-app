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
    {"no": 798, "company_en": "LED Screen Rentals", "phone": "+1 833 403 0420", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your LED screen, LED display and LED wall rental work and wanted to share a recent Korea LED installation reference. Do clients usually ask more for mobile LED screens or modular indoor/outdoor LED walls?"},
    {"no": 799, "company_en": "Legion LED Trucks", "phone": "+1 866 792 9533", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Legion LED truck and mobile billboard trailer work and wanted to share a recent Korea LED installation reference. For LED trucks, what pixel pitch and cabinet serviceability do your buyers care about most?"},
    {"no": 800, "company_en": "FunFlicks Kentucky", "phone": "+1 859 869 9669", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Kentucky LED screen rental work for outdoor movies, live sports and community events. Sharing a recent Korea LED installation reference. Do clients usually ask for trailer LED screens or modular LED walls?"},
    {"no": 801, "company_en": "Royal AV Solutions", "phone": "+1 206 580 3040", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Seattle/Pacific Northwest event AV work and LED video wall rental references. Sharing a recent Korea LED installation reference. For corporate events, do clients request more fine-pitch indoor LED or larger rental walls?"},
    {"no": 802, "company_en": "Game Craze Party Rentals", "phone": "+1 330 752 2351", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Northeast Ohio LED video wall rental page with 14ft x 8ft LED walls. Sharing a recent Korea LED installation reference. Are your LED wall jobs mostly schools/churches or corporate events?"},
    {"no": 803, "company_en": "Freedom Fun USA Dayton", "phone": "+1 937 970 4386", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Dayton LED Screen & Video Wall Rentals page with 17ft x 10ft and 23ft x 13ft mobile LED screens. Sharing a recent Korea LED installation reference. Are your events mostly outdoor community screens or corporate brand activations?"},
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
    print(f"=== WA Sender v26 | {len(TARGETS)} USA LED targets | {TODAY} ===", flush=True)
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
