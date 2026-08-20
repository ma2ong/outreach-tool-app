"""
LED Leads v45 — USA batch
Cities: Hurricane UT, Gahanna OH (Columbus), Nashville TN, Charlton MA (Boston area),
        Birmingham AL, San Jose CA, Oklahoma City OK x2, Detroit MI, Providence RI
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
               "v39","v40","v41","v42","v43","v44"):
    _p = BASE / f"generate_led_leads_{_vname}.py"
    if not _p.exists(): continue
    _src = open(_p, encoding="utf-8").read()
    _m = re.search(r"^new_entries = (\[.+?^\])", _src, re.M | re.S)
    if _m: leads.extend(ast.literal_eval(_m.group(1)))

new_entries = [
    {
        "no": 676,
        "country": "USA",
        "region": "Americas",
        "company_en": "Final Design Group",
        "company_local": "",
        "city": "Hurricane, UT",
        "contact_name": "",
        "title": "",
        "email": "SWLemmon@fdgtv.com",
        "phone_whatsapp": "",
        "website": "fdgtv.com",
        "business": "Mobile LED video wall and large screen rental for major touring events including Monster Jam, Supercross, Red Bull Racing. National service. Instagram @finaldesigngroup (empty/inactive). Email confirmed from website fdgtv.com",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 677,
        "country": "USA",
        "region": "Americas",
        "company_en": "The Penn Group",
        "company_local": "",
        "city": "Gahanna, OH",
        "contact_name": "",
        "title": "",
        "email": "sales@thepenn.group",
        "phone_whatsapp": "+1 614-741-5306",
        "website": "thepenn.group",
        "business": "Audio, Video, Lighting, Integration system integrator and LED video wall rental company serving Columbus, Cincinnati, and nationwide. 500+ service locations. Instagram @thepenn.group (141 followers, 5 posts); email confirmed from website thepenn.group",
        "facebook": "",
        "instagram": "thepenn.group",
        "linkedin": "",
    },
    {
        "no": 678,
        "country": "USA",
        "region": "Americas",
        "company_en": "Concept Pixels",
        "company_local": "",
        "city": "Nashville, TN",
        "contact_name": "",
        "title": "",
        "email": "info@conceptpixels.com",
        "phone_whatsapp": "",
        "website": "conceptpixels.com",
        "business": "LED video wall rental using ROE panels for Nashville and LA events. State-of-the-art LED wall configurations for corporate events, concerts, trade shows; expert installation and on-site support. Instagram @conceptpixels; email confirmed from website conceptpixels.com",
        "facebook": "",
        "instagram": "conceptpixels",
        "linkedin": "",
    },
    {
        "no": 679,
        "country": "USA",
        "region": "Americas",
        "company_en": "Supreme AV",
        "company_local": "",
        "city": "Charlton, MA",
        "contact_name": "Shane",
        "title": "",
        "email": "Shane@supremeav.net",
        "phone_whatsapp": "508-320-5426",
        "website": "supremeav.net",
        "business": "Full-service AV rental and event production serving Boston, Worcester, Providence, and all New England. LED video walls, sound, lighting, staging. 20+ years in business. Instagram @supreme_av; email confirmed from website supremeav.net",
        "facebook": "",
        "instagram": "supreme_av",
        "linkedin": "",
    },
    {
        "no": 680,
        "country": "USA",
        "region": "Americas",
        "company_en": "Moon Men DJs",
        "company_local": "",
        "city": "Birmingham, AL",
        "contact_name": "",
        "title": "",
        "email": "info@moonmenonline.com",
        "phone_whatsapp": "1-205-565-8654",
        "website": "moonmendjs.com",
        "business": "Virtual production studio in Birmingham with LED Volume for Unreal Engine 3D virtual environments, film production, live events. Giant LED Volume as core studio asset. Instagram @moonmendjs (396 followers, 109 posts); email confirmed from website moonmendjs.com",
        "facebook": "",
        "instagram": "moonmendjs",
        "linkedin": "",
    },
    {
        "no": 681,
        "country": "USA",
        "region": "Americas",
        "company_en": "A1 Visuals",
        "company_local": "",
        "city": "San Jose, CA",
        "contact_name": "",
        "title": "",
        "email": "A1visualevents@gmail.com",
        "phone_whatsapp": "(408) 409-8354",
        "website": "sanjoseledscreen.com",
        "business": "LED video wall rental company with 9+ years in San Jose, serving all of California. Services include LED video wall, intelligent lighting, LED dance floor, audio. Instagram @a1_visuals_ (~24K followers); email confirmed from Google/Yelp listing",
        "facebook": "",
        "instagram": "a1_visuals_",
        "linkedin": "",
    },
    {
        "no": 682,
        "country": "USA",
        "region": "Americas",
        "company_en": "Myx Productions",
        "company_local": "",
        "city": "Oklahoma City, OK",
        "contact_name": "",
        "title": "",
        "email": "info@myxproductions.com",
        "phone_whatsapp": "(405) 922-1896",
        "website": "myxproductions.com",
        "business": "Full-service event production and AV rental in Oklahoma City. Provides LED video wall, professional audio, lighting, stage, projection for corporate and private events. Instagram @myxproductions (400 followers); email confirmed from website myxproductions.com",
        "facebook": "",
        "instagram": "myxproductions",
        "linkedin": "",
    },
    {
        "no": 683,
        "country": "USA",
        "region": "Americas",
        "company_en": "Dizplay Inc",
        "company_local": "",
        "city": "Detroit, MI",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "(888) 827-8774",
        "website": "dizplayrentals.com",
        "business": "LED video wall rental, sales, and installation company covering Detroit, LA, Las Vegas, San Diego, Phoenix. Services concerts, corporate events, weddings, esports. Instagram @dizplayinc (271 followers); phone confirmed from website dizplayrentals.com",
        "facebook": "",
        "instagram": "dizplayinc",
        "linkedin": "",
    },
    {
        "no": 684,
        "country": "USA",
        "region": "Americas",
        "company_en": "Cory's AV Solutions",
        "company_local": "",
        "city": "Oklahoma City, OK",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "(405) 682-8800",
        "website": "corys.pro",
        "business": "Oklahoma's first full-service AV solutions provider. Live events, system integration, technology maintenance. Mobile LED screen rentals confirmed. Instagram @corysconnects (1,108 followers); phone confirmed from website corys.pro",
        "facebook": "",
        "instagram": "corysconnects",
        "linkedin": "",
    },
    {
        "no": 685,
        "country": "USA",
        "region": "Americas",
        "company_en": "Event Expert",
        "company_local": "",
        "city": "Providence, RI",
        "contact_name": "",
        "title": "",
        "email": "hello@eventexpert.io",
        "phone_whatsapp": "",
        "website": "eventexpert.io",
        "business": "Full-service corporate event production with 20+ years. LED video wall rental, stage design, audio-visual, hybrid events. Global service including Providence and major US cities. Email confirmed from website eventexpert.io",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
]

# print summary
existing = {(l.get("no"), l.get("company_en")) for l in leads}
added = [e for e in new_entries if e["no"] not in {no for no, _ in existing}]
print(f"v45: {len(added)} new entries, nos {added[0]['no']}-{added[-1]['no']}")
print(f"Total after v45: {len(leads) + len(added)}")
usa = [l for l in leads + added if l.get("country") == "USA"]
print(f"USA total: {len(usa)}")
for e in added:
    ig = f"@{e['instagram']}" if e.get("instagram") else "no IG"
    email = e.get("email") or "no email"
    print(f"  {e['no']} {e['company_en']} ({e['city']}) {ig} {email}")
