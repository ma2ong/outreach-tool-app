"""
generate_led_leads_v48.py
New entries: nos 699-704 (6 USA leads)
Cities: Meridian ID / Boise ID / Tucson AZ / Chattanooga TN / Spokane WA / Greenville SC
"""
import ast, re, os

_base = os.path.dirname(__file__)

def _load(path):
    return open(path, encoding="utf-8").read()

_v4_src = _load(os.path.join(_base, "generate_led_leads_v4.py"))
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", _v4_src, re.M | re.S).group(1))

for _vname in ("v5","v6","v7","v8","v9","v10","v11","v12","v13","v14","v15","v16",
               "v17","v18","v19","v20","v21","v22","v23","v24","v25","v26","v27",
               "v28","v29","v30","v31","v32","v33","v34","v35","v36","v37","v38",
               "v39","v40","v41","v42","v43","v44","v45","v46","v47"):
    _path = os.path.join(_base, f"generate_led_leads_{_vname}.py")
    if not os.path.exists(_path):
        continue
    _src = _load(_path)
    _m = re.search(r"^new_entries = (\[.+?^\])", _src, re.M | re.S)
    if _m:
        leads.extend(ast.literal_eval(_m.group(1)))

new_entries = [
    {
        "no": 699,
        "country": "USA",
        "region": "Americas",
        "company_en": "Rocky Mountain Roll",
        "company_local": "",
        "city": "Meridian, ID",
        "contact_name": "",
        "title": "",
        "email": "Sales@rockymountainroll.com",
        "phone_whatsapp": "",
        "website": "https://rockymountainroll.com",
        "business": "Boise-area AV rental company (est. 1981) offering LED video wall, audio, lighting and staging for corporate events, concerts and outdoor festivals across Idaho. Instagram @rockymountainroll",
        "facebook": "",
        "instagram": "rockymountainroll",
        "linkedin": "",
    },
    {
        "no": 700,
        "country": "USA",
        "region": "Americas",
        "company_en": "Rocky Mountain Audio Visual",
        "company_local": "",
        "city": "Boise, ID",
        "contact_name": "",
        "title": "",
        "email": "rentals@rmav.com",
        "phone_whatsapp": "",
        "website": "https://rmav.com",
        "business": "One of Idaho's largest AV service providers offering LED large-screen display solutions for conferences, trade shows, and concerts across the Pacific Northwest.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 701,
        "country": "USA",
        "region": "Americas",
        "company_en": "Arizona Mobile Media",
        "company_local": "",
        "city": "Tucson, AZ",
        "contact_name": "",
        "title": "",
        "email": "info@azmobilemedia.net",
        "phone_whatsapp": "",
        "website": "https://azmobilemedia.net",
        "business": "Arizona mobile LED screen rental company providing high-resolution outdoor trailer-mounted LED screens and live camera production for music festivals and corporate events statewide.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 702,
        "country": "USA",
        "region": "Americas",
        "company_en": "Seals Productions",
        "company_local": "",
        "city": "Chattanooga, TN",
        "contact_name": "Kendall Seals",
        "title": "",
        "email": "sealsproductions7@gmail.com",
        "phone_whatsapp": "",
        "website": "https://sealsproductions.com",
        "business": "Chattanooga AV rental and event production company offering LED displays, lighting, audio, and staging for local events. Instagram @sealsproductions",
        "facebook": "",
        "instagram": "sealsproductions",
        "linkedin": "",
    },
    {
        "no": 703,
        "country": "USA",
        "region": "Americas",
        "company_en": "AMPD Lighting and Audio Visual",
        "company_local": "",
        "city": "Spokane, WA",
        "contact_name": "",
        "title": "",
        "email": "Sales@ampdspokane.com",
        "phone_whatsapp": "",
        "website": "https://ampdspokane.com",
        "business": "Pacific Northwest premium AV rental company with 30x10ft LED video wall, serving concerts, corporate events, sports, and church productions across WA/ID. Instagram @ampdlightingaudiovisual",
        "facebook": "",
        "instagram": "ampdlightingaudiovisual",
        "linkedin": "",
    },
    {
        "no": 704,
        "country": "USA",
        "region": "Americas",
        "company_en": "AVL Solutions",
        "company_local": "",
        "city": "Greenville, SC",
        "contact_name": "",
        "title": "",
        "email": "info@avlsusa.com",
        "phone_whatsapp": "",
        "website": "https://avlsusa.com",
        "business": "Greenville SC AV company (20+ years) offering outdoor mobile LED screen rental (4.8mm weatherproof) for music festivals, graduations, drive-in events, and corporate productions. Instagram @avl_solutions",
        "facebook": "",
        "instagram": "avl_solutions",
        "linkedin": "",
    },
]

leads.extend(new_entries)

if __name__ == "__main__":
    usa = [l for l in leads if l.get("country") == "USA"]
    print(f"v48: {len(new_entries)} new entries, nos {new_entries[0]['no']}-{new_entries[-1]['no']}")
    print(f"Total: {len(leads)}, USA: {len(usa)}")
