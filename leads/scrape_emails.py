"""
Scrape email addresses from Korean prospect websites.
Checks homepage + /contact + /about pages.
Saves found emails back into prospects.json.
"""
import json, re, time, sys, random
from pathlib import Path
import urllib.request, urllib.error, urllib.parse

sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).parent
PROSPECTS_FILE = BASE / "pipeline/whatsapp/prospects.json"

EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,6}"
)

JUNK_DOMAINS = {
    "example.com", "sentry.io", "wix.com", "wordpress.com",
    "google.com", "facebook.com", "naver.com", "kakao.com",
    "youtube.com", "instagram.com", "apple.com", "microsoft.com",
    "w3.org", "schema.org",
}

CONTACT_PATHS = ["/", "/contact", "/contact-us", "/contacts",
                 "/about", "/about-us", "/company", "/eng/contact",
                 "/en/contact", "/kr/contact"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
}


def fetch(url, timeout=10):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            for enc in ("utf-8", "euc-kr", "cp949", "latin-1"):
                try:
                    return raw.decode(enc)
                except Exception:
                    pass
            return raw.decode("utf-8", "replace")
    except Exception as e:
        return None


def extract_emails(html, site_domain):
    if not html:
        return set()
    found = set()
    for m in EMAIL_RE.finditer(html):
        addr = m.group(0).lower().rstrip(".")
        domain = addr.split("@")[-1]
        if domain in JUNK_DOMAINS:
            continue
        if any(junk in domain for junk in ("example", "test", "placeholder")):
            continue
        # prefer emails that share the company domain
        found.add(addr)
    return found


def best_email(emails, site_domain):
    """Pick the most relevant email: prefer company domain match, then info/sales/contact prefixes."""
    if not emails:
        return None
    site_host = site_domain.replace("www.", "").split("/")[0]
    # prefer same domain
    same = [e for e in emails if site_host in e]
    pool = same if same else list(emails)
    priority = ["info", "sales", "contact", "export", "international", "overseas", "trade"]
    for prefix in priority:
        match = [e for e in pool if e.startswith(prefix)]
        if match:
            return sorted(match)[0]
    return sorted(pool)[0]


def scrape_site(website):
    parsed = urllib.parse.urlparse(website)
    base = f"{parsed.scheme}://{parsed.netloc}"
    site_domain = parsed.netloc

    all_emails = set()

    for path in CONTACT_PATHS:
        url = base + path
        html = fetch(url)
        if html:
            emails = extract_emails(html, site_domain)
            all_emails |= emails
            if emails:
                print(f"    {path} → {emails}", flush=True)
        time.sleep(0.3)

    return best_email(all_emails, site_domain), all_emails


def main():
    with open(PROSPECTS_FILE, encoding="utf-8") as f:
        data = json.load(f)

    korea = [p for p in data if p.get("country") == "Korea"
             and p.get("status") == "prospect"
             and p.get("website")]

    print(f"Scraping {len(korea)} Korean sites...\n", flush=True)

    found_count = 0
    for i, p in enumerate(korea, 1):
        site = p["website"].strip()
        print(f"[{i}/{len(korea)}] no:{p['no']} {p['company_en']}", flush=True)
        print(f"  {site}", flush=True)

        email, all_emails = scrape_site(site)
        if email:
            p["email"] = email
            p["email_candidates"] = sorted(all_emails)
            found_count += 1
            print(f"  → FOUND: {email}", flush=True)
        else:
            p.setdefault("email", "")
            p.setdefault("email_candidates", [])
            print(f"  → not found", flush=True)

        print(flush=True)
        time.sleep(random.uniform(1.0, 2.0))

    with open(PROSPECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Done. Found emails for {found_count}/{len(korea)} sites.", flush=True)


if __name__ == "__main__":
    main()
