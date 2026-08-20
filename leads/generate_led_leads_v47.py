"""
generate_led_leads_v47.py
New entries: nos 692-698 (7 USA leads)
Cities: Raleigh NC / Memphis TN / El Paso TX / Orlando FL x3 / Tulsa OK
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
               "v39","v40","v41","v42","v43","v44","v45","v46"):
    _path = os.path.join(_base, f"generate_led_leads_{_vname}.py")
    if not os.path.exists(_path):
        continue
    _src = _load(_path)
    _m = re.search(r"^new_entries = (\[.+?^\])", _src, re.M | re.S)
    if _m:
        leads.extend(ast.literal_eval(_m.group(1)))

new_entries = [
    {
        "no": 692,
        "country": "USA",
        "region": "Americas",
        "company_en": "GSF Productions",
        "company_local": "",
        "city": "Raleigh, NC",
        "contact_name": "",
        "title": "",
        "email": "info@gsfaudio.com",
        "phone_whatsapp": "+1 919-348-9954",
        "website": "https://gsfaudio.com",
        "business": "Raleigh-based AV production company offering LED video wall rental, lighting, and audio for corporate events and live shows in NC. Instagram @gsf_productions",
        "facebook": "",
        "instagram": "gsf_productions",
        "linkedin": "",
    },
    {
        "no": 693,
        "country": "USA",
        "region": "Americas",
        "company_en": "ProductionOne",
        "company_local": "",
        "city": "Memphis, TN",
        "contact_name": "",
        "title": "",
        "email": "info@productionone.com",
        "phone_whatsapp": "+1 901-881-2511",
        "website": "https://productionone.com",
        "business": "Memphis/Arlington TN AV production company offering LED video wall rental and permanent installation for corporate events, concerts, and trade shows. Instagram @productiononeav",
        "facebook": "",
        "instagram": "productiononeav",
        "linkedin": "",
    },
    {
        "no": 694,
        "country": "USA",
        "region": "Americas",
        "company_en": "TechPro Audio & Video",
        "company_local": "",
        "city": "El Paso, TX",
        "contact_name": "",
        "title": "",
        "email": "service@techpro-av.com",
        "phone_whatsapp": "+1 915-503-2601",
        "website": "https://techpro-av.com",
        "business": "El Paso AV integrator providing video wall installation, digital signage, and commercial AV systems. Instagram @techproavtx",
        "facebook": "",
        "instagram": "techproavtx",
        "linkedin": "",
    },
    {
        "no": 695,
        "country": "USA",
        "region": "Americas",
        "company_en": "Excel Presentation Services",
        "company_local": "",
        "city": "Orlando, FL",
        "contact_name": "",
        "title": "",
        "email": "info@excelpresentations.com",
        "phone_whatsapp": "",
        "website": "https://ledvideowallrentalorlando.com",
        "business": "Orlando LED video wall rental specialist offering indoor fine-pitch and outdoor high-brightness LED panels for trade shows, corporate events, weddings, and outdoor venues. Phone: (407) 884-8000",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 696,
        "country": "USA",
        "region": "Americas",
        "company_en": "AV Rental Orlando",
        "company_local": "",
        "city": "Orlando, FL",
        "contact_name": "",
        "title": "",
        "email": "info@avrentalorlando.com",
        "phone_whatsapp": "+1 407-412-9001",
        "website": "https://avrentalorlando.com",
        "business": "Orlando veteran AV rental company (est. 1995) specializing in seamless LED video walls for OCCC, hotels, and outdoor stages. Phone: (407) 412-9001",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 697,
        "country": "USA",
        "region": "Americas",
        "company_en": "Orlando Video Walls",
        "company_local": "",
        "city": "Orlando, FL",
        "contact_name": "",
        "title": "",
        "email": "hello@orlandovideowallrental.com",
        "phone_whatsapp": "",
        "website": "https://orlandovideowallrental.com",
        "business": "Orlando LED screen rental company focused on video walls, giant LED, mobile LED trailers, digital billboards, and touch screens for corporate events, concerts, and weddings.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 698,
        "country": "USA",
        "region": "Americas",
        "company_en": "VOX Audio Visual",
        "company_local": "",
        "city": "Tulsa, OK",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "",
        "website": "https://voxaudiovisual.com",
        "business": "Oklahoma's fast-growing commercial LED video wall installer; VOX Video Walls division specializes in indoor and outdoor LED wall systems for businesses. IG handle unconfirmed (voxaudiovisual redirected to wrong account)",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
]

leads.extend(new_entries)

if __name__ == "__main__":
    usa = [l for l in leads if l.get("country") == "USA"]
    print(f"v47: {len(new_entries)} new entries, nos {new_entries[0]['no']}-{new_entries[-1]['no']}")
    print(f"Total: {len(leads)}, USA: {len(usa)}")
