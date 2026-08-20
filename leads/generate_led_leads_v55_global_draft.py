"""
generate_led_leads_v55.py
New entries: nos 751-756 (6 leads: Korea + Colombia + Peru)
Korea: Bit Media (Daejeon), MT Media (Seoul)
Colombia: Dibelco (Barranquilla)
Peru: Virttua (Lima), Digital Studio Peru (Lima), Marketing Visual 360 (Lima)
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
               "v39","v40","v41","v42","v43","v44","v45","v46","v47","v48","v49","v50","v51","v52","v53","v54"):
    _path = os.path.join(_base, f"generate_led_leads_{_vname}.py")
    if not os.path.exists(_path):
        continue
    _src = _load(_path)
    _m = re.search(r"^new_entries = (\[.+?^\])", _src, re.M | re.S)
    if _m:
        leads.extend(ast.literal_eval(_m.group(1)))

new_entries = [
    {
        "no": 751,
        "country": "Korea",
        "region": "Asia",
        "company_en": "Bit Media Daejeon",
        "company_local": "비트미디어",
        "city": "Daejeon",
        "contact_name": "",
        "title": "",
        "email": "btm912@naver.com",
        "phone_whatsapp": "010-8270-0708",
        "website": "btm912.com",
        "business": "LED display rental, video systems, event production in Daejeon; serves exhibitions, hotels, convention centers, corporate events. Mobile 010-8270-0708. IG @beatmedia912. Email confirmed from website.",
        "facebook": "",
        "instagram": "beatmedia912",
        "linkedin": "",
    },
    {
        "no": 752,
        "country": "Korea",
        "region": "Asia",
        "company_en": "MT Media Seoul",
        "company_local": "엠티미디어",
        "city": "Seoul",
        "contact_name": "",
        "title": "",
        "email": "mtmedia@naver.com",
        "phone_whatsapp": "010-9045-3707",
        "website": "mtmedia.co.kr",
        "business": "LED display and projector rental/installation in Seoul; 20+ years since 2002; Seongbuk-gu. Mobile 010-9045-3707. Email confirmed from website.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 753,
        "country": "Colombia",
        "region": "Americas",
        "company_en": "Dibelco Barranquilla",
        "company_local": "DIBELCO S.A.S.",
        "city": "Barranquilla, Atlantico",
        "contact_name": "",
        "title": "",
        "email": "info@dibel.co",
        "phone_whatsapp": "+57 311 240 2705",
        "website": "dibel.co",
        "business": "Digital signage, LED panels indoor/outdoor, video walls, cloud content management in Barranquilla; Samsung Tizen, interactive displays, custom totems. WA +57 311 240 2705 (Colombia mobile). IG @dibel.co.",
        "facebook": "",
        "instagram": "dibel.co",
        "linkedin": "",
    },
    {
        "no": 754,
        "country": "Peru",
        "region": "Americas",
        "company_en": "Virttua Producciones",
        "company_local": "Virttua Producciones",
        "city": "Lima, Peru",
        "contact_name": "",
        "title": "",
        "email": "eventos@virttua.com.pe",
        "phone_whatsapp": "+51 999 132 134",
        "website": "virttua.com.pe",
        "business": "LED screen rental indoor/outdoor P2/P3, event production, AV for corporate and social events in Lima; Miraflores. WA +51 999132134 (Peru mobile confirmed). Email from website.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 755,
        "country": "Peru",
        "region": "Americas",
        "company_en": "Digital Studio Peru",
        "company_local": "Digital Studio Peru S.A.C.",
        "city": "Lima, Peru",
        "contact_name": "",
        "title": "",
        "email": "informes@digitalstudioperu.com",
        "phone_whatsapp": "+51 999 661 285",
        "website": "digitalstudioperu.com",
        "business": "P3 LED screen rental for corporate and institutional events in Lima; also live streaming, drone, AV. Phone +51 999661285 (Peru mobile). Email confirmed from website.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 756,
        "country": "Peru",
        "region": "Americas",
        "company_en": "Marketing Visual 360",
        "company_local": "Marketing Visual 360",
        "city": "Lima, Peru",
        "contact_name": "",
        "title": "",
        "email": "ventas@marketingvisual360.com",
        "phone_whatsapp": "+51 965 342 114",
        "website": "marketingvisual.pe",
        "business": "LED screen rental, touchscreen totems, BTL services for corporate and fashion events in Lima. WA +51 965342114 (Peru mobile confirmed). Email from website.",
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
