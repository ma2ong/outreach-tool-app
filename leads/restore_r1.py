"""
Restore round 1 results that were overwritten.
Also record all emails found in round 2.
"""
import json

PROSPECTS_FILE = r'C:\Users\Administrator\ai-topic-generator\output\leads\pipeline\whatsapp\prospects.json'

# Round 1 confirmed finds (from log)
R1_EMAILS = {
    169: {'email': 'sales@raonvisual.co.kr', 'email_candidates': ['sales@raonvisual.co.kr', 'tech@raonvisual.co.kr']},
    183: {'email': 'bandyled@bandyled.com', 'email_candidates': ['bandyled@bandyled.com']},
    300: {'email': 'led@cudo.kr', 'email_candidates': ['led@cudo.kr', 'hhj7518@cudo.co.kr']},
}

with open(PROSPECTS_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

restored = 0
for r in data:
    no = r.get('no')
    if no in R1_EMAILS:
        if not r.get('email') or not r.get('email', '').strip():
            print(f"Restoring #{no} {r.get('company_en')}: {R1_EMAILS[no]['email']}")
            r['email'] = R1_EMAILS[no]['email']
            r['email_candidates'] = R1_EMAILS[no]['email_candidates']
            restored += 1
        else:
            print(f"#{no} already has email: {r.get('email')} (no change)")

with open(PROSPECTS_FILE, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\nRestored {restored} records")
