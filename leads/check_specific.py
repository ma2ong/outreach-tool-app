import json
with open(r'C:\Users\Administrator\ai-topic-generator\output\leads\pipeline\whatsapp\prospects.json', encoding='utf-8') as f:
    data = json.load(f)

# Check specific records
target_nos = [169, 183, 300]
for r in data:
    if r.get('no') in target_nos:
        print('No:', r.get('no'))
        print('Company:', r.get('company_en'))
        print('Status:', r.get('status'))
        print('Email:', repr(r.get('email', '')))
        print('Candidates:', r.get('email_candidates', []))
        print()

# Also show all Korea records with email
print('--- ALL KOREA WITH EMAIL ---')
for r in data:
    if r.get('country') == 'Korea' and r.get('email','') and 'wixpress' not in r.get('email','') and 'sentry' not in r.get('email',''):
        print(f"#{r.get('no')} {r.get('company_en')} ({r.get('status')}) -> {r.get('email')}")
