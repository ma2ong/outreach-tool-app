"""
LED Leads v46 — USA batch
Cities: Peoria AZ (Phoenix metro) x2, Denver CO, Cincinnati/Indianapolis OH/IN,
        Ridgeville OH (Cleveland), Altamonte Springs FL (Orlando)
"""
import ast, re, os, json
from pathlib import Path

BASE = Path(__file__).parent

# --- chain load all previous entries ---
_v4_src = open(BASE / "generate_led_leads_v4.py", encoding="utf-8").read()
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", _v4_src, re.M | re.S).group(1))
for _vname in ("v5","v6","v7","v8","v9","v10","v11","v12","v13","v14","v15","v16",
               "v17","v18","v19","v20","v21","v22","v23","v24","v25","v26","v27",
               "v28","v29","v30","v31","v32","v33","v34","v35","v36","v37","v38",
               "v39","v40","v41","v42","v43","v44","v45"):
    _p = BASE / f"generate_led_leads_{_vname}.py"
    if not _p.exists(): continue
    _src = open(_p, encoding="utf-8").read()
    _m = re.search(r"^new_entries = (\[.+?^\])", _src, re.M | re.S)
    if _m: leads.extend(ast.literal_eval(_m.group(1)))

new_entries = [
    {
        "no": 686,
        "country": "USA",
        "region": "Americas",
        "company_en": "Xperience Entertainment",
        "company_local": "",
        "city": "Peoria, AZ",
        "contact_name": "",
        "title": "",
        "email": "info@readytoxperience.com",
        "phone_whatsapp": "602-834-0824",
        "website": "readytoxperience.com",
        "business": "LED video wall rental (2.9mm indoor / 3.9mm outdoor) for corporate events, trade shows, concerts in Greater Phoenix area. Instagram @xperienceent (1,989 followers); email confirmed from website readytoxperience.com",
        "facebook": "",
        "instagram": "xperienceent",
        "linkedin": "",
    },
    {
        "no": 687,
        "country": "USA",
        "region": "Americas",
        "company_en": "Denver Video Wall",
        "company_local": "",
        "city": "Denver, CO",
        "contact_name": "",
        "title": "",
        "email": "hello@denvervideowall.com",
        "phone_whatsapp": "",
        "website": "denvervideowall.com",
        "business": "LED screen rental company serving Denver/Boulder/Colorado Springs. Offers conference LED screens, curved/special shaped LED, mobile LED trailers, mobile billboard vans, kiosk displays, LED posters. All events types. Email confirmed from website denvervideowall.com",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 688,
        "country": "USA",
        "region": "Americas",
        "company_en": "Midwest Audio Visual",
        "company_local": "",
        "city": "Cincinnati, OH",
        "contact_name": "",
        "title": "",
        "email": "info@midwestaudiovisual.com",
        "phone_whatsapp": "",
        "website": "midwestaudiovisual.com",
        "business": "AV systems integrator covering Ohio, Kentucky, Indiana. Services include digital signage and video wall installation, sports venues (gymnasium/stadium), performance venues, auditoriums. Clients in Cincinnati, Columbus, Dayton, Indianapolis. Email confirmed from website midwestaudiovisual.com",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 689,
        "country": "USA",
        "region": "Americas",
        "company_en": "Phoenix LED Screens",
        "company_local": "",
        "city": "Phoenix, AZ",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "480-787-0067",
        "website": "phoenixledscreens.com",
        "business": "LED screen and video wall rental for churches, trade shows, corporate events, weddings, concerts. Serves 20+ cities across Greater Phoenix metro. Instagram @phoenixledscreens; phone confirmed from website phoenixledscreens.com",
        "facebook": "",
        "instagram": "phoenixledscreens",
        "linkedin": "",
    },
    {
        "no": 690,
        "country": "USA",
        "region": "Americas",
        "company_en": "Lime Lights Entertainment",
        "company_local": "",
        "city": "Ridgeville, OH",
        "contact_name": "",
        "title": "",
        "email": "contactus@limelightsent.com",
        "phone_whatsapp": "216-543-8157",
        "website": "limelightsent.com",
        "business": "Full-service entertainment company in Cleveland area offering LED video wall rental (10ft–30ft screens) for weddings, corporate events, trade shows, school events. Also provides DJ/MC, lighting, special effects. Instagram @limelightsentertain; email confirmed from website limelightsent.com",
        "facebook": "",
        "instagram": "limelightsentertain",
        "linkedin": "",
    },
    {
        "no": 691,
        "country": "USA",
        "region": "Americas",
        "company_en": "MTI Sound",
        "company_local": "",
        "city": "Altamonte Springs, FL",
        "contact_name": "",
        "title": "",
        "email": "contact@mtisound.com",
        "phone_whatsapp": "(407) 330-0906",
        "website": "mtisound.com",
        "business": "Stage, lighting and LED wall rental company serving Orlando and Florida. Services include LED wall rental, audio visual, event lighting, event staging, concert structures, event production. Instagram @mtisoundlighting; email confirmed from website mtisound.com",
        "facebook": "",
        "instagram": "mtisoundlighting",
        "linkedin": "",
    },
]

# print summary
existing = {(l.get("no"), l.get("company_en")) for l in leads}
added = [e for e in new_entries if e["no"] not in {no for no, _ in existing}]
print(f"v46: {len(added)} new entries, nos {added[0]['no']}-{added[-1]['no']}")
print(f"Total after v46: {len(leads) + len(added)}")
usa = [l for l in leads + added if l.get("country") == "USA"]
print(f"USA total: {len(usa)}")
for e in added:
    ig = f"@{e['instagram']}" if e.get("instagram") else "no IG"
    email = e.get("email") or "no email"
    print(f"  {e['no']} {e['company_en']} ({e['city']}) {ig} {email}")
