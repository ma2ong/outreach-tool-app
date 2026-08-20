"""
generate_led_leads_v58.py
USA verified LED display batch: nos 775-779 (5 leads)

Includes only US-based companies/pages with explicit LED display, LED screen, LED wall, or LED video wall work.
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
    "v50", "v51", "v52", "v53", "v54", "v55", "v56", "v57",
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
        "no": 775,
        "country": "USA",
        "region": "North America",
        "company_en": "HV ALL IN SOLUTIONS",
        "company_local": "HV ALL IN SOLUTIONS",
        "city": "Miami, FL",
        "contact_name": "",
        "title": "",
        "email": "Info@hvledusa.com",
        "phone_whatsapp": "+1 786 567 2007",
        "website": "hvallinsolutions.com",
        "business": "Verified LED target: Miami LED screen services, installation, repair and rental solutions. Website lists LED screen, LED display, Text us (786) 567-2007, and wa.me/17865672007. IG @hvallinsolutions.",
        "facebook": "",
        "instagram": "hvallinsolutions",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": True,
        "whatsapp_link": "https://wa.me/17865672007",
    },
    {
        "no": 776,
        "country": "USA",
        "region": "North America",
        "company_en": "EAV Pro",
        "company_local": "EAV Pro",
        "city": "Delaware / Miami event work",
        "contact_name": "",
        "title": "",
        "email": "info@eavpro.com",
        "phone_whatsapp": "+1 302 730 2441",
        "website": "eavpro.com",
        "business": "Verified LED target: Audio, lighting, video, LED video wall, installations and sales. Website lists high-resolution LED video walls and WhatsApp link wa.me/13027302441. FB page 104590035815139.",
        "facebook": "104590035815139",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": True,
        "whatsapp_link": "https://wa.me/13027302441",
    },
    {
        "no": 777,
        "country": "USA",
        "region": "North America",
        "company_en": "LED Media Group",
        "company_local": "LED Media Group",
        "city": "Miami, FL",
        "contact_name": "",
        "title": "",
        "email": "info@ledmediagroup.com",
        "phone_whatsapp": "+1 305 340 1396",
        "website": "ledmediagroup.com/contactanos",
        "business": "Verified LED target: audiovisual and digital screen solutions, LED displays, Miami address 20815 NE16 Ave B-6, WhatsApp +1 305 340 1396, US/Canada toll free line. Has Facebook/Instagram links on contact page.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": True,
    },
    {
        "no": 778,
        "country": "USA",
        "region": "North America",
        "company_en": "INTESOL USA",
        "company_local": "INTESOL USA",
        "city": "Coral Springs / Miami, FL",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "",
        "website": "intesolusa.com",
        "business": "Verified LED target: US location at 10303 Royal Palm Blvd, Coral Springs, FL; LED Video Displays category with LED screens, video walls and digital poster displays. Site testimonial mentions purchasing via WhatsApp but no number found.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 779,
        "country": "USA",
        "region": "North America",
        "company_en": "Intela USA",
        "company_local": "Intela USA",
        "city": "Placentia / Los Angeles, CA",
        "contact_name": "",
        "title": "",
        "email": "contact@intelaus.com",
        "phone_whatsapp": "+1 800 802 0778",
        "website": "intelaus.com",
        "business": "Verified LED target: Los Angeles based cinema LED wall and RGB laser light source company; address 990 S Via Rodeo, Placentia, CA 92870 United States; contact@intelaus.com.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
]

seen = set()
for lead in leads:
    for key in ("website", "email", "instagram", "facebook"):
        val = str(lead.get(key, "")).strip().lower()
        if val:
            seen.add(val)

for entry in new_entries:
    for key in ("website", "email", "instagram", "facebook"):
        val = str(entry.get(key, "")).strip().lower()
        if val and val in seen:
            raise SystemExit(f"Duplicate {key} found: {val}")

leads.extend(new_entries)

if __name__ == "__main__":
    usa_count = sum(1 for item in leads if item.get("country") == "USA")
    print(f"Total leads: {len(leads)}")
    print(f"USA leads: {usa_count}")
    for item in new_entries:
        print(f"{item['no']} | {item['company_en']} | email:{item['email']} | IG:{item['instagram']} | FB:{item['facebook']} | WA:{item.get('whatsapp_verified')}")
