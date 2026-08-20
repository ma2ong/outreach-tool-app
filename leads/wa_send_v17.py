"""
WA sender v17 — v52 batch: 2 Brazil + 2 Colombia
Brazil: Led Midia Goiania (no:731), OFF Produtora (no:732)
Colombia: Logistica y Eventos Medellin (no:734), King Productions Bogota (no:735)
"""
import json, sys, time, random, datetime, urllib.parse, subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

TODAY = datetime.date.today().isoformat()
CDP = "http://localhost:3456"
BASE = Path(__file__).parent
PROSPECTS_FILE = BASE / "pipeline/whatsapp/prospects.json"

MSG_PT = (
    "Ola! Sou Allen da Shenzhen Maxcolor Visual, fabricante de paineis de LED na China. "
    "Vi o trabalho de voces com locacao de paineis LED — muito bom! "
    "Fornecemos paineis LED internos e externos P0.7 a P10 com preco direto de fabrica. "
    "Se tiverem projetos ou precisarem de orcamento, ficamos a disposicao."
)

MSG_ES = (
    "Hola, soy Allen de Shenzhen Maxcolor Visual, fabricante de pantallas LED en China. "
    "Vi su trabajo con alquiler de pantallas LED — muy buen trabajo. "
    "Suministramos paneles LED interiores y exteriores P0.7 a P10 con precio directo de fabrica. "
    "Si tienen proyectos o necesitan cotizacion, con gusto les ayudamos."
)

TARGETS = [
    {"no": 731, "company_en": "Led Midia Goiania",         "phone": "+55 62 98498-8484", "msg": MSG_PT},
    {"no": 732, "company_en": "OFF Produtora",              "phone": "+55 51 98034-1515", "msg": MSG_PT},
    {"no": 734, "company_en": "Logistica y Eventos Medellin", "phone": "+57 312 759 0337", "msg": MSG_ES},
    {"no": 735, "company_en": "King Productions Bogota",    "phone": "+57 322 445 8123",  "msg": MSG_ES},
]

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


def is_already_sent(no):
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
    print(f"=== WA Sender v17 | {len(TARGETS)} targets | {TODAY} ===\n", flush=True)

    sent_count = 0
    for i, t in enumerate(TARGETS, 1):
        print(f"[{i}/{len(TARGETS)}] no:{t['no']} {t['company_en']}  {t['phone']}", flush=True)

        if is_already_sent(t["no"]):
            print(f"  SKIP — already messaged", flush=True)
            continue

        ok = send_wa(t["no"], t["company_en"], t["phone"], t["msg"])
        if ok:
            sent_count += 1
        if i < len(TARGETS):
            wait = random.randint(65, 90)
            print(f"  waiting {wait}s...\n", flush=True)
            time.sleep(wait)

    print(f"\n=== Done: {sent_count}/{len(TARGETS)} sent ===", flush=True)


if __name__ == "__main__":
    main()
