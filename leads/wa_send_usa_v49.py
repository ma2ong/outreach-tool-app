"""
WA Sender USA v49 — tries all unsent USA prospects (nos 510-517 + 706-714)
Includes existing pipeline prospects + new v49 entries.
Korea projects message approach.
Daily limit: 30 sends. Run update_pipeline_v49_wa.py first.
"""
import subprocess, json, sys, time, urllib.parse, random, datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

TODAY = datetime.date.today().isoformat()
CDP = "http://localhost:3456"
CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe"
BASE = Path(__file__).parent
PROSPECTS_FILE = BASE / "pipeline/whatsapp/prospects.json"

WA_MSG = (
    "Hi, I'd like to share some recent LED display projects we delivered in Korea — "
    "P1.86 fine-pitch indoor walls, P2.5 commercial installs, and P3.91/P10 outdoor screens. "
    "If you have any upcoming LED projects, feel free to contact me anytime. "
    "Happy to recommend suitable products and provide competitive pricing.\n\n"
    "Best regards,\nAllen Ma\nShenzhen Maxcolor Visual Co., Ltd.\n"
    "WhatsApp/WeChat: +86 135-7087-1001"
)

# All USA prospect nos to attempt (existing + v49 new)
USA_NOS = [510, 512, 516, 517,   # existing pipeline prospects (511 has no phone)
           706, 707, 708, 709, 710, 712, 713, 714]  # v49 new entries

OBSERVER_JS = (
    "(function(){"
    "if(window.__waSent) return 'already';"
    "window.__waSent=null;"
    "function go(){"
    "var s=document.querySelector('span[data-icon=\"wds-ic-send-filled\"]')"
    "||document.querySelector('span[data-icon=\"send\"]');"
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
    return cdp(f"/info?target={tid}").get("url", "")


def inject(tid):
    return cdp(f"/eval?target={tid}", OBSERVER_JS).get("value", "")


def check_sent(tid):
    v = cdp(f"/eval?target={tid}", "window.__waSent||null").get("value", "")
    return v if v and v not in ("null", "None", "") else None


def load_pipeline():
    return json.load(open(PROSPECTS_FILE, encoding="utf-8"))


def save_pipeline(data):
    with open(PROSPECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def mark_sent(no, msg):
    data = load_pipeline()
    for p in data:
        if p.get("no") == no and p.get("status") != "messaged":
            p["status"] = "messaged"
            p["touch_count"] = p.get("touch_count", 0) + 1
            p["message_sent_date"] = TODAY
            p["message_channel"] = "whatsapp"
            p["message_text"] = msg[:120]
            break
    save_pipeline(data)


def mark_not_on_wa(no):
    data = load_pipeline()
    for p in data:
        if p.get("no") == no and p.get("status") == "prospect":
            p["status"] = "excluded"
            p["exclude_reason"] = "not_on_whatsapp"
            break
    save_pipeline(data)


def main():
    all_data = load_pipeline()
    prospects = {p["no"]: p for p in all_data
                 if p.get("no") in USA_NOS and p.get("status") == "prospect"}

    queue = []
    for no in USA_NOS:
        if no in prospects:
            p = prospects[no]
            phone = p.get("phone") or p.get("phone_whatsapp", "")
            phone_clean = "".join(c for c in str(phone) if c.isdigit())
            if phone_clean:
                queue.append({"no": no, "company": p.get("company_en", ""), "city": p.get("city", ""), "phone": phone_clean})
            else:
                print(f"  SKIP no={no} {p.get('company_en','')} — no phone number", flush=True)
        else:
            print(f"  SKIP no={no} — not in pipeline or already messaged", flush=True)

    print(f"=== WA Sender USA v49 | {len(queue)} to try | {TODAY} ===", flush=True)
    print(f"Note: US landlines will show 'phone not on WA' — that's normal.", flush=True)
    print()

    injected = set()
    seen_sent_texts = set()
    sent_count = 0

    for i, c in enumerate(queue, 1):
        print(f"[{i}/{len(queue)}] {c['company']} ({c['city']})  +{c['phone']}", flush=True)

        wa_url = (f"https://web.whatsapp.com/send?phone={c['phone']}"
                  f"&text={urllib.parse.quote(WA_MSG)}")
        subprocess.Popen([CHROME, wa_url])

        tabs_before = get_wa_tids()
        confirmed = False
        deadline = time.time() + 40
        new_tab_tid = None

        while time.time() < deadline:
            tabs = get_wa_tids()
            for tid in tabs - injected:
                inject(tid)
                injected.add(tid)
                if tid not in tabs_before:
                    new_tab_tid = tid
                    print(f"  injected tab {tid[:8]}", flush=True)

            for tid in tabs:
                s = check_sent(tid)
                if s and s not in seen_sent_texts:
                    seen_sent_texts.add(s)
                    print(f"  SENT: {s}", flush=True)
                    mark_sent(c["no"], WA_MSG)
                    confirmed = True
                    sent_count += 1
                    break
            if confirmed:
                break

            if new_tab_tid and new_tab_tid in tabs:
                url = get_tab_url(new_tab_tid)
                if url and "send?phone=" not in url and "web.whatsapp.com" in url:
                    if "/send" not in url:
                        time.sleep(2)
                        s = check_sent(new_tab_tid)
                        if s and s not in seen_sent_texts:
                            seen_sent_texts.add(s)
                            print(f"  SENT (post-nav): {s}", flush=True)
                            mark_sent(c["no"], WA_MSG)
                            confirmed = True
                            sent_count += 1
                        else:
                            print(f"  not on WA (navigated to: {url[:60]})", flush=True)
                        break

            time.sleep(0.1)

        if not confirmed:
            print(f"  not on WhatsApp / timeout", flush=True)
            mark_not_on_wa(c["no"])

        if i < len(queue):
            wait = random.randint(65, 85)
            print(f"  waiting {wait}s...\n", flush=True)
            time.sleep(wait)

    print(f"\n=== Done: {sent_count}/{len(queue)} WA messages sent ===", flush=True)


if __name__ == "__main__":
    main()
