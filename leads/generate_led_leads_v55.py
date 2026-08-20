"""
generate_led_leads_v55.py
USA batch: nos 751-758 (8 leads)

Focus: LED video wall rental/sales/integration companies with email, IG, FB, and phone where available.
"""
import ast
import os
import re

_base = os.path.dirname(__file__)


def _load(path):
    return open(path, encoding="utf-8").read()


_v4_src = _load(os.path.join(_base, "generate_led_leads_v4.py"))
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", _v4_src, re.M | re.S).group(1))

for _vname in (
    "v5", "v6", "v7", "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", "v16",
    "v17", "v18", "v19", "v20", "v21", "v22", "v23", "v24", "v25", "v26", "v27",
    "v28", "v29", "v30", "v31", "v32", "v33", "v34", "v35", "v36", "v37", "v38",
    "v39", "v40", "v41", "v42", "v43", "v44", "v45", "v46", "v47", "v48", "v49",
    "v50", "v51", "v52", "v53", "v54",
):
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
        "country": "USA",
        "region": "North America",
        "company_en": "Live Light Inc.",
        "company_local": "Live Light Inc.",
        "city": "Fresno, CA",
        "contact_name": "",
        "title": "",
        "email": "info@livelightent.com",
        "phone_whatsapp": "(559) 453-1618",
        "website": "livelightent.com",
        "business": "Production services for concerts, theatre, churches, TV/film, corporate events and schools since 1978; offers LED wall rental, camera rental, video, audio, lighting and stage rental in Fresno.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 752,
        "country": "USA",
        "region": "North America",
        "company_en": "Freedom Fun USA Oklahoma City",
        "company_local": "Freedom Fun USA",
        "city": "Oklahoma City / Moore, OK",
        "contact_name": "",
        "title": "",
        "email": "okc@freedomfunusa.com",
        "phone_whatsapp": "(405) 955-4386",
        "website": "freedomfunusa.com/category/led-screen-rentals-oklahoma-city-oklahoma",
        "business": "Mobile LED screen and video wall rentals for Oklahoma City corporate events, watch parties, schools, churches, graduations and outdoor events. IG @freedomfunusa, FB freedomfunusa.",
        "facebook": "freedomfunusa",
        "instagram": "freedomfunusa",
        "linkedin": "",
        "target_fit": "excluded_non_core_led",
        "do_not_contact": True,
        "exclude_reason": "Party/outdoor entertainment rental company; LED screen page exists but not confirmed as LED display industry core customer.",
    },
    {
        "no": 753,
        "country": "USA",
        "region": "North America",
        "company_en": "KEAR Media",
        "company_local": "KEAR Media",
        "city": "Boise, ID",
        "contact_name": "Don",
        "title": "",
        "email": "mykearmedia@gmail.com",
        "phone_whatsapp": "(208) 713-0929",
        "website": "kearmedia.com",
        "business": "Mobile video wall advertising and event activation in Boise and the Treasure Valley; dual 3 ft x 5 ft LED screens on mobile truck for festivals, concerts, launches, weddings and campaigns. IG @kear_media_boise.",
        "facebook": "profile.php?id=61567844349693",
        "instagram": "kear_media_boise",
        "linkedin": "",
        "target_fit": "candidate_unverified",
        "do_not_contact": True,
        "exclude_reason": "Must manually verify the exact IG/FB account and LED display fit before any further outreach.",
    },
    {
        "no": 754,
        "country": "USA",
        "region": "North America",
        "company_en": "All Things Audio Visual",
        "company_local": "All Things Audio Visual",
        "city": "Boise, ID",
        "contact_name": "",
        "title": "",
        "email": "info@allthingsaudiovisual.com",
        "phone_whatsapp": "208-477-1028",
        "website": "allthingsaudiovisual.com",
        "business": "AV consultation, design and integration in Boise; includes LED video walls, restaurant/lobby speakers, theatrical and production lighting, PA systems, broadcast and streaming video solutions.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 755,
        "country": "USA",
        "region": "North America",
        "company_en": "Colossal Productions",
        "company_local": "Colossal Productions",
        "city": "Knoxville, TN",
        "contact_name": "",
        "title": "",
        "email": "Colossalproductionsllc@gmail.com",
        "phone_whatsapp": "1-865-236-1850",
        "website": "colossalproductions.com",
        "business": "Large-screen LED video walls and mobile LED trailers for East Tennessee events, watch parties, corporate gatherings and private events. IG @colossalproductionsevents, FB ColossalProductionsEvents.",
        "facebook": "ColossalProductionsEvents",
        "instagram": "colossalproductionsevents",
        "linkedin": "",
    },
    {
        "no": 756,
        "country": "USA",
        "region": "North America",
        "company_en": "Strategic Integrated Systems",
        "company_local": "Strategic Integrated Systems",
        "city": "Knoxville, TN",
        "contact_name": "",
        "title": "",
        "email": "info@strategic.is",
        "phone_whatsapp": "865-213-2778",
        "website": "strategic.is",
        "business": "AV system design, sales and installation in Knoxville; specializes in LED displays for digital signage, museum exhibits, live video for performance and other integrated applications.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 757,
        "country": "USA",
        "region": "North America",
        "company_en": "Anytime Party Machines USA",
        "company_local": "Anytime Party Machines USA",
        "city": "Atlanta, GA / Knoxville, TN / Nashville, TN",
        "contact_name": "",
        "title": "",
        "email": "info@anytimepartymachinesusa.com",
        "phone_whatsapp": "404-547-2659 / 404-641-1427",
        "website": "anytimepartymachinesusa.com/led-wall",
        "business": "Indoor/outdoor LED wall rental plus stage, audio, party machines and production rentals serving Atlanta, Knoxville and Nashville. IG @anytime_party_machines_usa_, FB anytimepartymachinesusa.",
        "facebook": "anytimepartymachinesusa",
        "instagram": "anytime_party_machines_usa_",
        "linkedin": "",
        "target_fit": "excluded_non_core_led",
        "do_not_contact": True,
        "exclude_reason": "Party machines/events rental company; not confirmed as LED display industry core customer.",
    },
    {
        "no": 758,
        "country": "USA",
        "region": "North America",
        "company_en": "SkySlate Signs",
        "company_local": "SkySlate Signs",
        "city": "Oklahoma City, OK",
        "contact_name": "",
        "title": "",
        "email": "sales@skyslate.com",
        "phone_whatsapp": "(405) 673-6925",
        "website": "skyslate.com",
        "business": "Custom indoor and outdoor LED screens and digital signage from Oklahoma City; designs and fabricates rugged LED screens for businesses, schools, churches and organizations.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
]

existing = {str(x.get("website", "")).lower() for x in leads}
for entry in new_entries:
    if entry["website"].lower() in existing:
        raise SystemExit(f"Duplicate website found: {entry['website']}")

leads.extend(new_entries)

if __name__ == "__main__":
    usa_count = sum(1 for x in leads if x.get("country") == "USA")
    print(f"Total leads: {len(leads)}")
    print(f"USA leads: {usa_count}")
    print("New v55 entries:")
    for item in new_entries:
        print(f"  {item['no']} | {item['company_en']} | {item['city']} | {item['email']} | IG:{item['instagram']} | FB:{item['facebook']}")
