"""
WA sender v4 - Colombia + Peru v19 batch (nos 490-509).
17 contacts with phones. Spanish message. Rate: 65-85s between sends.
"""
import subprocess, json, sys, time, urllib.parse, random, datetime
from pathlib import Path

TODAY = datetime.date.today().isoformat()
CDP = "http://localhost:3456"
CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe"
BASE = Path(__file__).parent
PROSPECTS_FILE = BASE / "pipeline/whatsapp/prospects.json"

# Spanish message for Colombia/Peru leads
MSG_TEMPLATE = (
    "Hola, soy Allen de Shenzhen Maxcolor Visual, fabricante de pantallas LED en China. "
    "Trabajamos con integradores y empresas de alquiler en Latinoamérica. "
    "¿Tienen proyectos activos o planificados? Podemos dar soporte técnico y cotizaciones competitivas."
)

# nos with phones from v19
TARGET_NOS = [490, 492, 493, 494, 496, 497, 498, 499,  # Colombia
              500, 501, 502, 503, 504, 505, 506, 507, 508]  # Peru

OBSERVER_JS = (
    "(function(){"
    "if(window.__waSent) return 'already';"
    "window.__waSent=null;"
    "function go(){"
    "var s=document.querySelector('span[data-icon=\"wds-ic-send-filled\"]')||document.querySelector('span[data-icon=\"send\"]');"
    "if(!s)return;"
    "var inp=document.querySelector('div[contenteditable]');"
    "if(!inp||inp.innerText.trim().length<10)return;"
    "var el=s;"
    "for(var i=0;i<8;i++){"
    "if(el.tagName==='BUTTON'||el.getAttribute('role')==='button'){el.click();window.__waSent=inp.innerText.slice(0,40);return;}"
    "if(!el.parentElement)break;el=el.parentElement;}"
    "s.click();window.__waSent=inp.innerText.slice(0,40);}"
    "go();"
    "new MutationObserver(go).observe(document.body,{childList:true,subtree:true});"
    "return 'ok';})()"
)


def cdp(path, body=None, timeout=6):
    args = ["curl", "-s"]
    if body is not None:
        args += ["-X", "POST", f"{CDP}{path}", "-d", body]
    else:
        args += [f"{CDP}{path}"]
    r = subprocess.run(args, capture_output=True, timeout=timeout)
    try:
        return json.loads(r.stdout.decode("utf-8", "replace"))
    except Exception:
        return {}


def get_wa_tids():
    r = cdp("/targets")
    return [t["targetId"] for t in (r if isinstance(r, list) else [])
            if "web.whatsapp.com" in t.get("url", "")]


def eval_js(tid, js):
    r = cdp(f"/eval?target={tid}", js)
    return r.get("value", "")


def is_already_messaged(no):
    with open(PROSPECTS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    for p in data:
        if p.get("no") == no and p.get("status") == "messaged":
            return True
    return False


def mark_sent(no, phone, msg):
    with open(PROSPECTS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    for p in data:
        if p.get("no") == no:
            p["status"] = "messaged"
            p["touch_count"] = 1
            p["message_sent_date"] = TODAY
            p["message_channel"] = "whatsapp"
            p["message_text"] = msg[:200]
            break
    with open(PROSPECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def clean_phone(phone):
    return "".join(c for c in phone if c.isdigit())


def send_wa(no, company, phone_raw, msg):
    if is_already_messaged(no):
        print(f"  SKIP — already messaged", flush=True)
        return False

    phone = clean_phone(phone_raw)
    enc_msg = urllib.parse.quote(msg)
    wa_url = f"https://web.whatsapp.com/send?phone={phone}&text={enc_msg}"

    subprocess.Popen([CHROME, "--new-tab", wa_url])
    time.sleep(8)

    tid = None
    for _ in range(20):
        tids = get_wa_tids()
        for t in tids:
            r = cdp(f"/info?target={t}")
            if phone[:6] in r.get("url", ""):
                tid = t
                break
        if tid:
            break
        time.sleep(0.5)

    if not tid:
        print(f"  ERROR: tab not found", flush=True)
        return False

    eval_js(tid, OBSERVER_JS)

    sent = False
    for _ in range(450):  # 45s timeout
        val = eval_js(tid, "window.__waSent || null")
        if val and val != "null" and val != "already":
            sent = True
            break
        cur_url = cdp(f"/info?target={tid}").get("url", "")
        if cur_url and "send?phone=" not in cur_url and "web.whatsapp.com" in cur_url:
            sent = True
            break
        time.sleep(0.1)

    cdp(f"/close?target={tid}")

    if sent:
        mark_sent(no, phone, msg)
        print(f"  SENT", flush=True)
        return True
    else:
        print(f"  TIMEOUT — not confirmed", flush=True)
        return False


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    with open(PROSPECTS_FILE, encoding="utf-8") as f:
        data = json.load(f)

    nos_map = {p["no"]: p for p in data}
    contacts = []
    for no in TARGET_NOS:
        p = nos_map.get(no)
        if not p:
            continue
        if p.get("status") == "messaged":
            continue
        phone = p.get("phone", "").strip()
        if not phone:
            continue
        contacts.append(p)

    print(f"=== WA Sender v4 | {len(contacts)} Colombia+Peru | {TODAY} ===\n", flush=True)

    sent_count = 0
    for i, p in enumerate(contacts, 1):
        print(f"[{i}/{len(contacts)}] no:{p['no']} {p['country']} {p['company_en']}  {p['phone']}", flush=True)
        ok = send_wa(p["no"], p["company_en"], p["phone"], MSG_TEMPLATE)
        if ok:
            sent_count += 1
        if i < len(contacts):
            wait = random.randint(65, 85)
            print(f"  waiting {wait}s...\n", flush=True)
            time.sleep(wait)

    from collections import Counter
    with open(PROSPECTS_FILE, encoding="utf-8") as f:
        final = json.load(f)
    st = Counter(p.get("status") for p in final)
    print(f"\n=== Done: {sent_count}/{len(contacts)} sent ===")
    print(f"Pipeline: {dict(st)}")


if __name__ == "__main__":
    main()
