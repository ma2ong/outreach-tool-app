"""
generate_led_leads_v52.py
New entries: nos 730-737 (8 leads: USA/Brazil/Colombia/Chile/Argentina)
Cities: Reno NV / Goiânia BR / Porto Alegre BR / São Paulo BR /
        Medellín CO / Bogotá CO / Santiago CL / Buenos Aires AR
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
               "v39","v40","v41","v42","v43","v44","v45","v46","v47","v48","v49","v50","v51"):
    _path = os.path.join(_base, f"generate_led_leads_{_vname}.py")
    if not os.path.exists(_path):
        continue
    _src = _load(_path)
    _m = re.search(r"^new_entries = (\[.+?^\])", _src, re.M | re.S)
    if _m:
        leads.extend(ast.literal_eval(_m.group(1)))

new_entries = [
    {
        "no": 730,
        "country": "USA",
        "region": "Americas",
        "company_en": "Vision Control Associates",
        "company_local": "",
        "city": "Reno, NV",
        "contact_name": "",
        "title": "",
        "email": "sales@visioncontrol.com",
        "phone_whatsapp": "775-391-0477",
        "website": "visioncontrol.com",
        "business": "LED video wall rental and installation for corporate and sporting events; indoor/outdoor; offices in Reno NV and Las Vegas NV. Nevada contractor #71570.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 731,
        "country": "Brazil",
        "region": "Americas",
        "company_en": "Led Midia Goiania",
        "company_local": "Led Mídia",
        "city": "Goiânia, GO",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+55 62 98498-8484",
        "website": "ledmidia.com.br",
        "business": "LED panel rental (P3 indoor/outdoor) for events in Goiás; 15+ years, 20,000+ rental projects, 1,500m² panel inventory; shows, weddings, graduations, corporate events. phone confirmed from website; mobile ✓",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 732,
        "country": "Brazil",
        "region": "Americas",
        "company_en": "OFF Produtora",
        "company_local": "OFF Produtora",
        "city": "Porto Alegre, RS",
        "contact_name": "Natalia",
        "title": "",
        "email": "contato@offprodutora.com.br",
        "phone_whatsapp": "+55 51 98034-1515",
        "website": "offprodutora.com.br",
        "business": "LED panel rental (PH3/PH5/PH6 indoor & outdoor) for events in Porto Alegre RS; VJ services, custom setups for parties, weddings, corporate. mobile ✓ (51 98034-1515)",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 733,
        "country": "Brazil",
        "region": "Americas",
        "company_en": "Multivision Locacoes",
        "company_local": "Multivision Locações",
        "city": "São Paulo, SP",
        "contact_name": "",
        "title": "",
        "email": "falecom@multivisionlocacoes.com.br",
        "phone_whatsapp": "+55 11 3941-5210",
        "website": "multivisionlocacoes.com.br",
        "business": "National LED panel rental company; indoor/outdoor panels for events across Brazil including SP, RJ, BH, Curitiba, Porto Alegre, Goiânia, Brasília. Also manufactures panels. email from website.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 734,
        "country": "Colombia",
        "region": "Americas",
        "company_en": "Logistica y Eventos Medellin",
        "company_local": "Logística y Eventos Medellín",
        "city": "Medellín, Colombia",
        "contact_name": "",
        "title": "",
        "email": "logisticaymontajes1@gmail.com",
        "phone_whatsapp": "+57 312 759 0337",
        "website": "logisticayeventosmedellin.com",
        "business": "LED screen rental and full event production; 18+ years experience; serves Medellín, Bogotá, Cali, Barranquilla, Cartagena, Bucaramanga nationally. WA mobile ✓ (312 = Colombia mobile)",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 735,
        "country": "Colombia",
        "region": "Americas",
        "company_en": "King Productions Bogota",
        "company_local": "King Productions",
        "city": "Bogotá, Colombia",
        "contact_name": "Andres Lopez",
        "title": "Commercial Management",
        "email": "contacto@kingproductions1.com",
        "phone_whatsapp": "+57 322 445 8123",
        "website": "kingproductions1.com",
        "business": "Specialized in LED screen, video wall, touch panel, and audio/video rental for events in Bogotá; Calle 9 #42-39. WA mobile ✓ (322 = Colombia mobile)",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 736,
        "country": "Chile",
        "region": "Americas",
        "company_en": "Alfacom Chile",
        "company_local": "Alfacom",
        "city": "Santiago, Chile",
        "contact_name": "",
        "title": "",
        "email": "informaciones@alfacom.cl",
        "phone_whatsapp": "+56 2 2476-1613",
        "website": "alfacom.cl",
        "business": "LED panel arriendo (P6, up to 30m²) + videowall for corporate events, stands, conferences; 28 years experience; nationwide Chile. Instagram @alfacom.cl (confirmed)",
        "facebook": "",
        "instagram": "alfacom.cl",
        "linkedin": "",
    },
    {
        "no": 737,
        "country": "Argentina",
        "region": "Americas",
        "company_en": "LS Producciones Buenos Aires",
        "company_local": "LS Producciones",
        "city": "Buenos Aires, Argentina",
        "contact_name": "",
        "title": "",
        "email": "info@lsproducciones.com.ar",
        "phone_whatsapp": "+54 11 7538-9877",
        "website": "lsproducciones.com.ar",
        "business": "LED screen rental (indoor & outdoor, various sizes) + sound, lighting, video production; 20+ years; exhibitions, conferences, events in Buenos Aires. Facebook: LSProduccionesBA",
        "facebook": "LSProduccionesBA",
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
    print(f"\nNew entries: {len(new_entries)} (nos {new_entries[0]['no']}–{new_entries[-1]['no']})")
    for e in new_entries:
        print(f"  {e['no']:>3}. {e['company_en']:<40} {e['city']}")
