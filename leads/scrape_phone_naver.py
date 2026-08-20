"""
Search Korean company phone numbers on Naver via CDP.
Naver shows company info cards for phone numbers — much more reliable than name search.
Runs AFTER scrape_naver.py finishes to avoid pipeline write conflicts.
"""
import json, re, time, sys, urllib.parse, subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CDP = "http://localhost:3456"
BASE = Path(__file__).parent
PROSPECTS_FILE = BASE / "pipeline/whatsapp/prospects.json"

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,6}")
# Allow naver.com emails for Korean companies
JUNK = {"wixpress", "sentry", "example.com", "google.com", "facebook.com",
        "instagram.com", "youtube.com", "w3.org", "schema.org", "microsoft.com"}


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
    r = cdp(f"/new?url={url}")
    return r.get("targetId", "")


def close_tab(tid):
    cdp(f"/close?target={tid}")


def eval_js(tid, js, timeout=10):
    r = cdp(f"/eval?target={tid}", js, timeout=timeout)
    return r.get("value", "")


def clean_phone(phone):
    """Strip country code and non-digits for Naver search."""
    p = phone.replace("+82", "0").replace(" ", "").replace("-", "")
    # Remove leading zeros issues
    if p.startswith("82"):
        p = "0" + p[2:]
    return p


def search_phone_naver(phone_raw, company_name):
    """Search phone number on Naver, extract email from company info card."""
    phone = clean_phone(phone_raw)
    query = urllib.parse.quote(phone)
    url = f"https://search.naver.com/search.naver?query={query}"

    tid = open_tab(url)
    if not tid:
        return None

    time.sleep(4)  # wait for Naver to load

    # Extract all text from Naver result page, focus on company info cards
    js = """
    (function() {
        var texts = [];
        // Naver business info card selectors
        var selectors = [
            '.place_section',      // place/business info
            '.business_info',      // business card
            '.phone_card',         // phone result card
            '.thumb_box',          // company thumbnail
            '[data-nclick]',       // Naver tracking items
            '.title_area',
            '.list_wrp',
        ];
        selectors.forEach(function(sel) {
            document.querySelectorAll(sel).forEach(function(el) {
                texts.push(el.innerText);
            });
        });
        // Also get full page text as fallback
        texts.push(document.body.innerText.slice(0, 3000));
        return texts.join('\\n---\\n');
    })()
    """
    page_text = eval_js(tid, js)
    close_tab(tid)

    if not page_text:
        return None

    # Extract emails
    emails = set()
    for m in EMAIL_RE.finditer(page_text):
        addr = m.group(0).lower().rstrip(".")
        if not any(j in addr for j in JUNK):
            # Must look like a business email (not random text)
            local, domain = addr.rsplit("@", 1)
            if len(local) >= 3 and "." in domain:
                emails.add(addr)

    if not emails:
        return None

    # Prefer emails that match company domain pattern
    priority = ["info", "sales", "contact", "admin", "led", "display", "office"]
    for prefix in priority:
        match = [e for e in emails if e.split("@")[0].startswith(prefix)]
        if match:
            return sorted(match)[0]

    return sorted(emails)[0]


def main():
    with open(PROSPECTS_FILE, encoding="utf-8") as f:
        data = json.load(f)

    # Targets: Korea prospects without email, has phone
    JUNK_CHECK = {"wixpress", "sentry"}
    targets = [
        p for p in data
        if p.get("country") == "Korea"
        and p.get("status") == "prospect"
        and p.get("phone", "").strip()
        and not (p.get("email", "").strip()
                 and not any(j in p.get("email", "") for j in JUNK_CHECK))
    ]

    # Also fix Monde DID manually (synmww@naver.com was in bio)
    for p in data:
        if p.get("no") == 391 and not p.get("email"):
            p["email"] = "synmww@naver.com"
            print(f"Fixed Monde DID email: synmww@naver.com", flush=True)

    print(f"\nPhone-based Naver search for {len(targets)} companies...\n", flush=True)
    found = 0

    for i, p in enumerate(targets, 1):
        phone = p.get("phone", "").strip()
        if not phone:
            continue

        print(f"[{i}/{len(targets)}] no:{p['no']} {p['company_en']}  {phone}", flush=True)
        email = search_phone_naver(phone, p["company_en"])

        if email:
            p["email"] = email
            found += 1
            print(f"  → FOUND: {email}", flush=True)
        else:
            print(f"  → not found", flush=True)

        time.sleep(2)

    with open(PROSPECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    from collections import Counter
    st = Counter(p.get("status") for p in data)
    print(f"\nDone. Found {found} new emails.", flush=True)
    print(f"Pipeline: {dict(st)}", flush=True)


if __name__ == "__main__":
    main()
