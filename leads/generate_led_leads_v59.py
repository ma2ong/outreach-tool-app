"""
generate_led_leads_v59.py
USA verified LED display batch: nos 780-783.
"""
import ast
import os
import re

BASE = os.path.dirname(__file__)


def _load(path):
    return open(path, encoding="utf-8").read()


src = _load(os.path.join(BASE, "generate_led_leads_v4.py"))
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", src, re.M | re.S).group(1))

for n in range(5, 59):
    path = os.path.join(BASE, f"generate_led_leads_v{n}.py")
    if not os.path.exists(path):
        continue
    text = _load(path)
    m = re.search(r"^new_entries = (\[.+?^\])", text, re.M | re.S)
    if m:
        leads.extend(ast.literal_eval(m.group(1)))


new_entries = [
    {
        "no": 780,
        "country": "USA",
        "region": "North America",
        "company_en": "Aplus Exhibits",
        "company_local": "Aplus Exhibits",
        "city": "Las Vegas, NV",
        "contact_name": "Jacky",
        "title": "",
        "email": "jacky@aplusexhibits.com",
        "phone_whatsapp": "+1 702 321 3322",
        "website": "aplusexhibits.com/led-video-wall",
        "business": "Verified LED target: Las Vegas LED video wall rentals and sales, 15,000+ LED panels, Las Vegas warehouse plus SF/Chicago/Orlando satellite locations; site form asks for phone number or WhatsApp.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "whatsapp_source": "site phone and form label says Phone Number or Whatsapp; needs WA attempt",
    },
    {
        "no": 781,
        "country": "USA",
        "region": "North America",
        "company_en": "Brilliant Event Lighting",
        "company_local": "Brilliant Event Lighting",
        "city": "San Diego / Southern California",
        "contact_name": "",
        "title": "",
        "email": "hello@brillianteventlighting.com",
        "phone_whatsapp": "+1 760 652 9939",
        "website": "brillianteventlighting.com/led-video-wall-rentals",
        "business": "Verified LED target: LED video wall rental, LED screen rental and LED display solutions in San Diego and Southern California; modular 1.9mm and 2.6mm LED walls from 138in to 360in.",
        "facebook": "BrilliantEventLighting",
        "instagram": "brillianteventlighting",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 782,
        "country": "USA",
        "region": "North America",
        "company_en": "Bolt LED",
        "company_local": "Bolt LED",
        "city": "San Diego / Los Angeles, CA",
        "contact_name": "",
        "title": "",
        "email": "info@boltled.net",
        "phone_whatsapp": "+1 619 537 9298",
        "website": "boltled.net",
        "business": "Verified LED target: LED video wall rental, sales, touring, design, installation and support; San Diego, Spring Valley and Los Angeles locations; ships to all 50 states.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 783,
        "country": "USA",
        "region": "North America",
        "company_en": "ADMFA Audio",
        "company_local": "ADMFA Audio LLC",
        "city": "Houston, TX",
        "contact_name": "",
        "title": "",
        "email": "info@admfaaudio.com",
        "phone_whatsapp": "+1 530 502 8346",
        "website": "admfaaudiollc.com",
        "business": "Verified LED target: Houston AV, venue, rentals and production company offering LED walls, LED screens, LED panels, livestreaming, lighting and show execution.",
        "facebook": "ADMFAAudioAcademy",
        "instagram": "admfaaudio",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
]

seen = set()
for lead in leads:
    for key in ("website", "email", "instagram", "facebook"):
        value = str(lead.get(key, "")).strip().lower()
        if value:
            seen.add(value)

for entry in new_entries:
    for key in ("website", "email", "instagram", "facebook"):
        value = str(entry.get(key, "")).strip().lower()
        if value and value in seen:
            raise SystemExit(f"Duplicate {key} found: {value}")

leads.extend(new_entries)

if __name__ == "__main__":
    print(f"Total leads: {len(leads)}")
    print(f"USA leads: {sum(1 for item in leads if item.get('country') == 'USA')}")
    for item in new_entries:
        print(f"{item['no']} | {item['company_en']} | email:{item['email']} | IG:{item['instagram']} | FB:{item['facebook']} | WA:{item['phone_whatsapp']}")
