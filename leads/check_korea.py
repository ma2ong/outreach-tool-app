import json
with open(r'C:\Users\Administrator\ai-topic-generator\output\leads\pipeline\whatsapp\prospects.json', encoding='utf-8') as f:
    data = json.load(f)
korea = [r for r in data if r.get('country') == 'Korea']
prospects = [r for r in korea if r.get('status') == 'prospect']
with_email = [r for r in korea if r.get('email','') and 'wixpress' not in r.get('email','') and 'sentry' not in r.get('email','')]
no_email = [r for r in prospects if not r.get('email','') or 'wixpress' in r.get('email','') or 'sentry' in r.get('email','')]
print('Total Korea:', len(korea))
print('Korea with real email:', len(with_email))
print('Korea prospects:', len(prospects))
print('Korea prospects still missing email:', len(no_email))
print()
print('Prospects missing email:')
for r in no_email:
    no = r.get('no', '?')
    name = r.get('company_en', '?')
    site = r.get('website', '')
    print('  #' + str(no) + ' ' + name + ' - ' + site)
