#!/usr/bin/env python3
"""
Round 2: Retry sites that failed due to 429/timeout in round 1.
Increases sleep interval to 3s to stay well under Jina's 20 RPM limit.
"""

import json
import re
import time
import urllib.request
from urllib.parse import urlparse

PROSPECTS_FILE = r"C:\Users\Administrator\ai-topic-generator\output\leads\pipeline\whatsapp\prospects.json"

EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,6}')

FAKE_KEYWORDS = ['wixpress', 'sentry', 'example', 'placeholder']
GENERIC_FREEMAIL = ['gmail.com', 'yahoo.com', 'hotmail.com', 'daum.net', 'hanmail.net', 'naver.com', 'kakao.com']

# Sites with 422 errors are blocked by Jina — skip them
SKIP_STATUS_422 = {
    'eng.galaxialed.com', 'kodico.co.kr', 'tagsolution.kr',
    'mpartners.co.kr', 'vissem.com', 'www.vissem.com', 'kioskkorea.com',
    'koled.co.kr', 'ldss.co.kr', 'lzone.co.kr', 'xtrmgroup.co.kr',
    'www.primemedia.co.kr', 'coses.co.kr', 'www.coses.co.kr',
    'nsled.kr', 'www.nsled.kr',
}

PRIORITY_PREFIXES = ['info', 'sales', 'contact', 'support', 'service', 'led', 'export', 'international']


def is_fake_email(email):
    el = email.lower()
    for kw in FAKE_KEYWORDS:
        if kw in el:
            return True
    return False


def is_generic_freemail(email):
    domain = email.split('@')[-1].lower()
    return domain in GENERIC_FREEMAIL


def get_domain(website):
    parsed = urlparse(website)
    return (parsed.netloc or parsed.path).lstrip('www.')


def get_base_url(website):
    parsed = urlparse(website)
    scheme = parsed.scheme or 'https'
    netloc = parsed.netloc or parsed.path
    return f"{scheme}://{netloc}"


def fetch_jina(url, timeout=25):
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
            return content.decode('utf-8', errors='replace'), None
    except urllib.error.HTTPError as e:
        return None, e.code
    except Exception as e:
        return None, str(e)


def score_email(email, domain):
    el = email.lower()
    ed = el.split('@')[-1]
    score = 0
    domain_clean = domain.replace('www.', '').lower()
    if domain_clean and ed == domain_clean:
        score += 10
    elif domain_clean and domain_clean in ed:
        score += 5
    prefix = el.split('@')[0]
    for i, p in enumerate(PRIORITY_PREFIXES):
        if prefix == p:
            score += (8 - i)
            break
        elif prefix.startswith(p):
            score += max(0, 4 - i)
            break
    if is_generic_freemail(email):
        score -= 5
    return score


def extract_best_emails(text, domain):
    if not text:
        return []
    found = EMAIL_REGEX.findall(text)
    seen = {}
    for e in found:
        k = e.lower()
        if k not in seen:
            seen[k] = e
    candidates = [e for e in seen.values() if not is_fake_email(e)]
    candidates.sort(key=lambda e: score_email(e, domain), reverse=True)
    return candidates


def needs_email(record):
    if record.get('country') != 'Korea':
        return False
    if record.get('status') != 'prospect':
        return False
    website = record.get('website', '')
    if not website:
        return False
    email = record.get('email', '')
    if email and not is_fake_email(email):
        return False  # Already has real email
    return True


def get_netloc(website):
    parsed = urlparse(website)
    return (parsed.netloc or parsed.path).lstrip('www.')


def scrape_record(record):
    website = record['website']
    domain = get_domain(website)
    netloc = get_netloc(website)

    # Skip sites known to return 422
    if netloc in SKIP_STATUS_422 or netloc.replace('www.', '') in SKIP_STATUS_422:
        print(f"  [SKIP] Known 422 site: {netloc}")
        return '', []

    base = get_base_url(website)

    # Try alternative contact page patterns for Korean sites
    urls_to_try = [
        website,
        base.rstrip('/') + '/contact',
        base.rstrip('/') + '/about',
        base.rstrip('/') + '/contactus',
        base.rstrip('/') + '/company',
    ]

    all_candidates = []
    consecutive_429 = 0

    for url in urls_to_try:
        print(f"  Fetching: {url}")
        text, err = fetch_jina(url)
        if text:
            consecutive_429 = 0
            emails = extract_best_emails(text, domain)
            if emails:
                print(f"    Found {len(emails)} candidate(s): {emails[:3]}")
            all_candidates.extend(emails)
        else:
            if err == 429:
                consecutive_429 += 1
                print(f"  [429] Rate limited")
                if consecutive_429 >= 2:
                    print(f"  [ABORT] Too many 429s, sleeping 60s then continuing")
                    time.sleep(60)
                    consecutive_429 = 0
            elif err == 422:
                print(f"  [422] Jina can't process this site")
                break  # No point retrying other pages for this site
            else:
                print(f"  [WARN] Error: {err}")
        time.sleep(3)  # 3s = ~20 RPM max

    seen = {}
    for e in all_candidates:
        k = e.lower()
        if k not in seen:
            seen[k] = e
    unique = list(seen.values())
    unique.sort(key=lambda e: score_email(e, domain), reverse=True)

    best = unique[0] if unique else ''
    return best, unique


def main():
    print(f"Loading {PROSPECTS_FILE}")
    with open(PROSPECTS_FILE, 'r', encoding='utf-8') as f:
        prospects = json.load(f)

    targets = [r for r in prospects if needs_email(r)]
    print(f"\nRound 2 targets: {len(targets)} Korea prospects still missing email\n")

    found_count = 0
    updated_nos = []

    for i, record in enumerate(targets):
        no = record.get('no', '?')
        company = record.get('company_en', '?')
        website = record.get('website', '')
        print(f"\n[{i+1}/{len(targets)}] #{no} {company} — {website}")

        best_email, candidates = scrape_record(record)

        if best_email:
            print(f"  => Best email: {best_email}")
            record['email'] = best_email
            record['email_candidates'] = candidates
            found_count += 1
            updated_nos.append(no)
        else:
            print(f"  => No email found")
            if 'email' not in record:
                record['email'] = ''
            if 'email_candidates' not in record:
                record['email_candidates'] = []

    with open(PROSPECTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(prospects, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"SUMMARY Round 2: Found {found_count} new emails out of {len(targets)} targets")
    if updated_nos:
        print(f"Updated records: #{', #'.join(str(n) for n in updated_nos)}")
    print(f"Saved to {PROSPECTS_FILE}")


if __name__ == '__main__':
    main()
