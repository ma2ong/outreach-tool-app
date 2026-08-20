"""
generate_led_leads_v53.py
New entries: nos 738-745 (8 leads: Mexico + Chile)
Mexico: Servittec (CDMX), PROLED (Guadalajara), Luas Sound (Guadalajara),
        ABK Lighting (CDMX), Troya Eventos (Monterrey), Doppmedia (Puebla),
        GDLED (Guadalajara)
Chile: StageCore (Santiago)
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
               "v39","v40","v41","v42","v43","v44","v45","v46","v47","v48","v49","v50","v51","v52"):
    _path = os.path.join(_base, f"generate_led_leads_{_vname}.py")
    if not os.path.exists(_path):
        continue
    _src = _load(_path)
    _m = re.search(r"^new_entries = (\[.+?^\])", _src, re.M | re.S)
    if _m:
        leads.extend(ast.literal_eval(_m.group(1)))

new_entries = [
    {
        "no": 738,
        "country": "Mexico",
        "region": "Americas",
        "company_en": "Servittec Audiovisual",
        "company_local": "Servittec Audiovisual",
        "city": "Mexico City, CDMX",
        "contact_name": "",
        "title": "",
        "email": "servittec@servittecaudiovisual.com.mx",
        "phone_whatsapp": "+52 55 1547-1265",
        "website": "servittecaudiovisual.com.mx",
        "business": "LED screen rental for corporate events and audio-visual solutions in CDMX; also serves nationwide. Phone confirmed from website.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 739,
        "country": "Mexico",
        "region": "Americas",
        "company_en": "PROLED Guadalajara",
        "company_local": "PROLED",
        "city": "Guadalajara, JAL",
        "contact_name": "Jorge Hernandez",
        "title": "Rentals",
        "email": "Jorgeibarrah@proled.com.mx",
        "phone_whatsapp": "+52 332-733-7524",
        "website": "proled.com.mx",
        "business": "LED screen rental, sales, installation and event design in Guadalajara; 15+ years; also serves CDMX and Monterrey. IG @proledgdl (confirmed). WA: 332-733-7524 (GDL mobile).",
        "facebook": "",
        "instagram": "proledgdl",
        "linkedin": "",
    },
    {
        "no": 740,
        "country": "Mexico",
        "region": "Americas",
        "company_en": "Luas Sound Events",
        "company_local": "Luas Sound Events",
        "city": "Guadalajara, JAL",
        "contact_name": "",
        "title": "",
        "email": "info@luaseventos.com.mx",
        "phone_whatsapp": "+52 333-476-4230",
        "website": "luaseventos.com.mx",
        "business": "LED screen rental, video mapping, live streaming for events in Guadalajara. IG @luas_sound. WA: 3334764230 (GDL mobile confirmed).",
        "facebook": "",
        "instagram": "luas_sound",
        "linkedin": "",
    },
    {
        "no": 741,
        "country": "Mexico",
        "region": "Americas",
        "company_en": "ABK Lighting Mexico",
        "company_local": "ABK",
        "city": "Mexico City, CDMX",
        "contact_name": "",
        "title": "",
        "email": "info@abk.mx",
        "phone_whatsapp": "+52 55 5517-5571",
        "website": "abk.mx",
        "business": "LED screen sales and rental, robotic lighting, audio, professional installation in CDMX; 18+ years; serves Tijuana, Puebla, nationwide. Email confirmed from website.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 742,
        "country": "Mexico",
        "region": "Americas",
        "company_en": "Troya Eventos Monterrey",
        "company_local": "Troya Eventos",
        "city": "Monterrey, NL",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+52 81 8372-6327",
        "website": "troyaeventos.com",
        "business": "LED screens 3mm-16mm indoor/outdoor, audio, lighting, staging in Monterrey; serves northern Mexico. IG/FB @troyaeventosMX. Phone from website.",
        "facebook": "troyaeventosMX",
        "instagram": "troyaeventosMX",
        "linkedin": "",
    },
    {
        "no": 743,
        "country": "Mexico",
        "region": "Americas",
        "company_en": "Doppmedia Puebla",
        "company_local": "Doppmedia",
        "city": "Puebla, PUE",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+52 222 672-0113",
        "website": "doppmedia.com",
        "business": "LED screen rental (multiple sizes), audio, closed circuit, video streaming for events in Puebla; 10+ years. Phone from website.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 744,
        "country": "Mexico",
        "region": "Americas",
        "company_en": "GDLED Guadalajara",
        "company_local": "GDLED",
        "city": "Guadalajara, JAL",
        "contact_name": "",
        "title": "",
        "email": "contacto@gdled.com.mx",
        "phone_whatsapp": "",
        "website": "gdled.com.mx",
        "business": "LED screen rental and sales for events in Guadalajara; indoor/outdoor panels. Email confirmed from website.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 745,
        "country": "Chile",
        "region": "Americas",
        "company_en": "StageCore Chile",
        "company_local": "StageCore",
        "city": "Santiago, Chile",
        "contact_name": "",
        "title": "",
        "email": "contacto@stagecore.cl",
        "phone_whatsapp": "",
        "website": "stagecore.cl",
        "business": "LED screen rental indoor/outdoor, professional audio, lighting, scenic design, digital scenography in Santiago; serves corporate, sports, cultural, private events. Las Condes RM. Email confirmed.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
]

leads.extend(new_entries)

if __name__ == "__main__":
    by_country = {}
    for l in leads:
        c = l.get("country", "?")
        by_country[c] = by_country.get(c, 0) + 1
    print(f"Total leads: {len(leads)}")
    for c, n in sorted(by_country.items()):
        print(f"  {c}: {n}")
    print(f"\nNew entries: {len(new_entries)} (nos {new_entries[0]['no']}-{new_entries[-1]['no']})")
    for e in new_entries:
        print(f"  {e['no']:>3}. {e['company_en']:<40} {e['city']}")
