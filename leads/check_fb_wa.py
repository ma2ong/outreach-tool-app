import json

# FB pipeline
fb = json.load(open("pipeline/facebook/prospects.json", encoding="utf-8"))
usa_fb = [p for p in fb if p.get("country") == "USA"]
print(f"USA in FB pipeline: {len(usa_fb)}")
for p in usa_fb[:20]:
    st = p.get("status", "")
    fb_handle = p.get("facebook", "")
    co = p.get("company_en", "")
    no = p["no"]
    print(f"  no={no} {co} fb=@{fb_handle} status={st}")

print()
# WA pipeline - check USA prospects not yet messaged
wa = json.load(open("pipeline/whatsapp/prospects.json", encoding="utf-8"))
usa_wa_prospect = [p for p in wa if p.get("country") == "USA" and p.get("status") == "prospect"]
print(f"USA WA prospects (not yet sent): {len(usa_wa_prospect)}")
for p in usa_wa_prospect[:20]:
    no = p["no"]
    co = p.get("company_en", "")
    ph = p.get("phone_whatsapp", "") or p.get("phone", "")
    print(f"  no={no} {co} phone={ph}")

print()
usa_wa_all = [p for p in wa if p.get("country") == "USA"]
messaged = len([p for p in usa_wa_all if p.get("status") == "messaged"])
excluded = len([p for p in usa_wa_all if p.get("status") == "excluded"])
print(f"USA WA total={len(usa_wa_all)} messaged={messaged} excluded={excluded}")
