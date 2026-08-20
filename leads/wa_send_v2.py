"""
WA sender v2 - no threads, encoding-safe, MutationObserver auto-click.
Run: python output/leads/wa_send_v2.py
"""
import subprocess, json, sys, time, urllib.parse, random, datetime
from pathlib import Path

TODAY = datetime.date.today().isoformat()
CDP = "http://localhost:3456"
CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe"
BASE = Path(__file__).parent
PROSPECTS_FILE = BASE / "pipeline/whatsapp/prospects.json"

CONTACTS = [
    {"no":463,"country":"Brazil", "company":"CIA do LED",        "phone":"5551992314663","msg":"Allen from Shenzhen - LED manufacturer. LED panels plus pyro effects for events in RS and SC is a creative combo. What screen sizes do you typically run for stage backdrops?"},
    {"no":465,"country":"Brazil", "company":"Projeta Producoes", "phone":"5583988648221","msg":"Hi Allen from Shenzhen, LED manufacturer. Full event production out of Paraiba - panels, projection, audio, stage. What pitch and size do you run for stage LED backdrops?"},
    {"no":131,"country":"Mexico", "company":"RGB Tronics",       "phone":"528117724695", "msg":"Allen from Shenzhen, LED manufacturer. 10+ years in giant LED screen wholesale in Mexico. What pixel pitch is selling fastest right now - P4, P6, or bigger?"},
    {"no":132,"country":"Mexico", "company":"DMX Technologies",  "phone":"525556622600", "msg":"Allen from Shenzhen, LED manufacturer. 10+ years wholesaling large-scale LED screens. What specs are clients requesting most from you right now?"},
    {"no":133,"country":"Mexico", "company":"iLED Mexico",       "phone":"528111015015", "msg":"Allen from Shenzhen, LED manufacturer. Curved, outdoor, and mobile LED with full engineering. Are clients asking for curved more for indoor retail or outdoor advertising?"},
    {"no":134,"country":"Mexico", "company":"Medios Mexico",     "phone":"525552932000", "msg":"Allen from Shenzhen, LED manufacturer. LED manufacturing plus outdoor digital advertising. What pitch range do your OOH billboard clients spec most?"},
    {"no":135,"country":"Mexico", "company":"HPMLED GV",        "phone":"528111585800", "msg":"Allen from Shenzhen, LED manufacturer. LED display solutions. What pixel pitch range is moving most for your clients right now?"},
    {"no":136,"country":"Mexico", "company":"Pixel Window MX",  "phone":"524424564968", "msg":"Allen from Shenzhen, LED manufacturer. Offices in CDMX, Queretaro, and Guadalajara. What is driving most business - indoor installs, outdoor, or rental?"},
    {"no":137,"country":"Mexico", "company":"Showco Mexico",    "phone":"525550009480", "msg":"Allen from Shenzhen, LED manufacturer. LED screens plus AV for events. What indoor pixel pitch do clients ask for on stage events in Mexico?"},
    {"no":138,"country":"Mexico", "company":"MAX Signage MX",   "phone":"525550213584", "msg":"Allen from Shenzhen, LED manufacturer. LED signage in Mexico. What is the split between outdoor advertising and indoor corporate installs for your clients?"},
    {"no":139,"country":"Mexico", "company":"Luft Screen",      "phone":"525523353227", "msg":"Allen from Shenzhen, LED manufacturer. LED screens in CDMX. Are you focused more on events and rental or permanent installs?"},
    {"no":140,"country":"Mexico", "company":"SAP LED",          "phone":"524442100824", "msg":"Allen from Shenzhen, LED manufacturer. Distributing LED displays in Mexico. What pixel pitch range are clients requesting most?"},
    {"no":141,"country":"Mexico", "company":"Eyecatch Mexico",  "phone":"525610046498", "msg":"Allen from Shenzhen, LED manufacturer. LED display and digital signage in Mexico. More demand from corporate clients or outdoor advertising?"},
    {"no":142,"country":"Mexico", "company":"MMP Screen",       "phone":"525554120445", "msg":"Allen from Shenzhen, LED manufacturer. LED screens in Mexico. What is more common for your clients - retail signage or large video walls?"},
    {"no":355,"country":"Mexico", "company":"DMX Tech v2",      "phone":"525533169827", "msg":"Allen from Shenzhen, LED manufacturer. 20+ years making large-format LED for advertising and stadiums. What pitch are stadium clients specifying most right now?"},
    {"no":356,"country":"Mexico", "company":"HPMLED",           "phone":"528111580000", "msg":"Allen from Shenzhen, LED manufacturer. Indoor/outdoor video walls plus event displays. What is heavier in your order mix - permanent installs or rental?"},
    {"no":357,"country":"Mexico", "company":"Mundo Videowall",  "phone":"525575838168", "msg":"Allen from Shenzhen, LED manufacturer. 15 years integrating video walls for corporate, events, and signage. What indoor pixel pitch do you specify most for corporate installs?"},
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
    data = cdp("/targets")
    if isinstance(data, list):
        return {t["targetId"] for t in data if "web.whatsapp.com" in t.get("url", "")}
    return set()

def inject(tid):
    r = cdp(f"/eval?target={tid}", OBSERVER_JS)
    return r.get("value", "")

def check_sent(tid):
    r = cdp(f"/eval?target={tid}", "window.__waSent||null")
    v = r.get("value", "")
    return v if v and v not in ("null", "None", "") else None

def update_pipeline(sent_nos, not_on_wa_nos):
    msg_map = {c["no"]: c["msg"] for c in CONTACTS}
    msg_map[462] = "Allen from Shenzhen - LED manufacturer. Panel rental and sales across Ceara for events - what pixel pitch are clients asking for on outdoor stages right now, P3.9 or something tighter?"
    msg_map[315] = "Allen from Shenzhen - LED manufacturer. Event LED rental from Leon to CDMX, Guadalajara, Monterrey, and Cancun - what pixel pitch do you run for outdoor stages, P3.9 or tighter?"

    LANDLINES = {1,2,3,4,7,8,9,10,12,13,15,18,19,20,24,281,282,349,369,381,
                 41,42,43,44,45,47,284,285,322,35,212,214,218,72,75,
                 88,89,92,93,95,387,422,358,370}

    with open(PROSPECTS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    for p in data:
        no = p.get("no")
        if no in sent_nos and p.get("status") != "messaged":
            p["status"] = "messaged"
            p["touch_count"] = 1
            p["message_sent_date"] = TODAY
            p["message_text"] = msg_map.get(no, "")
        elif no in not_on_wa_nos and p.get("status") == "prospect":
            p["status"] = "excluded"
            p["exclude_reason"] = "not_on_whatsapp"
        elif no in LANDLINES and p.get("status") not in ("messaged", "excluded"):
            p["status"] = "excluded"
            p["exclude_reason"] = "landline" if no not in (358,370) else f"dup_{358 if no==358 else 370}"

    with open(PROSPECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    from collections import Counter
    st = Counter(p.get("status") for p in data)
    print(f"Pipeline: {dict(st)}")


def main():
    print(f"=== WA Sender v2 | {len(CONTACTS)} contacts | {TODAY} ===", flush=True)
    already_sent = {462, 315}  # confirmed sent before this run
    sent_nos = set(already_sent)
    not_on_wa_nos = set()
    injected = set()
    seen_sent_texts = set()

    # Pre-inject into existing tabs
    known = get_wa_tids()
    for tid in known:
        inject(tid)
        injected.add(tid)
    print(f"Pre-injected {len(injected)} existing tabs", flush=True)
    print(flush=True)

    for i, c in enumerate(CONTACTS, 1):
        print(f"[{i}/{len(CONTACTS)}] [{c['country']}] {c['company']}  +{c['phone']}", flush=True)
        wa_url = (f"https://web.whatsapp.com/send?phone={c['phone']}"
                  f"&text={urllib.parse.quote(c['msg'])}")
        subprocess.Popen([CHROME, wa_url])

        # Poll for up to 25s: detect new tabs and check for send
        confirmed = False
        deadline = time.time() + 25
        while time.time() < deadline:
            tabs = get_wa_tids()
            # Inject any new tabs immediately
            for tid in tabs - injected:
                inject(tid)
                injected.add(tid)
            # Check all tabs for a new sent message
            for tid in tabs:
                s = check_sent(tid)
                if s and s not in seen_sent_texts:
                    seen_sent_texts.add(s)
                    sent_nos.add(c["no"])
                    print(f"  SENT: {s}", flush=True)
                    confirmed = True
                    break
            if confirmed:
                break
            time.sleep(0.25)

        if not confirmed:
            print(f"  skip (no WA or timeout)", flush=True)
            not_on_wa_nos.add(c["no"])

        # Rate limit between sends
        if i < len(CONTACTS):
            wait = random.randint(65, 85)
            print(f"  waiting {wait}s...", flush=True)
            time.sleep(wait)

    print(flush=True)
    print(f"=== Done: {len(sent_nos)} sent, {len(not_on_wa_nos)} skipped ===", flush=True)
    print(f"Sent nos: {sorted(sent_nos)}", flush=True)
    print(f"Skipped nos: {sorted(not_on_wa_nos)}", flush=True)
    print(flush=True)
    print("Updating pipeline...", flush=True)
    update_pipeline(sent_nos, not_on_wa_nos)


if __name__ == "__main__":
    main()
