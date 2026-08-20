"""
generate_led_leads_v71.py
USA verified LED display / LED video wall batch: nos 872-876.
"""
import ast
import os
import re

BASE = os.path.dirname(__file__)


def _load(path):
    return open(path, encoding="utf-8").read()


src = _load(os.path.join(BASE, "generate_led_leads_v4.py"))
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", src, re.M | re.S).group(1))

for n in range(5, 71):
    path = os.path.join(BASE, f"generate_led_leads_v{n}.py")
    if not os.path.exists(path):
        continue
    text = _load(path)
    m = re.search(r"^new_entries = (\[.+?^\])", text, re.M | re.S)
    if m:
        leads.extend(ast.literal_eval(m.group(1)))


new_entries = [
    {
        "no": 872,
        "country": "USA",
        "region": "North America",
        "company_en": "Goodboy Multimedia",
        "company_local": "Goodboy Multimedia, Inc.",
        "city": "Detroit, MI",
        "contact_name": "Daniel",
        "title": "",
        "email": "goodboymultimedia@gmail.com",
        "phone_whatsapp": "+1 313 349 3234",
        "website": "goodboymultimedia.com",
        "business": "Verified LED target: Detroit AV/media production company offering LED wall installation, LED wall rental, AV production, lighting and audio for event venues, churches, retail and permanent media spaces.",
        "facebook": "",
        "instagram": "",
        "linkedin": "goodboy-multimedia",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": [
            "https://www.goodboymultimedia.com/media-installations",
            "https://www.goodboymultimedia.com/",
        ],
    },
    {
        "no": 873,
        "country": "USA",
        "region": "North America",
        "company_en": "The ProMedia Group",
        "company_local": "The ProMedia Group of Tampa Corp.",
        "city": "Tampa, FL",
        "contact_name": "",
        "title": "",
        "email": "sales@thepromediagroup.com",
        "phone_whatsapp": "+1 800 881 6887",
        "website": "thepromediagroup.com",
        "business": "Verified LED target: Tampa commercial AV design-build integrator specializing in video walls, digital signage, direct-view LED, broadcast systems and meeting room AV installation.",
        "facebook": "",
        "instagram": "thepromediagroup",
        "linkedin": "the-promedia-group",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": [
            "https://thepromediagroup.com/",
            "https://do.linkedin.com/company/the-promedia-group",
        ],
    },
    {
        "no": 874,
        "country": "USA",
        "region": "North America",
        "company_en": "EventFab",
        "company_local": "EventFab LLC",
        "city": "Waterbury, CT / New York, NY",
        "contact_name": "Alex",
        "title": "",
        "email": "alex@eventfab.com",
        "phone_whatsapp": "+1 203 208 8909",
        "website": "eventfab.com",
        "business": "Verified LED target: event production and rental company serving CT, NY, MA and RI with LED video walls, AV production, lighting, projection, show control and fabrication services.",
        "facebook": "eventfab",
        "instagram": "eventfab.pro",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": [
            "https://eventfab.com/services/a-v-production-services-in-ct-ny-ma-ri/",
            "https://eventfab.com/contact-us",
        ],
    },
    {
        "no": 875,
        "country": "USA",
        "region": "North America",
        "company_en": "MARX entertainment",
        "company_local": "MARX entertainment",
        "city": "East Longmeadow, MA",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+1 866 627 9357",
        "website": "marxentertainment.net/led-wall-rental-ma",
        "business": "Verified LED target: Massachusetts full-service event production company offering LED wall rental, LED video wall rental and LED stage screen rental for conferences, galas, weddings, trade shows and awards ceremonies.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://www.marxentertainment.net/led-wall-rental-ma/"],
    },
    {
        "no": 876,
        "country": "USA",
        "region": "North America",
        "company_en": "media mea",
        "company_local": "media mea LLC",
        "city": "Miami, FL",
        "contact_name": "",
        "title": "",
        "email": "sales@mediamea.io",
        "phone_whatsapp": "+1 305 928 3311",
        "website": "mediamea.io/Ad-Tech-Solutions/Digital-Signage-Hardware/LED-RENTAL-SERVICES",
        "business": "Verified LED target: Miami digital out-of-home and ad-tech company with LED rental services, full HD LED video walls, LED DJ booth/wall facade, indoor/outdoor LED rental screens and digital signage hardware.",
        "facebook": "",
        "instagram": "",
        "linkedin": "mediamea",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://www.mediamea.io/Ad-Tech-Solutions/Digital-Signage-Hardware/LED-RENTAL-SERVICES"],
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
