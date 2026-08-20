"""
WA sender v21 - verified USA LED display WhatsApp targets.
Text is casual DM format, not email format. Attempts to attach latest project poster.
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
IMAGE_PATH = r"C:\Users\Administrator\Desktop\Recent-led-projects-poster-4k.jpg"

TARGETS = [
    {
        "no": 769,
        "company_en": "XR Stages LA",
        "phone": "+1 818 641 0220",
        "url": "",
        "message": (
            "Hi! I'm from Shenzhen, China. I saw your XR LED stage and 30ft LED video wall work in LA. "
            "Sharing a recent Korea LED installation reference. For XR stages, do you usually need higher refresh indoor panels or flexible cabinet sizes?"
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


def mark_result(target, sent, image_sent=False, reason=""):
    data = load_pipeline()
    payload = {
        "no": target["no"],
        "country": "USA",
        "company_en": target["company_en"],
        "phone": target["phone"],
        "platform": "whatsapp",
        "username": target["phone"] or target["url"],
        "target_fit": "verified_led_display",
        "do_not_contact": False,
    }
    if sent:
        payload.update({
            "status": "messaged",
            "touch_count": 1,
            "message_sent_date": TODAY,
            "message_channel": "whatsapp",
            "message_text": target["message"],
            "image_sent": image_sent,
            "attachment": IMAGE_PATH,
        })
    else:
        payload.update({
            "status": "prospect",
            "last_attempt_date": TODAY,
            "last_attempt_result": reason,
        })
    for row in data:
        if row.get("no") == target["no"]:
            row.update(payload)
            break
    else:
        data.append(payload)
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
    eval_js(tid, r"""
(function(){
  const btns=Array.from(document.querySelectorAll('[role=button],button,span'));
  const b=btns.find(x=>{
    const a=(x.getAttribute('aria-label')||'').toLowerCase();
    const d=(x.getAttribute('data-icon')||'').toLowerCase();
    return a.includes('attach') || d.includes('attach') || d.includes('clip');
  });
  if(b)b.click();
})()
""")
    time.sleep(2)
    upload = set_files(tid, [IMAGE_PATH])
    print(f"  image setFiles: {upload}", flush=True)
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
  return JSON.stringify({ok:true});
})()
""")
    try:
        return bool(json.loads(sent or "{}").get("ok"))
    except Exception:
        return False


def send_target(target):
    if target["url"]:
        url = target["url"]
        if "wa.me/message/" not in url:
            url = f"{url}?text={urllib.parse.quote(target['message'])}"
    else:
        url = f"https://web.whatsapp.com/send?phone={clean_phone(target['phone'])}&text={urllib.parse.quote(target['message'])}"
    tid = open_tab(url)
    if not tid:
        return False, False, "open_tab_failed"
    try:
        time.sleep(10)
        current = cdp(f"/info?target={tid}").get("url", "")
        print(f"  url: {current[:90]}", flush=True)
        if "wa.me/message/" in url:
            # Click Continue to Chat if present, then rely on manual text field load.
            eval_js(tid, r"""
(function(){
  const links=Array.from(document.querySelectorAll('a,button,[role=button]'));
  const b=links.find(x=>(x.innerText||x.getAttribute('aria-label')||'').toLowerCase().includes('continue'));
  if(b)b.click();
})()
""")
            time.sleep(8)
        eval_js(tid, OBSERVER_JS)
        text_sent = False
        for _ in range(220):
            val = eval_js(tid, "window.__waSent || null")
            if val and val not in ("null", "already", ""):
                text_sent = True
                break
            time.sleep(0.1)
        image_sent = False
        if text_sent:
            image_sent = try_send_image(tid)
        return text_sent, image_sent, "sent" if text_sent else "text_not_sent"
    finally:
        close_tab(tid)


def main():
    print(f"=== WA Sender v21 | {len(TARGETS)} verified USA WA targets | {TODAY} ===", flush=True)
    sent = 0
    for target in TARGETS:
        print(f"\nno:{target['no']} {target['company_en']}", flush=True)
        if already_sent(target["no"]):
            print("  SKIP: already sent", flush=True)
            continue
        text_sent, image_sent, reason = send_target(target)
        if text_sent:
            mark_result(target, True, image_sent=image_sent)
            sent += 1
            print(f"  SENT | image={image_sent}", flush=True)
        else:
            mark_result(target, False, reason=reason)
            print(f"  FAILED | reason={reason}", flush=True)
    print(f"\n=== Done: {sent}/{len(TARGETS)} WA sent ===", flush=True)


if __name__ == "__main__":
    main()
