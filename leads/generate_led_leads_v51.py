"""
generate_led_leads_v51.py
New entries: nos 723-729 (7 USA leads)
Cities: Nashua NH / Wichita KS / West Columbia SC /
        Waipahu HI / Aiea HI / Kailua-Kona HI / Albuquerque NM
Note: All companies verified — LED display rental, sales or integration.
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
               "v39","v40","v41","v42","v43","v44","v45","v46","v47","v48","v49","v50"):
    _path = os.path.join(_base, f"generate_led_leads_{_vname}.py")
    if not os.path.exists(_path):
        continue
    _src = _load(_path)
    _m = re.search(r"^new_entries = (\[.+?^\])", _src, re.M | re.S)
    if _m:
        leads.extend(ast.literal_eval(_m.group(1)))

new_entries = [
    {
        "no": 723,
        "country": "USA",
        "region": "Americas",
        "company_en": "MLD Lighting",
        "company_local": "",
        "city": "Nashua, NH",
        "contact_name": "",
        "title": "",
        "email": "contact@mldlighting.com",
        "phone_whatsapp": "603-235-9336",
        "website": "mldlighting.com",
        "business": "LED video wall design, rental and installation serving New England; corporate events, trade shows, concerts. Instagram @mldlighting",
        "facebook": "",
        "instagram": "mldlighting",
        "linkedin": "",
    },
    {
        "no": 724,
        "country": "USA",
        "region": "Americas",
        "company_en": "Relevant Audio + Visual",
        "company_local": "",
        "city": "Wichita, KS",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "316-252-1153",
        "website": "relevantav.com",
        "business": "LED video wall rental and AV production in Wichita and surrounding Kansas/Oklahoma region; events, concerts, corporate. Instagram @relevant_av; Facebook relevantaudiovisual",
        "facebook": "relevantaudiovisual",
        "instagram": "relevant_av",
        "linkedin": "",
    },
    {
        "no": 725,
        "country": "USA",
        "region": "Americas",
        "company_en": "SCAV South Carolina AV",
        "company_local": "",
        "city": "West Columbia, SC",
        "contact_name": "",
        "title": "",
        "email": "rental@scav.com",
        "phone_whatsapp": "803-227-2981",
        "website": "scav.com",
        "business": "LED video wall rental and full AV production; preferred vendor at Columbia Metropolitan Convention Center. Serves Carolinas. Instagram @scav_sc",
        "facebook": "",
        "instagram": "scav_sc",
        "linkedin": "",
    },
    {
        "no": 726,
        "country": "USA",
        "region": "Americas",
        "company_en": "Theatrix Hawaii",
        "company_local": "",
        "city": "Waipahu, HI",
        "contact_name": "",
        "title": "",
        "email": "info@theatrix.com",
        "phone_whatsapp": "808-836-5647",
        "website": "theatrix.com",
        "business": "LED video wall rental and full production services for events across Oahu and Maui; corporate events, concerts, trade shows. Also serves Maui location.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 727,
        "country": "USA",
        "region": "Americas",
        "company_en": "OnStage Hawaii",
        "company_local": "",
        "city": "Aiea, HI",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "808-570-0088",
        "website": "onstagehavaii.com",
        "business": "LED wall rental for events across Hawaii; 40+ years combined AV experience. Oahu-based serving all islands.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 728,
        "country": "USA",
        "region": "Americas",
        "company_en": "AVS Audio Visual Services Hawaii",
        "company_local": "",
        "city": "Kailua-Kona, HI",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "808-331-8403",
        "website": "avshawaii.com",
        "business": "LED video wall rental and full AV production; locations on Kailua-Kona (Big Island), Maui, and Oahu. Events, conferences, concerts.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 729,
        "country": "USA",
        "region": "Americas",
        "company_en": "Document Solutions Inc (DSI NM)",
        "company_local": "",
        "city": "Albuquerque, NM",
        "contact_name": "",
        "title": "",
        "email": "info@dsinm.com",
        "phone_whatsapp": "888-386-7834",
        "website": "dsinm.com",
        "business": "LED video wall sales and white-glove installation across 8 New Mexico locations plus El Paso TX; OneScreen and commercial LED displays. Instagram @documentsolutionsinc",
        "facebook": "",
        "instagram": "documentsolutionsinc",
        "linkedin": "",
    },
]

leads.extend(new_entries)

if __name__ == "__main__":
    usa = [l for l in leads if l.get("country") == "USA"]
    print(f"Total leads: {len(leads)} | USA: {len(usa)}")
    print(f"New entries this batch: {len(new_entries)} (nos {new_entries[0]['no']}–{new_entries[-1]['no']})")
    for e in new_entries:
        print(f"  {e['no']:>3}. {e['company_en']:<40} {e['city']}")
