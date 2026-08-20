"""
WA sender v3 - 3 Mexico contacts (355/356/357).
Fixes vs v2: pre-send dedup check, faster polling (100ms), longer window (45s),
URL-change as secondary send confirmation, immediate per-contact pipeline update.
"""
import subprocess, json, sys, time, urllib.parse, random, datetime
from pathlib import Path

TODAY = datetime.date.today().isoformat()
CDP = "http://localhost:3456"
CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe"
BASE = Path(__file__).parent
PROSPECTS_FILE = BASE / "pipeline/whatsapp/prospects.json"

CONTACTS = [
    {"no": 355, "country": "Mexico", "company": "DMX Technologies",
     "phone": "525533169827",
     "msg": "Allen from Shenzhen, LED manufacturer. 20+ years making large-format LED for advertising and stadiums. What pitch are stadium clients specifying most right now?"},
    {"no": 356, "country": "Mexico", "company": "HPMLED",
     "phone": "528111580000",
     "msg": "Allen from Shenzhen, LED manufacturer. Indoor/outdoor video walls plus event displays. What is heavier in your order mix - permanent installs or rental?"},
    {"no": 357, "country": "Mexico", "company": "Mundo Videowall",
     "phone": "525575838168",
     "msg": "Allen from Shenzhen, LED manufacturer. 15 years integrating video walls for corporate, events, and signage. What indoor pixel pitch do you specify most for corporate installs?"},
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


def get_tab_url(tid):
    r = cdp(f"/info?target={tid}")
    return r.get("url", "")


def inject(tid):
    r = cdp(f"/eval?target={tid}", OBSERVER_JS)
    return r.get("value", "")


def check_sent(tid):
    r = cdp(f"/eval?target={tid}", "window.__waSent||null")
    v = r.get("value", "")
    return v if v and v not in ("null", "None", "") else None


def load_pipeline():
    with open(PROSPECTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_pipeline(data):
    with open(PROSPECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_already_messaged(no):
    data = load_pipeline()
    for p in data:
        if p.get("no") == no:
            return p.get("status") == "messaged"
    return False


def mark_sent(no, msg):
    data = load_pipeline()
    for p in data:
        if p.get("no") == no and p.get("status") != "messaged":
            p["status"] = "messaged"
            p["touch_count"] = 1
            p["message_sent_date"] = TODAY
            p["message_text"] = msg
            break
    save_pipeline(data)
    from collections import Counter
    st = Counter(p.get("status") for p in data)
    print(f"  Pipeline: {dict(st)}", flush=True)


def mark_not_on_wa(no):
    data = load_pipeline()
    for p in data:
        if p.get("no") == no and p.get("status") == "prospect":
            p["status"] = "excluded"
            p["exclude_reason"] = "not_on_whatsapp"
            break
    save_pipeline(data)


def main():
    print(f"=== WA Sender v3 | {len(CONTACTS)} contacts | {TODAY} ===", flush=True)
    injected = set()
    seen_sent_texts = set()

    for i, c in enumerate(CONTACTS, 1):
        print(f"\n[{i}/{len(CONTACTS)}] [{c['country']}] {c['company']}  +{c['phone']}", flush=True)

        # DEDUP CHECK: skip if already messaged
        if is_already_messaged(c["no"]):
            print(f"  SKIP: already messaged in pipeline", flush=True)
            continue

        wa_url = (f"https://web.whatsapp.com/send?phone={c['phone']}"
                  f"&text={urllib.parse.quote(c['msg'])}")
        subprocess.Popen([CHROME, wa_url])

        tabs_before = get_wa_tids()

        # Poll: 45s window, 100ms intervals
        confirmed = False
        deadline = time.time() + 45
        new_tab_tid = None

        while time.time() < deadline:
            tabs = get_wa_tids()
            # Inject any new tabs immediately
            for tid in tabs - injected:
                inject(tid)
                injected.add(tid)
                if tid not in tabs_before:
                    new_tab_tid = tid
                    print(f"  Injected new tab {tid[:8]}", flush=True)

            # Check all tabs for send confirmation
            for tid in tabs:
                s = check_sent(tid)
                if s and s not in seen_sent_texts:
                    seen_sent_texts.add(s)
                    print(f"  SENT: {s}", flush=True)
                    mark_sent(c["no"], c["msg"])
                    confirmed = True
                    break
            if confirmed:
                break

            # Secondary: if new tab URL changed away from /send?phone= → likely sent or rejected
            if new_tab_tid and new_tab_tid in tabs:
                url = get_tab_url(new_tab_tid)
                if url and "send?phone=" not in url and "web.whatsapp.com" in url:
                    # Navigated away — could be sent (to chat) or not-on-WA (to home)
                    if "/send" not in url:
                        # Give it 2 more seconds for __waSent to appear
                        time.sleep(2)
                        s = check_sent(new_tab_tid)
                        if s and s not in seen_sent_texts:
                            seen_sent_texts.add(s)
                            print(f"  SENT (post-nav): {s}", flush=True)
                            mark_sent(c["no"], c["msg"])
                            confirmed = True
                        else:
                            print(f"  Tab navigated to: {url[:60]}", flush=True)
                        break

            time.sleep(0.1)

        if not confirmed:
            print(f"  skip (no WA or timeout)", flush=True)
            mark_not_on_wa(c["no"])

        # Rate limit between sends
        if i < len(CONTACTS):
            wait = random.randint(65, 85)
            print(f"  waiting {wait}s...", flush=True)
            time.sleep(wait)

    print(f"\n=== Done ===", flush=True)


if __name__ == "__main__":
    main()
