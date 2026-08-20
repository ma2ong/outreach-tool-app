"""
WA sender v19 — v54 batch: Stage Audiovisual Curitiba (no:746)
Brazil mobile confirmed: +55 41 99717-0279
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
    "Vi o trabalho de voces com locacao de paineis LED para eventos em Curitiba — otimo trabalho! "
    "Fornecemos paineis LED internos e externos P0.7 a P10 com preco direto de fabrica. "
    "Se tiverem projetos ou precisarem de orcamento, ficamos a disposicao."
)

TARGETS = [
    {"no": 746, "company_en": "Stage Audiovisual Curitiba", "phone": "+55 41 99717-0279", "msg": MSG_PT},
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
    return cdp(f"/eval?target={tid}", js, timeout=timeout).get("value", "")


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
        print(f"  TIMEOUT — number may not be on WA", flush=True)
        return False


def main():
    print(f"=== WA Sender v19 | {len(TARGETS)} Brazil | {TODAY} ===\n", flush=True)

    sent_count = 0
    for i, t in enumerate(TARGETS, 1):
        print(f"[{i}/{len(TARGETS)}] no:{t['no']} {t['company_en']}  {t['phone']}", flush=True)

        if is_already_sent(t["no"]):
            print(f"  SKIP — already messaged", flush=True)
            continue

        ok = send_wa(t["no"], t["company_en"], t["phone"], t["msg"])
        if ok:
            sent_count += 1

    print(f"\n=== Done: {sent_count}/{len(TARGETS)} sent ===", flush=True)


if __name__ == "__main__":
    main()
