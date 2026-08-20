"""
WhatsApp auto-sender with MutationObserver injection.
Strategy:
  1. Inject auto-click observer into every WA tab as soon as it appears
  2. Open Chrome with WA send URLs (15s intervals)
  3. Observer fires instantly when send button appears, no polling delay
"""
import subprocess, json, sys, time, urllib.parse, datetime, random, threading
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

CDP = "http://localhost:3456"
CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe"
TODAY = datetime.date.today().isoformat()
BASE = Path(__file__).parent
PROSPECTS_FILE = BASE / "pipeline/whatsapp/prospects.json"

# All contacts EXCEPT already sent: 315 (Fenix), 462 (LED Eart)
CONTACTS = [
    # Brazil -- confirmed mobile
    {"no": 463, "country": "Brazil",  "company": "CIA do LED",          "phone": "5551992314663",
     "msg": "Allen from Shenzhen - LED manufacturer. LED panels plus pyro effects for events in RS and SC is a creative combo. What screen sizes do you typically run for stage backdrops?"},
    {"no": 465, "country": "Brazil",  "company": "Projeta Producoes",   "phone": "5583988648221",
     "msg": "Hi, Allen from Shenzhen - LED manufacturer. Full event production - panels, projection, audio, stage structure - out of Paraiba. What pitch and size do you run for stage LED backdrops?"},
    # Mexico
    {"no": 131, "country": "Mexico",  "company": "RGB Tronics",         "phone": "528117724695",
     "msg": "Allen from Shenzhen - LED manufacturer. 10+ years in giant LED screen wholesale in Mexico is a long run. What pixel pitch is selling fastest right now - outdoor P4, P6, or bigger?"},
    {"no": 132, "country": "Mexico",  "company": "DMX Technologies",    "phone": "525556622600",
     "msg": "Allen from Shenzhen - LED manufacturer. 10+ years wholesaling large-scale LED screens - what specs are clients requesting most from you right now?"},
    {"no": 133, "country": "Mexico",  "company": "iLED Mexico",         "phone": "528111015015",
     "msg": "Allen from Shenzhen - LED manufacturer. Curved, outdoor, and mobile LED with full engineering support - are clients asking for curved more for indoor retail or outdoor advertising?"},
    {"no": 134, "country": "Mexico",  "company": "Medios Mexico",       "phone": "525552932000",
     "msg": "Allen from Shenzhen - LED manufacturer. LED manufacturing plus outdoor digital advertising - what pitch range do your OOH billboard clients spec most?"},
    {"no": 135, "country": "Mexico",  "company": "HPMLED Grupo Vision", "phone": "528111585800",
     "msg": "Allen from Shenzhen - LED manufacturer. LED display solutions - what pixel pitch range is moving most for your clients right now?"},
    {"no": 136, "country": "Mexico",  "company": "Pixel Window Mexico", "phone": "524424564968",
     "msg": "Allen from Shenzhen - LED manufacturer. Offices across CDMX, Queretaro, and Guadalajara - what's driving most business right now, indoor installs, outdoor, or rental?"},
    {"no": 137, "country": "Mexico",  "company": "Showco Mexico",       "phone": "525550009480",
     "msg": "Allen from Shenzhen - LED manufacturer. LED screens plus AV for events - what indoor pixel pitch do clients ask for most on stage events in Mexico?"},
    {"no": 138, "country": "Mexico",  "company": "MAX Signage Mexico",  "phone": "525550213584",
     "msg": "Allen from Shenzhen - LED manufacturer. LED signage in Mexico - what's the split between outdoor advertising and indoor corporate installs for your clients?"},
    {"no": 139, "country": "Mexico",  "company": "Luft Screen",         "phone": "525523353227",
     "msg": "Allen from Shenzhen - LED manufacturer. LED screen solutions in CDMX - are you focused more on events and rental or permanent installs?"},
    {"no": 140, "country": "Mexico",  "company": "SAP LED",             "phone": "524442100824",
     "msg": "Allen from Shenzhen - LED manufacturer. Distributing LED displays in Mexico - what pixel pitch range are clients requesting most right now?"},
    {"no": 141, "country": "Mexico",  "company": "Eyecatch Mexico",     "phone": "525610046498",
     "msg": "Allen from Shenzhen - LED manufacturer. LED display and digital signage in Mexico - more demand from corporate clients or outdoor advertising?"},
    {"no": 142, "country": "Mexico",  "company": "MMP Screen",          "phone": "525554120445",
     "msg": "Allen from Shenzhen - LED manufacturer. LED screen solutions in Mexico - what's more common for your clients, retail signage or large video walls?"},
    {"no": 355, "country": "Mexico",  "company": "DMX Technologies v2", "phone": "525533169827",
     "msg": "Allen from Shenzhen - LED manufacturer. 20+ years making large-format LED for advertising and stadiums - what pitch are stadium clients specifying most right now?"},
    {"no": 356, "country": "Mexico",  "company": "HPMLED",              "phone": "528111580000",
     "msg": "Allen from Shenzhen - LED manufacturer. Indoor/outdoor video walls plus event displays - what's heavier in your order mix right now, permanent installs or rental?"},
    {"no": 357, "country": "Mexico",  "company": "Mundo Videowall",     "phone": "525575838168",
     "msg": "Allen from Shenzhen - LED manufacturer. 15 years integrating video walls for corporate, events, and signage - what indoor pixel pitch do you specify most for corporate installs?"},
]

# JS: inject auto-clicker (MutationObserver) that fires the moment send button appears
OBSERVER_JS = r"""
(function() {
  if (window.__wa_ac_v2) return 'already';
  window.__wa_ac_v2 = true;
  window.__wa_last_sent = null;

  function tryClickSend() {
    var icons = ['wds-ic-send-filled', 'send'];
    for (var i = 0; i < icons.length; i++) {
      var span = document.querySelector('span[data-icon="' + icons[i] + '"]');
      if (!span) continue;
      var input = document.querySelector('div[contenteditable]');
      if (!input || input.innerText.trim().length < 10) continue;
      // Walk up to find button
      var el = span;
      for (var j = 0; j < 8; j++) {
        if (el.tagName === 'BUTTON' || el.getAttribute('role') === 'button') {
          el.click();
          window.__wa_last_sent = new Date().toISOString() + '|' + input.innerText.slice(0,40);
          return 'clicked_button';
        }
        if (!el.parentElement) break;
        el = el.parentElement;
      }
      span.click();
      window.__wa_last_sent = new Date().toISOString() + '|direct';
      return 'clicked_span';
    }
    return null;
  }

  // Try immediately
  tryClickSend();

  // Watch DOM for changes
  var obs = new MutationObserver(function() { tryClickSend(); });
  obs.observe(document.body, {childList: true, subtree: true});
  window.__wa_obs = obs;
  return 'observer_injected';
})()
"""

def cdp_eval(tid, js, timeout=6):
    try:
        r = subprocess.run(
            ["curl", "-s", "-X", "POST", f"{CDP}/eval?target={tid}", "-d", js],
            capture_output=True, text=True, encoding="utf-8", timeout=timeout
        )
        d = json.loads(r.stdout)
        return d.get("value", d.get("error", ""))
    except Exception as e:
        return f"err:{e}"

def get_wa_targets():
    try:
        r = subprocess.run(["curl", "-s", f"{CDP}/targets"],
                           capture_output=True, text=True, encoding="utf-8", timeout=5)
        data = json.loads(r.stdout)
        return {t["targetId"]: t.get("url", "") for t in data
                if "web.whatsapp.com" in t.get("url", "")}
    except:
        return {}

def open_chrome(url):
    subprocess.Popen([CHROME, url])

def check_sent(tid):
    """Check if this tab sent something via the observer."""
    r = cdp_eval(tid, "window.__wa_last_sent || 'none'", timeout=4)
    return r if r and r != "none" else None

# Track state
injected_tabs = set()
sent_results = {}   # no -> result string
lock = threading.Lock()

def injector_loop(stop_event):
    """Background thread: inject observer into any new WA tab immediately."""
    while not stop_event.is_set():
        tabs = get_wa_targets()
        for tid in tabs:
            if tid not in injected_tabs:
                result = cdp_eval(tid, OBSERVER_JS, timeout=5)
                with lock:
                    injected_tabs.add(tid)
                if result and result != "already":
                    print(f"  [inject] {tid[:16]} => {result}")
        time.sleep(0.15)  # check every 150ms

def main():
    print("=== WhatsApp Auto-Sender v2 (MutationObserver) ===")
    print(f"Contacts: {len(CONTACTS)}")
    print()

    # Pre-inject into all existing WA tabs
    print("Pre-injecting observer into existing WA tabs...")
    tabs = get_wa_targets()
    for tid in tabs:
        result = cdp_eval(tid, OBSERVER_JS, timeout=5)
        injected_tabs.add(tid)
        print(f"  {tid[:16]} => {result}")
    print()

    # Start background injector thread
    stop_event = threading.Event()
    injector_thread = threading.Thread(target=injector_loop, args=(stop_event,), daemon=True)
    injector_thread.start()

    # Process each contact
    for i, c in enumerate(CONTACTS, 1):
        print(f"[{i}/{len(CONTACTS)}] [{c['country']}] {c['company']}  +{c['phone']}")

        # Build WA send URL
        wa_url = (f"https://web.whatsapp.com/send?phone={c['phone']}"
                  f"&text={urllib.parse.quote(c['msg'])}")

        # Open Chrome with the URL
        open_chrome(wa_url)
        time.sleep(0.3)  # tiny delay for tab to appear in CDP

        # Wait up to 30s for the observer to fire in the new tab
        tab_found = None
        deadline = time.time() + 30
        while time.time() < deadline:
            tabs = get_wa_targets()
            for tid in tabs:
                if tid in injected_tabs:
                    sent = check_sent(tid)
                    if sent and tid not in sent_results.values():
                        # This tab sent something
                        if no_already_sent(sent, sent_results):
                            sent_results[c["no"]] = {"tid": tid, "sent": sent, "company": c["company"]}
                            print(f"  ✓ SENT: {c['company']} -- {sent[:60]}")
                            tab_found = tid
                            break
            if tab_found:
                break
            time.sleep(0.3)

        if not tab_found:
            print(f"  ? Timeout -- could not confirm send for {c['company']}")
            sent_results[c["no"]] = {"tid": None, "sent": None, "company": c["company"], "status": "unconfirmed"}

        # Interval between sends (60-90s with jitter)
        if i < len(CONTACTS):
            interval = random.randint(60, 90)
            print(f"  ⏱ {interval}s until next...")
            time.sleep(interval)

    stop_event.set()

    # Summary
    print()
    print("=" * 50)
    confirmed = [no for no, r in sent_results.items() if r.get("sent")]
    unconfirmed = [no for no, r in sent_results.items() if not r.get("sent")]
    print(f"DONE: {len(confirmed)} confirmed, {len(unconfirmed)} unconfirmed")
    for no, r in sent_results.items():
        status = "✓" if r.get("sent") else "?"
        print(f"  {status} no:{no} {r['company']}")

    # Update pipeline
    update_pipeline(confirmed, [315, 462])  # 315, 462 already sent earlier


def no_already_sent(sent_str, results):
    """Avoid counting the same send event twice."""
    for r in results.values():
        if r.get("sent") and r["sent"] == sent_str:
            return False
    return True


def update_pipeline(messaged_nos, also_messaged):
    all_messaged = set(messaged_nos) | set(also_messaged)
    contact_msgs = {c["no"]: c["msg"] for c in CONTACTS}
    # Fénix msg
    fenix_msg = "Allen from Shenzhen - LED manufacturer. Event LED rental from Leon to CDMX, Guadalajara, Monterrey, and Cancun - what pixel pitch do you run for outdoor stages, P3.9 or tighter?"
    contact_msgs[315] = fenix_msg

    ALWAYS_EXCLUDE = {
        358: "duplicate_of_140", 370: "duplicate_of_315",
        1:"landline",2:"landline",3:"landline",4:"landline",7:"landline",8:"landline",
        9:"landline",10:"landline",12:"landline",13:"landline",15:"landline",18:"landline",
        19:"landline",20:"landline",24:"landline",281:"landline",282:"landline",
        349:"landline",369:"landline",381:"landline",
        41:"landline",42:"landline",43:"landline",44:"landline",45:"landline",47:"landline",
        284:"landline",285:"landline",322:"landline",
        35:"landline",212:"landline",214:"landline",218:"landline",
        72:"landline",75:"landline",
        88:"landline",89:"landline",92:"landline",93:"landline",95:"landline",
        387:"landline",422:"landline",
    }

    with open(PROSPECTS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    changed = 0
    for p in data:
        no = p.get("no")
        if no in all_messaged and p.get("status") != "messaged":
            p["status"] = "messaged"
            p["touch_count"] = 1
            p["message_sent_date"] = TODAY
            p["message_text"] = contact_msgs.get(no, "")
            changed += 1
        elif no in ALWAYS_EXCLUDE and p.get("status") != "excluded":
            p["status"] = "excluded"
            p["exclude_reason"] = ALWAYS_EXCLUDE[no]
            changed += 1

    with open(PROSPECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    from collections import Counter
    statuses = Counter(p.get("status") for p in data)
    print(f"\nPipeline updated: {changed} changed")
    print(f"Totals: {dict(statuses)}")


if __name__ == "__main__":
    main()
