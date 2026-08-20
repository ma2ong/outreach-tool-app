#!/usr/bin/env python3
"""
Jina reader email scraper for Korea LED prospects.
Targets: country=="Korea", status=="prospect", website set, email empty/fake.
"""

import json
import re
import time
import urllib.request
import urllib.error
from urllib.parse import urlparse

PROSPECTS_FILE = r"C:\Users\Administrator\ai-topic-generator\output\leads\pipeline\whatsapp\prospects.json"

EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,6}')

FAKE_KEYWORDS = [
    'wixpress', 'sentry', 'example', 'placeholder',
    'naver.com', 'kakao.com'
]

# Gmail is only ok if it contains the company name patterns; default exclude
GENERIC_FREEMAIL = ['gmail.com', 'yahoo.com', 'hotmail.com', 'daum.net', 'hanmail.net']

PRIORITY_PREFIXES = ['info', 'sales', 'contact', 'support', 'service', 'led', 'export', 'international']


def is_fake_email(email):
    email_lower = email.lower()
    for kw in FAKE_KEYWORDS:
        if kw in email_lower:
            return True
    return False


def is_generic_freemail(email):
    domain = email.split('@')[-1].lower()
    return domain in GENERIC_FREEMAIL


def get_domain(website):
    """Extract base domain from URL."""
    parsed = urlparse(website)
    return parsed.netloc or parsed.path


def get_base_url(website):
    """Get scheme + netloc."""
    parsed = urlparse(website)
    scheme = parsed.scheme or 'https'
    netloc = parsed.netloc or parsed.path
    return f"{scheme}://{netloc}"


def fetch_jina(url, timeout=20):
    """Fetch a URL via Jina reader. Returns text or None."""
    jina_url = f"https://r.jina.ai/{url}"
    req = urllib.request.Request(
        jina_url,
        headers={
            'User-Agent': 'Mozilla/5.0 (compatible; email-scraper/1.0)',
            'Accept': 'text/plain, */*'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
            return content.decode('utf-8', errors='replace')
    except Exception as e:
        print(f"  [WARN] Jina fetch failed for {url}: {e}")
        return None


def score_email(email, domain):
    """Score an email: higher = better candidate."""
    email_lower = email.lower()
    email_domain = email.split('@')[-1].lower()
    score = 0

    # Domain match
    domain_clean = domain.replace('www.', '').lower()
    if domain_clean and email_domain == domain_clean:
        score += 10
    elif domain_clean and domain_clean in email_domain:
        score += 5

    # Priority prefix
    prefix = email_lower.split('@')[0]
    for i, p in enumerate(PRIORITY_PREFIXES):
        if prefix == p:
            score += (8 - i)
            break
        elif prefix.startswith(p):
            score += (4 - min(i, 3))
            break

    # Penalty for generic freemail
    if is_generic_freemail(email):
        score -= 5

    return score


def extract_best_emails(text, domain):
    """Extract and rank emails from text."""
    if not text:
        return []

    found = EMAIL_REGEX.findall(text)
    # Deduplicate (case-insensitive)
    seen = {}
    for e in found:
        key = e.lower()
        if key not in seen:
            seen[key] = e

    candidates = []
    for email in seen.values():
        if is_fake_email(email):
            continue
        candidates.append(email)

    # Sort by score descending
    candidates.sort(key=lambda e: score_email(e, domain), reverse=True)
    return candidates


def needs_email(record):
    """Return True if this record needs email scraping."""
    if record.get('country') != 'Korea':
        return False
    if record.get('status') != 'prospect':
        return False
    website = record.get('website', '')
    if not website:
        return False

    email = record.get('email', '')
    if email:
        # Has an email — check if it's fake
        if not is_fake_email(email):
            return False  # Already has real email, skip
    return True


def scrape_emails_for_record(record):
    """Try main page, /contact, /about via Jina. Return (best_email, candidates)."""
    website = record['website']
    base = get_base_url(website)
    domain = get_domain(website)

    urls_to_try = [
        website,
        base.rstrip('/') + '/contact',
        base.rstrip('/') + '/about',
    ]

    all_candidates = []

    for url in urls_to_try:
        print(f"  Fetching: {url}")
        text = fetch_jina(url)
        if text:
            emails = extract_best_emails(text, domain)
            if emails:
                print(f"    Found {len(emails)} candidate(s): {emails[:3]}")
            all_candidates.extend(emails)
        time.sleep(0.8)  # ~20 RPM limit

    # Deduplicate across all pages
    seen = {}
    for e in all_candidates:
        key = e.lower()
        if key not in seen:
            seen[key] = e
    unique_candidates = list(seen.values())
    unique_candidates.sort(key=lambda e: score_email(e, domain), reverse=True)

    best = unique_candidates[0] if unique_candidates else ''
    return best, unique_candidates


def main():
    print(f"Loading {PROSPECTS_FILE}")
    with open(PROSPECTS_FILE, 'r', encoding='utf-8') as f:
        prospects = json.load(f)

    targets = [r for r in prospects if needs_email(r)]
    print(f"\nTargets: {len(targets)} Korea prospects needing email scraping\n")

    found_count = 0
    updated_nos = []

    for i, record in enumerate(targets):
        no = record.get('no', '?')
        company = record.get('company_en', '?')
        website = record.get('website', '')
        print(f"\n[{i+1}/{len(targets)}] #{no} {company} — {website}")

        best_email, candidates = scrape_emails_for_record(record)

        if best_email:
            print(f"  => Best email: {best_email}")
            record['email'] = best_email
            record['email_candidates'] = candidates
            found_count += 1
            updated_nos.append(no)
        else:
            print(f"  => No email found")
            # Ensure fields exist even if empty
            if 'email' not in record:
                record['email'] = ''
            if 'email_candidates' not in record:
                record['email_candidates'] = []

    # Save back
    with open(PROSPECTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(prospects, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"SUMMARY: Found {found_count} new emails out of {len(targets)} targets")
    if updated_nos:
        print(f"Updated records: #{', #'.join(str(n) for n in updated_nos)}")
    print(f"Saved to {PROSPECTS_FILE}")


if __name__ == '__main__':
    main()
