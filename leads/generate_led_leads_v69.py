"""
generate_led_leads_v69.py
USA verified LED display / LED video wall batch: nos 861-866.
"""
import ast
import os
import re

BASE = os.path.dirname(__file__)


def _load(path):
    return open(path, encoding="utf-8").read()


src = _load(os.path.join(BASE, "generate_led_leads_v4.py"))
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", src, re.M | re.S).group(1))

for n in range(5, 69):
    path = os.path.join(BASE, f"generate_led_leads_v{n}.py")
    if not os.path.exists(path):
        continue
    text = _load(path)
    m = re.search(r"^new_entries = (\[.+?^\])", text, re.M | re.S)
    if m:
        leads.extend(ast.literal_eval(m.group(1)))


new_entries = [
    {
        "no": 861,
        "country": "USA",
        "region": "North America",
        "company_en": "Beantown Audio Rentals",
        "company_local": "Beantown Audio Rentals",
        "city": "Boston, MA",
        "contact_name": "",
        "title": "",
        "email": "info@beantownaudiorentals.com",
        "phone_whatsapp": "+1 617 286 4757",
        "website": "beantownaudiorentals.com",
        "business": "Verified LED target: Boston AV rental company offering 2.67mm indoor LED video walls, 3.91 outdoor video wall trailers, video packages and production support across Massachusetts and New England.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 862,
        "country": "USA",
        "region": "North America",
        "company_en": "A. A. Rental",
        "company_local": "AA Rental",
        "city": "Washington DC / VA / MD",
        "contact_name": "",
        "title": "",
        "email": "info@aarental.com",
        "phone_whatsapp": "+1 703 644 1660",
        "website": "aarental.com",
        "business": "Verified LED target: Washington DC area AV rental company offering LED and LCD video wall rental services for events, conventions, meetings and exhibitions across DC, Virginia and Maryland.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 863,
        "country": "USA",
        "region": "North America",
        "company_en": "EMI Audio",
        "company_local": "Sound Video & Lighting / EMI Audio",
        "city": "Minneapolis, MN",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+1 612 789 2496",
        "website": "emiaudio.com",
        "business": "Verified LED target: Minneapolis sound, video and lighting rental company offering CHAUVET LED video wall panel packages and LED video wall rental support for Minneapolis / St. Paul events.",
        "facebook": "EMIAUDIO",
        "instagram": "EMIAudio",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 864,
        "country": "USA",
        "region": "North America",
        "company_en": "AValive",
        "company_local": "AValive",
        "city": "Nationwide USA",
        "contact_name": "",
        "title": "",
        "email": "customerservice@avalive.com",
        "phone_whatsapp": "+1 866 937 7628",
        "website": "avalive.com",
        "business": "Verified LED target: nationwide AV rental supplier with a dedicated LED video wall rental / digital signage video wall / trade show video wall product category.",
        "facebook": "AValive",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 865,
        "country": "USA",
        "region": "North America",
        "company_en": "Electric Events DC",
        "company_local": "Electric Events DC",
        "city": "Washington DC / MD / VA",
        "contact_name": "",
        "title": "",
        "email": "hithere@electriceventsdc.com",
        "phone_whatsapp": "+1 301 370 1125",
        "website": "electriceventsdc.com",
        "business": "Verified LED target: DC event production company offering LED poster rental, LED video wall poster rental and high-resolution LED display rentals for event signage and visual experiences.",
        "facebook": "electriceventsdc",
        "instagram": "electriceventsdc",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 866,
        "country": "USA",
        "region": "North America",
        "company_en": "Screenworks NEP",
        "company_local": "Screenworks NEP",
        "city": "Corona, CA",
        "contact_name": "",
        "title": "",
        "email": "info@screenworksnep.com",
        "phone_whatsapp": "+1 951 279 8877",
        "website": "screenworksnep.com",
        "business": "Verified LED target: California LED video display solutions company providing indoor rental LED video walls, outdoor rental LED displays and mobile LED screens for sports, concerts and corporate events.",
        "facebook": "NEPGroupInc",
        "instagram": "screenworksnep",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
]

leads.extend(new_entries)

if __name__ == "__main__":
    usa = sum(1 for row in leads if row.get("country") == "USA")
    print(f"Total leads: {len(leads)}")
    print(f"USA leads: {usa}")
    print(f"New entries: {len(new_entries)}")
    for row in new_entries:
        print(f"{row['no']} | {row['company_en']} | {row['city']} | {row['website']}")
