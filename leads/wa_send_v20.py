"""
WA sender v20 - verified USA LED target with confirmed WhatsApp link.
Target: SergeiSolutions (no:768), wa.me/18182773201 on website.
Sends casual WhatsApp text and attempts to attach Korea project image.
"""
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
IMAGE_PATH = r"C:\Users\Administrator\Desktop\korea-led-projects-poster-4k.jpg"

TARGETS = [
    {
        "no": 768,
        "company_en": "SergeiSolutions",
        "phone": "+1 818 277 3201",
        "website": "sergeisolutions.com",
        "city": "Los Angeles, CA",
        "message": (
            "Hi! I'm from Shenzhen, China. I saw your luxury LED video wall and outdoor LED screen installation work in Los Angeles. "
            "Sharing a few recent LED projects we delivered in Korea. For residential LED walls, do your clients usually prefer fine pitch indoor panels or higher-brightness outdoor panels?"
        ),
    }
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


def set_files(tid, files, timeout=20):
    body = json.dumps({"selector": 'input[type="file"]', "files": files})
    return cdp(f"/setFiles?target={tid}", body=body, timeout=timeout)


def open_tab(url):
    return cdp(f"/new?url={urllib.parse.quote(url, safe=':/?=&%')}", timeout=35).get("targetId", "")


def close_tab(tid):
    cdp(f"/close?target={tid}")


def clean_phone(phone):
    return "".join(c for c in phone if c.isdigit())


def load_pipeline():
    with open(PIPELINE, encoding="utf-8") as f:
        return json.load(f)


def save_pipeline(data):
    with open(PIPELINE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def already_sent(no):
    return any(row.get("no") == no and row.get("status") == "messaged" for row in load_pipeline())


def mark_sent(target, image_sent):
    data = load_pipeline()
    for row in data:
        if row.get("no") == target["no"]:
            row.update({
                "status": "messaged",
                "touch_count": max(int(row.get("touch_count") or 0), 1),
                "message_sent_date": TODAY,
                "message_channel": "whatsapp",
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
            "company_en": target["company_en"],
            "city": target["city"],
            "website": target["website"],
            "phone": target["phone"],
            "platform": "whatsapp",
            "username": target["phone"],
            "status": "messaged",
            "touch_count": 1,
            "message_sent_date": TODAY,
            "message_channel": "whatsapp",
            "message_text": target["message"],
            "image_sent": image_sent,
            "target_fit": "verified_led_display",
            "do_not_contact": False,
        })
    save_pipeline(data)


OBSERVER_JS = r"""
(function(){
  if(window.__waSent) return 'already';
  window.__waSent=null;
  function go(){
    var s=document.querySelector('span[data-icon="wds-ic-send-filled"]')||document.querySelector('span[data-icon="send"]');
    if(!s)return;
    var inp=document.querySelector('div[contenteditable]');
    if(!inp||inp.innerText.trim().length<10)return;
    var el=s;
    for(var i=0;i<8;i++){
      if(el.tagName==='BUTTON'||el.getAttribute('role')==='button'){el.click();window.__waSent=inp.innerText.slice(0,40);return;}
      if(!el.parentElement)break;
      el=el.parentElement;
    }
    s.click();window.__waSent=inp.innerText.slice(0,40);
  }
  go();
  new MutationObserver(go).observe(document.body,{childList:true,subtree:true});
  return 'ok';
})()
"""


def try_send_image(tid):
    click_attach = eval_js(tid, r"""
(function(){
  var labels=["Attach","附件","Attach file"];
  for (var l of labels) {
    var el=document.querySelector('[aria-label="'+l+'"]');
    if(el){el.click(); return JSON.stringify({ok:true,label:l});}
  }
  var btns=Array.from(document.querySelectorAll('[role=button],button,span'));
  var b=btns.find(x=>{
    var a=(x.getAttribute('aria-label')||'').toLowerCase();
    var d=(x.getAttribute('data-icon')||'').toLowerCase();
    return a.includes('attach') || d.includes('attach') || d.includes('clip');
  });
  if(b){b.click(); return JSON.stringify({ok:true,label:b.getAttribute('aria-label')||b.getAttribute('data-icon')});}
  return JSON.stringify({ok:false});
})()
""")
    print(f"  attach: {click_attach}", flush=True)
    time.sleep(2)
    upload = set_files(tid, [IMAGE_PATH])
    print(f"  setFiles: {upload}", flush=True)
    time.sleep(4)
    sent = eval_js(tid, r"""
(function(){
  var s=document.querySelector('span[data-icon="wds-ic-send-filled"]')||document.querySelector('span[data-icon="send"]');
  if(!s)return JSON.stringify({ok:false});
  var el=s;
  for(var i=0;i<8;i++){
    if(el.tagName==='BUTTON'||el.getAttribute('role')==='button'){el.click();return JSON.stringify({ok:true});}
    if(!el.parentElement)break;
    el=el.parentElement;
  }
  s.click();
  return JSON.stringify({ok:true,method:'icon'});
})()
""")
    print(f"  image send: {sent}", flush=True)
    try:
        return bool(json.loads(sent or "{}").get("ok"))
    except Exception:
        return False


def send_target(target):
    phone = clean_phone(target["phone"])
    url = f"https://web.whatsapp.com/send?phone={phone}&text={urllib.parse.quote(target['message'])}"
    tid = open_tab(url)
    if not tid:
        return False, False
    try:
        time.sleep(10)
        eval_js(tid, OBSERVER_JS)
        text_sent = False
        for _ in range(180):
            val = eval_js(tid, "window.__waSent || null")
            if val and val not in ("null", "already", ""):
                text_sent = True
                break
            time.sleep(0.1)
        image_sent = False
        if text_sent:
            time.sleep(3)
            image_sent = try_send_image(tid)
        return text_sent, image_sent
    finally:
        close_tab(tid)


def main():
    print(f"=== WA Sender v20 | {len(TARGETS)} verified USA WhatsApp target | {TODAY} ===", flush=True)
    sent = 0
    for target in TARGETS:
        print(f"\nno:{target['no']} {target['company_en']} -> {target['phone']}", flush=True)
        if already_sent(target["no"]):
            print("  SKIP: already sent", flush=True)
            continue
        text_sent, image_sent = send_target(target)
        if text_sent:
            mark_sent(target, image_sent)
            sent += 1
            print(f"  SENT | image={image_sent}", flush=True)
        else:
            print("  FAILED: text not sent", flush=True)
    print(f"\n=== Done: {sent}/{len(TARGETS)} WA sent ===", flush=True)


if __name__ == "__main__":
    main()
