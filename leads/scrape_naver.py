"""
Search Naver for Korean prospects without websites to find email/contact info.
Uses Jina reader on Naver search results pages.
"""
import json, re, time, sys, urllib.parse, urllib.request, subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CDP = "http://localhost:3456"
BASE = Path(__file__).parent
PROSPECTS_FILE = BASE / "pipeline/whatsapp/prospects.json"

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,6}")
JUNK = {"wixpress", "sentry", "example", "naver.com", "kakao.com",
        "google.com", "facebook.com", "instagram.com", "youtube.com",
        "w3.org", "schema.org", "microsoft.com", "apple.com"}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}


def jina_fetch(url, timeout=12):
    jina_url = f"https://r.jina.ai/{url}"
    req = urllib.request.Request(jina_url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except Exception:
        return ""


def extract_emails(text):
    found = set()
    for m in EMAIL_RE.finditer(text):
        addr = m.group(0).lower().rstrip(".")
        if not any(j in addr for j in JUNK):
            found.add(addr)
    return found


def search_naver(company_name, phone=""):
    """Search Naver for company email using multiple queries."""
    queries = [
        f"{company_name} 이메일",
        f"{company_name} 연락처",
        f'"{company_name}" LED',
    ]
    if phone:
        # Strip non-digits for search
        digits = re.sub(r"\D", "", phone)
        if digits:
            queries.append(digits)

    all_emails = set()
    for q in queries[:2]:  # limit to 2 queries to stay fast
        encoded = urllib.parse.quote(q)
        naver_url = f"https://search.naver.com/search.naver?query={encoded}"
        text = jina_fetch(naver_url)
        if text:
            emails = extract_emails(text)
            all_emails |= emails
            if emails:
                break
        time.sleep(1)

    return all_emails


def best_email(emails, company_name):
    if not emails:
        return None
    # prefer non-personal looking emails
    priority = ["info", "sales", "contact", "admin", "led", "display"]
    for prefix in priority:
        match = [e for e in emails if e.startswith(prefix)]
        if match:
            return sorted(match)[0]
    return sorted(emails)[0]


def main():
    with open(PROSPECTS_FILE, encoding="utf-8") as f:
        data = json.load(f)

    # Targets: Korea prospects without website AND without email
    targets = [
        p for p in data
        if p.get("country") == "Korea"
        and p.get("status") == "prospect"
        and not p.get("website", "").strip()
        and not (p.get("email", "").strip()
                 and not any(j in p.get("email", "") for j in JUNK))
    ]

    print(f"Naver search for {len(targets)} companies without websites...\n", flush=True)
    found = 0

    for i, p in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] no:{p['no']} {p['company_en']}", flush=True)
        emails = search_naver(p["company_en"], p.get("phone", ""))
        email = best_email(emails, p["company_en"])

        if email:
            p["email"] = email
            p.setdefault("email_candidates", list(emails))
            found += 1
            print(f"  → FOUND: {email}", flush=True)
        else:
            print(f"  → not found", flush=True)

        time.sleep(1.5)

    with open(PROSPECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nDone. Found emails for {found}/{len(targets)} companies.", flush=True)


if __name__ == "__main__":
    main()
