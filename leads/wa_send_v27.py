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
    {"no": 804, "company_en": "Mobile Stage USA", "phone": "+1 888 855 1641", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your nationwide LED video wall rental packages and wanted to share a recent Korea LED installation reference. For touring events, do clients usually ask more for modular LED walls or mobile LED display packages?"},
    {"no": 805, "company_en": "SRXTeK", "phone": "+1 847 275 3456", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your LED wall rental and virtual production work in Arlington Heights. Sharing a recent Korea LED installation reference. For your LED stages, do clients usually focus more on fine pixel pitch or camera refresh performance?"},
    {"no": 806, "company_en": "LED Exhibits", "phone": "+1 888 895 3372", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Orlando LED video wall exhibit rentals and sales. Sharing a recent Korea LED installation reference. For trade show LED walls, what sizes or pixel pitches do clients request most?"},
    {"no": 807, "company_en": "Grant's Tech", "phone": "+1 740 206 7245", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Central Ohio LED video wall rental, sales and installation page. Sharing a recent Korea LED installation reference. Are your LED wall projects mostly rentals or fixed installs?"},
    {"no": 808, "company_en": "Summit Prestige", "phone": "+1 301 707 5785", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your LED video wall rental package products and wanted to share a recent Korea LED installation reference. Are your customers usually buying ready packages or asking for custom LED wall sizes?"},
    {"no": 809, "company_en": "The Tekk Group Corporation", "phone": "+1 702 851 8351", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your USA video wall rental service and Las Vegas office. Sharing a recent Korea LED installation reference. For US rentals, do clients usually request indoor fine-pitch walls or larger event video walls?"},
    {"no": 810, "company_en": "Profigroup", "phone": "+1 253 349 7753", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Seattle LED screens, video walls and LED panel rental work. Sharing a recent Korea LED installation reference. For local events, do clients ask more for modular LED walls or TV/LED panel packages?"},
    {"no": 811, "company_en": "Big Wheel Digital Media", "phone": "+1 918 921 4818", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Big LED Screens page for LED video wall screen systems. Sharing a recent Korea LED installation reference. Are your LED screen projects mostly churches/casinos or rental/touring use?"},
    {"no": 812, "company_en": "Mobile Technology Graphics", "phone": "+1 877 392 4220", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your nationwide indoor/outdoor LED video wall rentals and mobile jumbotrons. Sharing a recent Korea LED installation reference. Do clients ask more for mobile jumbotrons or indoor curved LED walls?"},
    {"no": 813, "company_en": "HB Live", "phone": "+1 203 234 8107", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Connecticut LED wall rental page for meetings, festivals and live events. Sharing a recent Korea LED installation reference. Are your LED wall jobs mostly indoor corporate events or outdoor community/festival screens?"},
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


def build_contact_note(target):
    name = (target.get("contact_name") or target.get("name") or "").strip()
    company = (target.get("company_en") or "").strip()
    country = (target.get("country") or "USA").strip()
    country_cn = {
        "USA": "美国",
        "United States": "美国",
        "Mexico": "墨西哥",
        "Brazil": "巴西",
        "Colombia": "哥伦比亚",
        "Peru": "秘鲁",
        "Argentina": "阿根廷",
        "Chile": "智利",
    }.get(country, country)
    country_cn = {
        "USA": "\u7f8e\u56fd",
        "United States": "\u7f8e\u56fd",
        "Mexico": "\u58a8\u897f\u54e5",
        "Brazil": "\u5df4\u897f",
        "Colombia": "\u54e5\u4f26\u6bd4\u4e9a",
        "Peru": "\u79d8\u9c81",
        "Argentina": "\u963f\u6839\u5ef7",
        "Chile": "\u667a\u5229",
    }.get(country, country)
    text = " ".join(str(target.get(key, "")) for key in ("business", "message", "company_en")).lower()
    rental_words = (
        "rental", "rentals", "rent ", "event", "events", "av rental", "stage",
        "mobile billboard", "led truck", "truck", "trailer", "jumbotron",
        "production", "touring", "video wall rental", "renta", "alquiler",
        "arriendo", "locacion", "locación", "locacao", "locação",
        "eventos", "producciones", "produtora", "audiovisual",
    )
    fixed_words = (
        "installation", "install", "fixed", "sales", "integration", "integrator",
        "repair", "service", "display systems", "signage", "exhibit",
        "venta", "instalacion", "instalación", "venda", "instalação",
        "technology", "solutions", "soluciones", "digital signage",
    )
    prefix = target.get("contact_note_prefix") or target.get("wa_note_prefix")
    if not prefix:
        if any(word in text for word in rental_words):
            prefix = "2"
        elif any(word in text for word in fixed_words):
            prefix = "1"
        else:
            prefix = "1"
    return f"{prefix}_{country_cn}_{company}_{name}" if name else f"{prefix}_{country_cn}_{company}"


def mark_result(target, text_sent, image_sent=False, reason=""):
    data = load_pipeline()
    contact_note = build_contact_note(target)
    payload = {
        "no": target["no"],
        "country": target.get("country", "USA"),
        "company_en": target["company_en"],
        "phone": target["phone"],
        "platform": "whatsapp",
        "username": target["phone"],
        "target_fit": "verified_led_display",
        "whatsapp_verified": target.get("verified", False),
        "do_not_contact": False,
        "contact_note": contact_note,
        "whatsapp_contact_note": contact_note,
        "contact_note_format": "1_国家_公司名_名字 / 2_国家_公司名_名字",
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
            "contact_note_status": "recorded",
        })
        if image_sent:
            payload["image_sent_date"] = TODAY
    else:
        payload.update({
            "status": "prospect",
            "last_attempt_date": TODAY,
            "last_attempt_result": reason,
            "contact_note_status": "not_sent_not_applied",
        })
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
    print(f"=== WA Sender v27 | {len(TARGETS)} USA LED targets | {TODAY} ===", flush=True)
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
