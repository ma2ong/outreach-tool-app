"""
generate_led_leads_v72.py
USA verified LED display / LED video wall batch: nos 877-881.
"""
import ast
import os
import re

BASE = os.path.dirname(__file__)


def _load(path):
    return open(path, encoding="utf-8").read()


src = _load(os.path.join(BASE, "generate_led_leads_v4.py"))
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", src, re.M | re.S).group(1))

for n in range(5, 72):
    path = os.path.join(BASE, f"generate_led_leads_v{n}.py")
    if not os.path.exists(path):
        continue
    text = _load(path)
    m = re.search(r"^new_entries = (\[.+?^\])", text, re.M | re.S)
    if m:
        leads.extend(ast.literal_eval(m.group(1)))


new_entries = [
    {
        "no": 877,
        "country": "USA",
        "region": "North America",
        "company_en": "Masato Events",
        "company_local": "Masato Events",
        "city": "South Plainfield, NJ",
        "contact_name": "",
        "title": "",
        "email": "info@masatoevents.com",
        "phone_whatsapp": "+1 929 284 5566",
        "website": "masatoevents.com",
        "business": "Verified LED target: event production company offering LED video wall rental and production services, including indoor LED walls and outdoor LED walls for corporate and party events.",
        "facebook": "",
        "instagram": "masatoevents",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://www.masatoevents.com/"],
    },
    {
        "no": 878,
        "country": "USA",
        "region": "North America",
        "company_en": "Radium Pictures",
        "company_local": "Radium Pictures Inc",
        "city": "Fremont, CA",
        "contact_name": "",
        "title": "",
        "email": "info@radiumpix.com",
        "phone_whatsapp": "+1 510 200 3409",
        "website": "radiumpictures.com",
        "business": "Verified LED target: Silicon Valley live event, A/V and LED video wall company with an LED studio, XR stage, 10ft x 16ft LED wall and LED video walls for events and presentations.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://radiumpictures.com/"],
    },
    {
        "no": 879,
        "country": "USA",
        "region": "North America",
        "company_en": "AV Rentals NYC",
        "company_local": "AV Rentals NYC",
        "city": "Brooklyn, NY",
        "contact_name": "",
        "title": "",
        "email": "info@avrentalsnyc.com",
        "phone_whatsapp": "+1 888 691 4991",
        "website": "avrentalsnyc.com",
        "business": "Verified LED target: NYC AV rental and event production company offering LED video wall rentals, LED walls, monitors, displays, stages, lighting and event technical support.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://www.avrentalsnyc.com/"],
    },
    {
        "no": 880,
        "country": "USA",
        "region": "North America",
        "company_en": "Affordable Sound Stages",
        "company_local": "Affordable Sound Stages",
        "city": "Los Angeles, CA",
        "contact_name": "Vic Anthony",
        "title": "",
        "email": "affordablesoundstages@yahoo.com",
        "phone_whatsapp": "+1 818 641 0220",
        "website": "affordablesoundstages.com/led-xr-stage-rental",
        "business": "Verified LED target: Los Angeles XR LED virtual production stage rental with 30ft panoramic LED video wall, LED XR stage rental, LED screen rental and explicit Text/WhatsApp 24/7 contact.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://affordablesoundstages.com/led-xr-stage-rental/"],
    },
    {
        "no": 881,
        "country": "USA",
        "region": "North America",
        "company_en": "Interactive Vision Solutions",
        "company_local": "Interactive Vision Solutions",
        "city": "New York, NY",
        "contact_name": "",
        "title": "",
        "email": "info@avequipmentrental.nyc",
        "phone_whatsapp": "+1 212 729 4305",
        "website": "avequipmentrental.nyc/video-walls-rental-nyc",
        "business": "Verified LED target: NYC video wall rental company offering LED video wall rentals, interactive LED walls and AV equipment rental services for events in the New York metropolitan area.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://avequipmentrental.nyc/video-walls-rental-nyc/"],
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
