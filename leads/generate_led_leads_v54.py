"""
generate_led_leads_v54.py
New entries: nos 746-750 (5 leads: Brazil + Argentina + USA)
Stage Audiovisual (Curitiba BR), AudioLuz (Rosario AR),
7Sentidos (Cordoba AR), Eventos Meet (Cordoba AR),
Visual Impact Productions (Birmingham AL USA)
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
               "v39","v40","v41","v42","v43","v44","v45","v46","v47","v48","v49","v50","v51","v52","v53"):
    _path = os.path.join(_base, f"generate_led_leads_{_vname}.py")
    if not os.path.exists(_path):
        continue
    _src = _load(_path)
    _m = re.search(r"^new_entries = (\[.+?^\])", _src, re.M | re.S)
    if _m:
        leads.extend(ast.literal_eval(_m.group(1)))

new_entries = [
    {
        "no": 746,
        "country": "Brazil",
        "region": "Americas",
        "company_en": "Stage Audiovisual Curitiba",
        "company_local": "Stage Audiovisual",
        "city": "Curitiba, PR",
        "contact_name": "",
        "title": "",
        "email": "comercial@stageaudiovisual.com.br",
        "phone_whatsapp": "+55 41 99717-0279",
        "website": "stageaudiovisual.com.br",
        "business": "LED panel rental for corporate events, weddings, shows, trade fairs in Curitiba PR; 3D simulation projects. WA: 41 99717-0279 (Curitiba mobile confirmed). Email from website.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 747,
        "country": "Argentina",
        "region": "Americas",
        "company_en": "AudioLuz Rosario",
        "company_local": "AudioLuz",
        "city": "Rosario, Santa Fe",
        "contact_name": "",
        "title": "",
        "email": "contacto@audioluz.com.ar",
        "phone_whatsapp": "+54 341 6919230",
        "website": "audioluz.com.ar",
        "business": "25+ years; LED screens indoor/outdoor, architectural mapping, HD cameras, robotic lighting for events in Rosario; Maipú 877. Email confirmed from website.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 748,
        "country": "Argentina",
        "region": "Americas",
        "company_en": "7Sentidos Cordoba",
        "company_local": "7Sentidos",
        "city": "Córdoba, Argentina",
        "contact_name": "",
        "title": "",
        "email": "info@sietesentidos.com.ar",
        "phone_whatsapp": "0800-444-1204",
        "website": "sietesentidos.com.ar",
        "business": "Sales, rental and management of LED screens indoor/outdoor throughout Córdoba province; Villa Allende. Email confirmed from website.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 749,
        "country": "Argentina",
        "region": "Americas",
        "company_en": "Eventos Meet Cordoba",
        "company_local": "Eventos Meet",
        "city": "Córdoba, Argentina",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+54 351 7037719",
        "website": "",
        "business": "LED screen rental and projectors for events in Córdoba capital and interior region. Phone from web search.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 750,
        "country": "USA",
        "region": "Americas",
        "company_en": "Visual Impact Productions",
        "company_local": "",
        "city": "Birmingham, AL",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "844-568-0004",
        "website": "leddisplayrentals.net",
        "business": "Mobile LED screen rentals, custom high-res LED displays, jumbotrons for Birmingham and Alabama events. Phone from website.",
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
