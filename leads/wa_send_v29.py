"""
WhatsApp sender v29 - verified USA LED display / mobile LED truck targets.
Sends the recent project image with the outreach text as the image caption.
"""
import json
import subprocess
import time
import urllib.parse

import wa_send_v27 as base


base.TARGETS = [
    {"no": 824, "company_en": "MVS Media Group", "phone": "+1 877 728 9631", "verified": False, "country": "USA", "contact_name": "Alex", "contact_note_prefix": "2",
     "message": "Hi Alex! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw MVS Media Group's mobile LED billboard truck work across the US. Sharing a recent Korea LED display reference. For LED truck fleets, do you usually care more about outdoor brightness, easier maintenance, or panel weight?"},
    {"no": 825, "company_en": "LEDTRUCK.COM", "phone": "+1 213 814 3138", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your LED truck advertising work in New York and Los Angeles. Sharing a recent Korea LED display reference. For mobile LED billboard trucks, do you usually upgrade by module/panel replacement or full screen replacement?"},
    {"no": 826, "company_en": "Mobile LED Trucks", "phone": "+1 437 979 4769", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your mobile LED billboard truck and LED media van campaigns across major US markets. Sharing a recent Korea LED display reference. What pixel pitch and brightness are most useful for your truck screens?"},
    {"no": 827, "company_en": "Advanced Mobile LED", "phone": "+1 786 580 8624", "verified": False, "country": "USA", "contact_name": "Allen Simkovitch", "contact_note_prefix": "2",
     "message": "Hi Allen! I'm Allen too, from an LED display manufacturing factory in Shenzhen, China. I saw Advanced Mobile LED's custom-built mobile digital billboard fleet. Sharing a recent Korea LED display reference. For your truck displays, is serviceability or outdoor brightness the bigger priority?"},
    {"no": 828, "company_en": "Unlimited Mobile LED", "phone": "+1 786 389 1438", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Unlimited Mobile LED's Miami digital LED billboard trucks and live broadcasting capability. Sharing a recent Korea LED display reference. Do your clients ask more for outdoor brightness or live-video input support?"},
    {"no": 829, "company_en": "DMS LED Trucks", "phone": "+1 516 912 8940", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw DMS LED Trucks uses full-color LED screen technology on mobile advertising vehicles. Sharing a recent Korea LED display reference. Are your current needs more truck screen upgrades or new mobile LED display builds?"},
    {"no": 830, "company_en": "Lux Media", "phone": "+1 469 389 0046", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Lux Media's high-resolution mobile LED billboard trucks serving all 50 states. Sharing a recent Korea LED display reference. For Dallas and nationwide campaigns, do clients care more about screen brightness or fast maintenance?"},
    {"no": 831, "company_en": "Nomadic Genius", "phone": "+1 615 336 6678", "verified": False, "country": "USA", "contact_name": "Regis", "contact_note_prefix": "2",
     "message": "Hi Regis! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Nomadic Genius works with LED mobile billboards and LED billboard truck sales. Sharing a recent Korea LED display reference. For your mobile billboard jobs, what LED screen size or pitch do clients request most?"},
    {"no": 832, "company_en": "American Guerrilla Marketing", "phone": "+1 917 444 1065", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your LED billboard truck service and WhatsApp contact option for LED truck inquiries. Sharing a recent Korea LED display reference. For LED mobile billboard activations, do you usually need high-brightness outdoor panels or lighter truck screen modules?"},
]


def type_text(tid, text, timeout=35):
    args = [
        "curl", "-s", "--max-time", str(timeout), "-X", "POST",
        f"{base.CDP}/type?target={tid}", "--data-binary", text.encode("utf-8"),
    ]
    r = subprocess.run(args, capture_output=True, timeout=timeout + 5)
    try:
        return json.loads(r.stdout.decode("utf-8", "replace"))
    except Exception:
        return {}


def focus_caption_box(tid):
    return base.eval_js(tid, r"""
(function(){
  const boxes=Array.from(document.querySelectorAll('[contenteditable=true],[role=textbox]'))
    .filter(x=>x.offsetParent!==null);
  const box=boxes[boxes.length-1];
  if(!box)return JSON.stringify({ok:false,count:boxes.length});
  box.focus();
  box.click();
  return JSON.stringify({ok:true,count:boxes.length,text:box.innerText||''});
})()
""")


def wait_for_chat(tid):
    for _ in range(80):
        ready = base.eval_js(tid, r"""
(function(){
  const body=document.body ? document.body.innerText : '';
  const invalid=/phone number shared via url is invalid|phone number shared via url is not valid|isn't on whatsapp|not on whatsapp|not registered on whatsapp|没有注册 WhatsApp|电话号码.+没有注册/i.test(body);
  const boxes=Array.from(document.querySelectorAll('[contenteditable=true],[role=textbox]'));
  const hasComposer=boxes.some(x=>{
    const label=(x.getAttribute('aria-label')||'').toLowerCase();
    return label.includes('type a message') || label.includes('message') || label.includes('输入消息');
  });
  const hasAttach=Array.from(document.querySelectorAll('[role=button],button,span,[aria-label]')).some(x=>{
    const a=(x.getAttribute('aria-label')||'').toLowerCase();
    const d=(x.getAttribute('data-icon')||'').toLowerCase();
    return a.includes('attach') || a.includes('附件') || d.includes('attach') || d.includes('clip') || d.includes('plus');
  });
  return JSON.stringify({invalid, boxes: boxes.length, hasComposer, hasAttach, body: body.slice(0, 220)});
})()
""")
        try:
            data = json.loads(ready or "{}")
            if data.get("invalid"):
                return False, "invalid_or_not_whatsapp"
            if data.get("hasComposer") or data.get("hasAttach"):
                return True, "ready"
        except Exception:
            pass
        time.sleep(0.5)
    return False, "chat_not_ready"


def click_attach(tid):
    result = base.eval_js(tid, r"""
(function(){
  const els=Array.from(document.querySelectorAll('[role=button],button,span,[aria-label]'));
  const b=els.find(x=>{
    const a=(x.getAttribute('aria-label')||'').toLowerCase();
    const d=(x.getAttribute('data-icon')||'').toLowerCase();
    return a.includes('attach') || d.includes('attach') || d.includes('clip') || d.includes('plus');
  });
  if(b){b.click(); return JSON.stringify({ok:true,label:b.getAttribute('aria-label')||b.getAttribute('data-icon')||''});}
  return JSON.stringify({ok:false});
})()
""")
    try:
        return bool(json.loads(result or "{}").get("ok"))
    except Exception:
        return False


def upload_image(tid):
    if not click_attach(tid):
        return False, "attach_button_missing"
    time.sleep(1.5)
    body = json.dumps({"selector": 'input[type="file"]', "files": [base.IMAGE_PATH]})
    upload = base.cdp(f"/setFiles?target={tid}", body=body, timeout=25)
    print(f"  image setFiles: {upload}", flush=True)
    if not upload.get("success"):
        return False, "setfiles_failed"
    for _ in range(30):
        preview = base.eval_js(tid, r"""
(function(){
  const blobs=document.querySelectorAll('img[src^="blob:"]').length;
  const hasCaption=Array.from(document.querySelectorAll('[contenteditable=true],[role=textbox]')).some(x=>x.offsetParent!==null);
  return JSON.stringify({blobs, hasCaption});
})()
""")
        try:
            data = json.loads(preview or "{}")
            if int(data.get("blobs") or 0) > 0 or data.get("hasCaption"):
                return True, "preview_ready"
        except Exception:
            pass
        time.sleep(0.5)
    return False, "preview_missing"


def send_image_with_caption(tid, text):
    uploaded, reason = upload_image(tid)
    if not uploaded:
        return False, reason
    focus = focus_caption_box(tid)
    print(f"  caption focus: {focus}", flush=True)
    type_text(tid, text)
    time.sleep(1)
    length = base.eval_js(tid, r"""
(function(){
  const boxes=Array.from(document.querySelectorAll('[contenteditable=true],[role=textbox]')).filter(x=>x.offsetParent!==null);
  const box=boxes[boxes.length-1];
  return box ? String((box.innerText||'').trim().length) : '0';
})()
""")
    print(f"  caption len: {length}", flush=True)
    if int(length or "0") < 20:
        return False, "caption_not_inserted"
    return (True, "sent") if base.click_send(tid) else (False, "send_button_missing")


def send_target(target):
    phone = base.clean_phone(target["phone"])
    tid = base.open_tab(f"https://web.whatsapp.com/send?phone={phone}")
    if not tid:
        return False, False, "open_tab_failed"
    try:
        time.sleep(8)
        current = base.cdp(f"/info?target={tid}").get("url", "")
        print(f"  url: {current[:100]}", flush=True)
        ready, reason = wait_for_chat(tid)
        if not ready:
            return False, False, reason
        ok, reason = send_image_with_caption(tid, target["message"])
        return ok, ok, reason
    finally:
        base.close_tab(tid)


base.send_target = send_target

if __name__ == "__main__":
    base.main()
