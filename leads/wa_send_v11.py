"""
WA sender v11 - Argentina (nos 547, 548) + Peru (no 550)
Spanish message per country
"""
import json, sys, time, random, datetime, urllib.parse, subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

TODAY = datetime.date.today().isoformat()
CDP = "http://localhost:3456"
BASE = Path(__file__).parent
PROSPECTS_FILE = BASE / "pipeline/whatsapp/prospects.json"

MSG_AR = (
    "Hola, soy Allen de Shenzhen Maxcolor Visual, fabricante de pantallas LED en China. "
    "Trabajamos con empresas de alquiler e instalacion en Argentina. "
    "¿Tienen proyectos activos o planificados? "
    "Podemos dar soporte tecnico y cotizaciones competitivas."
)

MSG_PE = (
    "Hola, soy Allen de Shenzhen Maxcolor Visual, fabricante de pantallas LED en China. "
    "Trabajamos con empresas de alquiler e instalacion en Peru. "
    "¿Tienen proyectos activos o planificados? "
    "Podemos dar soporte tecnico y cotizaciones competitivas."
)

TARGET_NOS = [547, 548, 550]

COUNTRY_MSG = {
    "Argentina": MSG_AR,
    "Peru": MSG_PE,
}

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


def cdp(path, body=None, timeout=15):
    args = ["curl", "-s", "--max-time", str(timeout)]
    if body is not None:
        args += ["-X", "POST", f"{CDP}{path}", "-d", body]
    else:
        args += [f"{CDP}{path}"]
    r = subprocess.run(args, capture_output=True, timeout=timeout + 5)
    try:
        return json.loads(r.stdout.decode("utf-8", "replace"))
    except Exception:
        return {}


def open_tab(url):
    r = cdp(f"/new?url={urllib.parse.quote(url, safe=':/?=&')}")
    return r.get("targetId", "")


def close_tab(tid):
    cdp(f"/close?target={tid}")


def eval_js(tid, js, timeout=10):
    r = cdp(f"/eval?target={tid}", js, timeout=timeout)
    return r.get("value", "")


def clean_phone(phone):
    return "".join(c for c in phone if c.isdigit())


def is_already_messaged(no):
    with open(PROSPECTS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    for p in data:
        if p.get("no") == no and p.get("status") == "messaged":
            return True
    return False


def mark_sent(no, msg):
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


def send_wa(no, company, phone_raw, msg):
    if is_already_messaged(no):
        print(f"  SKIP — already messaged", flush=True)
        return False

    phone = clean_phone(phone_raw)
    enc_msg = urllib.parse.quote(msg)
    wa_url = f"https://web.whatsapp.com/send?phone={phone}&text={enc_msg}"

    tid = open_tab(wa_url)
    if not tid:
        print(f"  ERROR: CDP open_tab failed", flush=True)
        return False

    time.sleep(10)
    eval_js(tid, OBSERVER_JS)

    sent = False
    for _ in range(500):
        val = eval_js(tid, "window.__waSent || null")
        if val and val not in ("null", "already", ""):
            sent = True
            break
        cur_url = cdp(f"/info?target={tid}").get("url", "")
        if cur_url and "send?phone=" not in cur_url and "web.whatsapp.com" in cur_url:
            sent = True
            break
        time.sleep(0.1)

    close_tab(tid)

    if sent:
        mark_sent(no, msg)
        print(f"  SENT", flush=True)
        return True
    else:
        print(f"  TIMEOUT — not confirmed", flush=True)
        return False


def main():
    with open(PROSPECTS_FILE, encoding="utf-8") as f:
        data = json.load(f)

    nos_map = {p["no"]: p for p in data}
    contacts = [nos_map[no] for no in TARGET_NOS
                if no in nos_map and nos_map[no].get("status") != "messaged"
                and nos_map[no].get("phone")]

    print(f"=== WA Sender v11 | {len(contacts)} Argentina+Peru v25 | {TODAY} ===\n", flush=True)

    sent_count = 0
    for i, p in enumerate(contacts, 1):
        country = p.get("country", "Argentina")
        msg = COUNTRY_MSG.get(country, MSG_AR)
        print(f"[{i}/{len(contacts)}] no:{p['no']} {country} {p['company_en']}  {p['phone']}", flush=True)
        ok = send_wa(p["no"], p["company_en"], p["phone"], msg)
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
