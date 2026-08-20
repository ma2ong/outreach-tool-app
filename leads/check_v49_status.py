import json

data = json.load(open("pipeline/email/prospects.json", encoding="utf-8"))
usa49 = [p for p in data if p.get("no") in range(705, 715)]
print(f"v49 in email pipeline: {len(usa49)}")
for p in usa49:
    no = p["no"]
    co = p.get("company_en", "")
    st = p.get("status", "")
    sd = p.get("email_sent_date", "")
    print(f"  no={no} {co} status={st} sent={sd}")

print()
ig = json.load(open("pipeline/instagram/prospects.json", encoding="utf-8"))
v49_users = ["tsvusa", "soflostudio", "mastersoundpro", "mediaquestpgh", "allproaudiovisual", "vegaseventgroup"]
print("v49 in IG pipeline:")
found = []
for p in ig:
    u = p.get("username") or p.get("instagram", "")
    if u in v49_users:
        warmup = p.get("warmup_done")
        status = p.get("status")
        dm_sent = p.get("dm_sent_date", "")
        print(f"  @{u} status={status} warmup={warmup} dm_sent={dm_sent}")
        found.append(u)
missing = [u for u in v49_users if u not in found]
if missing:
    print(f"  NOT IN PIPELINE: {missing}")

print()
wa = json.load(open("pipeline/whatsapp/prospects.json", encoding="utf-8"))
usa_wa = [p for p in wa if p.get("country") == "USA"]
print(f"USA in WA pipeline: {len(usa_wa)}")
for p in usa_wa[:10]:
    no = p["no"]
    co = p.get("company_en", "")
    st = p.get("status", "")
    ph = p.get("phone_whatsapp", "") or p.get("phone", "")
    print(f"  no={no} {co} status={st} phone={ph}")
