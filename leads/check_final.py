"""Final summary of Jina email scraping results for Korea prospects."""
import json

PROSPECTS_FILE = r'C:\Users\Administrator\ai-topic-generator\output\leads\pipeline\whatsapp\prospects.json'
FAKE_KW = ['wixpress', 'sentry', 'example', 'placeholder']
NAVER_KAKAO = ['naver.com', 'kakao.com']
FREEMAIL = ['gmail.com', 'yahoo.com', 'hotmail.com', 'daum.net', 'hanmail.net']

def is_fake(e): return any(k in e.lower() for k in FAKE_KW)
def is_naver_kakao(e): return e.lower().split('@')[-1] in NAVER_KAKAO
def is_freemail(e): return e.lower().split('@')[-1] in FREEMAIL
def is_company_email(e): return not is_fake(e) and not is_naver_kakao(e) and not is_freemail(e)

with open(PROSPECTS_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

korea = [r for r in data if r.get('country') == 'Korea']
prospects = [r for r in korea if r.get('status') == 'prospect']

company_emails = [r for r in korea if r.get('email') and is_company_email(r['email'])]
naver_emails = [r for r in korea if r.get('email') and is_naver_kakao(r['email'])]
all_with_email = [r for r in korea if r.get('email') and not is_fake(r['email'])]

print('=== KOREA EMAIL SCRAPING FINAL SUMMARY ===')
print()
print(f'Total Korea records: {len(korea)}')
print(f'Korea prospects: {len(prospects)}')
print()
print(f'Company domain emails (best quality): {len(company_emails)}')
for r in company_emails:
    status = r.get("status", "?")
    print(f'  #{r["no"]} {r["company_en"]} ({status}) -> {r["email"]}')
print()
print(f'Naver/Kakao emails (usable but generic): {len(naver_emails)}')
for r in naver_emails:
    status = r.get("status", "?")
    print(f'  #{r["no"]} {r["company_en"]} ({status}) -> {r["email"]}')
print()

prospects_no_email = [r for r in prospects if not r.get('email') or is_fake(r.get('email', ''))]
prospects_with_website_no_email = [r for r in prospects_no_email if r.get('website')]
print(f'Prospects still without any email: {len(prospects_no_email)}')
print(f'  of which have website (Jina could retry): {len(prospects_with_website_no_email)}')
