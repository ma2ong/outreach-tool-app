"""
WhatsApp Web CDP auto-sender -- uses browser CDP proxy to send messages fully automatically.
Opens each contact in a new tab, waits for chat to load, clicks Send, then closes tab.
"""
import sys, json, subprocess, time, datetime, urllib.parse, random
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

CDP = "http://localhost:3456"
TODAY = datetime.date.today().isoformat()
BASE = Path(__file__).parent
PROSPECTS_FILE = BASE / "pipeline/whatsapp/prospects.json"

CONTACTS = [
    # Brazil -- confirmed mobile
    {"no": 462, "country": "Brazil",  "company": "LED Eart",             "phone": "5585994324544",
     "msg": "Allen from Shenzhen - LED manufacturer. Panel rental and sales across Ceara for events - what pixel pitch are clients asking for on outdoor stages right now, P3.9 or something tighter?"},
    {"no": 463, "country": "Brazil",  "company": "CIA do LED",            "phone": "5551992314663",
     "msg": "Allen from Shenzhen - LED manufacturer. LED panels plus pyro effects for events in RS and SC is a creative combo. What screen sizes do you typically run for stage backdrops?"},
    {"no": 465, "country": "Brazil",  "company": "Projeta Producoes",     "phone": "5583988648221",
     "msg": "Hi, Allen from Shenzhen - LED manufacturer. Full event production - panels, projection, audio, stage structure - out of Paraiba. What pitch and size do you run for stage LED backdrops?"},
    # Mexico -- unverified
    {"no": 131, "country": "Mexico",  "company": "RGB Tronics",           "phone": "528117724695",
     "msg": "Allen from Shenzhen - LED manufacturer. 10+ years in giant LED screen wholesale in Mexico is a long run. What pixel pitch is selling fastest right now - outdoor P4, P6, or bigger?"},
    {"no": 132, "country": "Mexico",  "company": "DMX Technologies",      "phone": "525556622600",
     "msg": "Allen from Shenzhen - LED manufacturer. 10+ years wholesaling large-scale LED screens - what specs are clients requesting most from you right now?"},
    {"no": 133, "country": "Mexico",  "company": "iLED Mexico",           "phone": "528111015015",
     "msg": "Allen from Shenzhen - LED manufacturer. Curved, outdoor, and mobile LED with full engineering support - are clients asking for curved more for indoor retail or outdoor advertising?"},
    {"no": 134, "country": "Mexico",  "company": "Medios Mexico",         "phone": "525552932000",
     "msg": "Allen from Shenzhen - LED manufacturer. LED manufacturing plus outdoor digital advertising - what pitch range do your OOH billboard clients spec most?"},
    {"no": 135, "country": "Mexico",  "company": "HPMLED Grupo Vision",   "phone": "528111585800",
     "msg": "Allen from Shenzhen - LED manufacturer. LED display solutions - what pixel pitch range is moving most for your clients right now?"},
    {"no": 136, "country": "Mexico",  "company": "Pixel Window Mexico",   "phone": "524424564968",
     "msg": "Allen from Shenzhen - LED manufacturer. Offices across CDMX, Queretaro, and Guadalajara - what's driving most business right now, indoor installs, outdoor, or rental?"},
    {"no": 137, "country": "Mexico",  "company": "Showco Mexico",         "phone": "525550009480",
     "msg": "Allen from Shenzhen - LED manufacturer. LED screens plus AV for events - what indoor pixel pitch do clients ask for most on stage events in Mexico?"},
    {"no": 138, "country": "Mexico",  "company": "MAX Signage Mexico",    "phone": "525550213584",
     "msg": "Allen from Shenzhen - LED manufacturer. LED signage in Mexico - what's the split between outdoor advertising and indoor corporate installs for your clients?"},
    {"no": 139, "country": "Mexico",  "company": "Luft Screen",           "phone": "525523353227",
     "msg": "Allen from Shenzhen - LED manufacturer. LED screen solutions in CDMX - are you focused more on events and rental or permanent installs?"},
    {"no": 140, "country": "Mexico",  "company": "SAP LED",               "phone": "524442100824",
     "msg": "Allen from Shenzhen - LED manufacturer. Distributing LED displays in Mexico - what pixel pitch range are clients requesting most right now?"},
    {"no": 141, "country": "Mexico",  "company": "Eyecatch Mexico",       "phone": "525610046498",
     "msg": "Allen from Shenzhen - LED manufacturer. LED display and digital signage in Mexico - more demand from corporate clients or outdoor advertising?"},
    {"no": 142, "country": "Mexico",  "company": "MMP Screen",            "phone": "525554120445",
     "msg": "Allen from Shenzhen - LED manufacturer. LED screen solutions in Mexico - what's more common for your clients, retail signage or large video walls?"},
    {"no": 315, "country": "Mexico",  "company": "Fenix-Evolution LED",   "phone": "524771255013",
     "msg": "Allen from Shenzhen - LED manufacturer. Event LED rental from Leon to CDMX, Guadalajara, Monterrey, and Cancun - what pixel pitch do you run for outdoor stages, P3.9 or tighter?"},
    {"no": 355, "country": "Mexico",  "company": "DMX Technologies v2",   "phone": "525533169827",
     "msg": "Allen from Shenzhen - LED manufacturer. 20+ years making large-format LED for advertising and stadiums - what pitch are stadium clients specifying most right now?"},
    {"no": 356, "country": "Mexico",  "company": "HPMLED",                "phone": "528111580000",
     "msg": "Allen from Shenzhen - LED manufacturer. Indoor/outdoor video walls plus event displays - what's heavier in your order mix right now, permanent installs or rental?"},
    {"no": 357, "country": "Mexico",  "company": "Mundo Videowall",       "phone": "525575838168",
     "msg": "Allen from Shenzhen - LED manufacturer. 15 years integrating video walls for corporate, events, and signage - what indoor pixel pitch do you specify most for corporate installs?"},
]


def cdp(method, path, body=None):
    args = ["curl", "-s"]
    if body is not None:
        args += ["-X", "POST", f"{CDP}{path}", "-d", body]
    else:
        args += [f"{CDP}{path}"]
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", timeout=20)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"raw": r.stdout[:200]}


def new_tab(url):
    enc = urllib.parse.quote(url, safe=":/?=&")
    r = cdp("GET", f"/new?url={enc}")
    return r.get("targetId", "")


def eval_js(tid, js):
    r = subprocess.run(
        ["curl", "-s", "-X", "POST", f"{CDP}/eval?target={tid}", "-d", js],
        capture_output=True, text=True, encoding="utf-8", timeout=20
    )
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"error": r.stdout[:200]}


def close_tab(tid):
    subprocess.run(["curl", "-s", f"{CDP}/close?target={tid}"],
                   capture_output=True, timeout=10)


def wait_for_send_btn(tid, max_wait=25):
    """Wait until WA send button appears (or 'invalid number' / 'not on WA' dialog)."""
    for _ in range(max_wait):
        time.sleep(1)
        r = eval_js(tid, '''
(function() {
  var btn = document.querySelector('[data-testid="send"]') ||
            document.querySelector('[data-testid="compose-btn-send"]') ||
            document.querySelector('button[aria-label="Send"]') ||
            document.querySelector('span[data-testid="send"]');
  if (btn) return "send_ready";
  // Check for "phone not on WA" / invalid number dialog
  var body = document.body.innerText || "";
  if (body.includes("phone number shared via url is invalid") ||
      body.includes("not registered") ||
      body.includes("numero invalido") ||
      body.includes("Invalid phone") ||
      body.includes("not on WhatsApp")) return "not_on_wa";
  // Check for OK button on invalid number popup
  var okBtn = Array.from(document.querySelectorAll("button")).find(b => b.innerText.trim() === "OK");
  if (okBtn) return "invalid_popup";
  return "loading";
})()
''')
        status = r.get("value", "loading")
        if status in ("send_ready", "not_on_wa", "invalid_popup"):
            return status
    return "timeout"


def click_send(tid):
    return eval_js(tid, '''
(function() {
  var btn = document.querySelector('[data-testid="send"]') ||
            document.querySelector('[data-testid="compose-btn-send"]') ||
            document.querySelector('button[aria-label="Send"]') ||
            document.querySelector('span[data-testid="send"]');
  if (!btn) return "not_found";
  // Walk up to find clickable parent if needed
  var el = btn;
  for (var i = 0; i < 5; i++) {
    if (el.tagName === "BUTTON" || el.getAttribute("role") === "button") break;
    el = el.parentElement;
  }
  el.click();
  return "clicked";
})()
''')


def verify_sent(tid):
    """Check that the input box is now empty (message was sent)."""
    time.sleep(2)
    r = eval_js(tid, '''
(function() {
  var box = document.querySelector('[data-testid="conversation-compose-box-input"]') ||
            document.querySelector('div[contenteditable="true"][data-tab="10"]') ||
            document.querySelector('div[contenteditable="true"]');
  if (!box) return "box_gone";
  return box.innerText.trim() === "" ? "sent" : "still_has_text";
})()
''')
    return r.get("value", "unknown")


def update_pipeline(messaged, excluded_not_on_wa):
    with open(PROSPECTS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    updated = 0
    for p in data:
        no = p.get("no")
        if no in messaged:
            p["status"] = "messaged"
            p["touch_count"] = 1
            p["message_sent_date"] = TODAY
            p["message_text"] = messaged[no]
            updated += 1
        elif no in excluded_not_on_wa:
            p["status"] = "excluded"
            p["exclude_reason"] = "not_on_whatsapp"
            updated += 1

    # Always exclude landlines and duplicates
    ALWAYS_EXCLUDE = {
        358: "duplicate_of_140", 370: "duplicate_of_315",
        1: "landline", 2: "landline", 3: "landline", 4: "landline",
        7: "landline", 8: "landline", 9: "landline", 10: "landline",
        12: "landline", 13: "landline", 15: "landline", 18: "landline",
        19: "landline", 20: "landline", 24: "landline", 281: "landline",
        282: "landline", 349: "landline", 369: "landline", 381: "landline",
        41: "landline", 42: "landline", 43: "landline", 44: "landline",
        45: "landline", 47: "landline", 284: "landline", 285: "landline",
        322: "landline", 35: "landline", 212: "landline", 214: "landline",
        218: "landline", 72: "landline", 75: "landline", 88: "landline",
        89: "landline", 92: "landline", 93: "landline", 95: "landline",
        387: "landline", 422: "landline",
    }
    for p in data:
        no = p.get("no")
        if no in ALWAYS_EXCLUDE and p.get("status") != "excluded":
            p["status"] = "excluded"
            p["exclude_reason"] = ALWAYS_EXCLUDE[no]
            updated += 1

    with open(PROSPECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    from collections import Counter
    statuses = Counter(p.get("status") for p in data)
    print(f"\nPipeline updated: {updated} records changed")
    print(f"Totals: {dict(statuses)}")


def main():
    results = {"sent": [], "not_on_wa": [], "failed": []}
    messaged = {}
    excluded_not_on_wa = set()

    total = len(CONTACTS)
    for i, c in enumerate(CONTACTS, 1):
        print(f"\n[{i}/{total}] [{c['country']}] {c['company']}  +{c['phone']}")

        url = f"https://web.whatsapp.com/send?phone={c['phone']}&text={urllib.parse.quote(c['msg'])}"
        tid = new_tab(url)
        if not tid:
            print("  ✗ Could not open tab")
            results["failed"].append(c["no"])
            continue

        print("  → Tab opened, waiting for chat to load...")
        status = wait_for_send_btn(tid, max_wait=30)

        if status == "not_on_wa" or status == "invalid_popup":
            print(f"  ✗ Not on WhatsApp (or invalid number)")
            excluded_not_on_wa.add(c["no"])
            results["not_on_wa"].append(c["company"])
            close_tab(tid)

        elif status == "send_ready":
            click_result = click_send(tid)
            print(f"  → Click send: {click_result}")
            verify = verify_sent(tid)
            if verify in ("sent", "box_gone"):
                print(f"  ✓ SENT")
                messaged[c["no"]] = c["msg"]
                results["sent"].append(c["company"])
            else:
                print(f"  ? Send uncertain (verify={verify}), counting as sent")
                messaged[c["no"]] = c["msg"]
                results["sent"].append(c["company"])
            time.sleep(3)
            close_tab(tid)

        else:
            print(f"  ✗ Timeout waiting for chat ({status})")
            results["failed"].append(c["no"])
            close_tab(tid)

        # Interval between sends: 60-90s with jitter (skip after last)
        if i < total:
            wait = random.randint(60, 90)
            print(f"  ⏱ Waiting {wait}s before next...")
            time.sleep(wait)

    # Summary
    print("\n" + "="*50)
    print(f"DONE: {len(results['sent'])} sent, {len(results['not_on_wa'])} not on WA, {len(results['failed'])} failed")
    if results["sent"]:
        print(f"  Sent: {', '.join(results['sent'])}")
    if results["not_on_wa"]:
        print(f"  Not on WA: {', '.join(results['not_on_wa'])}")
    if results["failed"]:
        print(f"  Failed nos: {results['failed']}")

    # Update pipeline
    print("\nUpdating pipeline...")
    update_pipeline(messaged, excluded_not_on_wa)


if __name__ == "__main__":
    main()
