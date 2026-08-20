"""
Debug: test Jina fetch for one site and see what emails come back.
"""
import re
import urllib.request
import time

EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,6}')

FAKE_KEYWORDS = ['wixpress', 'sentry', 'example', 'placeholder']

def fetch_jina(url, timeout=20):
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
        print(f"  FAIL: {e}")
        return None

# Test a few sites
test_sites = [
    'https://rgbkorea.com',
    'https://www.primemedia.co.kr',
    'https://tagsolution.kr',
    'https://mpartners.co.kr',
    'https://www.vissem.com',
]

for site in test_sites:
    print(f"\n=== {site} ===")
    text = fetch_jina(site)
    if text:
        # Show first 500 chars
        print("CONTENT PREVIEW:", text[:500])
        emails = EMAIL_REGEX.findall(text)
        print(f"ALL EMAILS FOUND ({len(emails)}):", emails[:20])
    time.sleep(1)
