"""
generate_led_leads_v75.py
USA verified LED display / LED video wall batch: nos 894-900.
"""
import ast
import os
import re

BASE = os.path.dirname(__file__)


def _load(path):
    return open(path, encoding="utf-8").read()


src = _load(os.path.join(BASE, "generate_led_leads_v4.py"))
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", src, re.M | re.S).group(1))

for n in range(5, 75):
    path = os.path.join(BASE, f"generate_led_leads_v{n}.py")
    if not os.path.exists(path):
        continue
    text = _load(path)
    m = re.search(r"^new_entries = (\[.+?^\])", text, re.M | re.S)
    if m:
        leads.extend(ast.literal_eval(m.group(1)))


new_entries = [
    {
        "no": 894,
        "country": "USA",
        "region": "North America",
        "company_en": "SOHO LED Rentals",
        "company_local": "SOHO LED Rentals",
        "city": "New York, NY",
        "contact_name": "",
        "title": "",
        "email": "Contact@SOHOLedRentals.com",
        "phone_whatsapp": "+1 212 431 8920",
        "website": "soholedrentals.com",
        "business": "Verified LED target: Soho NYC LED video wall rental and installation company offering customized LED video wall solutions for retail, conferences, stadium/events, houses of worship and live show operation.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://soholedrentals.com/"],
    },
    {
        "no": 895,
        "country": "USA",
        "region": "North America",
        "company_en": "Nerotek Industries",
        "company_local": "Nerotek Industries IA",
        "city": "Des Moines, IA",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+1 515 599 6376",
        "website": "nerotekindustries.com",
        "business": "Verified LED target: Iowa mobile LED wall rental and creative event production company offering outdoor LED video wall rentals with onboard generator and event production support.",
        "facebook": "",
        "instagram": "",
        "linkedin": "nerotek-industries-llc",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://www.nerotekindustries.com/"],
    },
    {
        "no": 896,
        "country": "USA",
        "region": "North America",
        "company_en": "Ultimate Occasions",
        "company_local": "Ultimate Occasions",
        "city": "Jessup, MD / DMV",
        "contact_name": "",
        "title": "",
        "email": "info@ultoccasions.com",
        "phone_whatsapp": "+1 443 419 4360",
        "website": "ultoccasions.com/led-screen",
        "business": "Verified LED target: DMV event production company providing LED video walls, LED screens, staging, lighting and entertainment rentals for Washington DC, Virginia, Baltimore, Philadelphia and NYC.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://www.ultoccasions.com/led-screen", "https://www.ultoccasions.com/about"],
    },
    {
        "no": 897,
        "country": "USA",
        "region": "North America",
        "company_en": "1st Way Pro Rental",
        "company_local": "1st Way Pro Rental",
        "city": "Westminster, CA",
        "contact_name": "",
        "title": "",
        "email": "info@1stwayprorental.com",
        "phone_whatsapp": "+1 714 487 7419",
        "website": "1stwayprorental.com",
        "business": "Verified LED target: Southern California event production and AV rental company offering LED video walls, stage lighting, sound systems, truss, VJ services and full production for concerts, weddings and corporate events.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://1stwayprorental.com/"],
    },
    {
        "no": 898,
        "country": "USA",
        "region": "North America",
        "company_en": "NYC LED Wall Rental",
        "company_local": "ledwall.nyc",
        "city": "Brooklyn, NY",
        "contact_name": "",
        "title": "",
        "email": "wlab@wlab.tech",
        "phone_whatsapp": "",
        "website": "ledwall.nyc",
        "business": "Verified LED target: NYC LED wall rental provider offering high-resolution P1.875/P3.91 LED walls for corporate events, concerts and trade shows with union-certified setup and technical support.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://ledwall.nyc/"],
    },
    {
        "no": 899,
        "country": "USA",
        "region": "North America",
        "company_en": "Mystical Entertainment Group",
        "company_local": "Mystical Entertainment Group, LLC",
        "city": "Verona, NJ / Staten Island, NY",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+1 973 542 8068",
        "website": "medjs.com/enhancements/A/V/led-video-wall",
        "business": "Verified LED target: NJ and NYC metro entertainment/production company offering modular P3.9 indoor LED video wall rentals for corporate events, weddings, live productions and festivals.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": [
            "https://www.medjs.com/enhancements/A/V/led-video-wall",
            "https://www.medjs.com/company/contact",
        ],
    },
    {
        "no": 900,
        "country": "USA",
        "region": "North America",
        "company_en": "PhotoTek NYC",
        "company_local": "PhotoTekNYC",
        "city": "New York, NY",
        "contact_name": "",
        "title": "",
        "email": "info@phototeknyc.com",
        "phone_whatsapp": "+1 516 582 4422",
        "website": "phototeknyc.com/led-video-wall-rental",
        "business": "Verified LED target: NYC event technology company offering professional LED video wall rental for trade show booths, corporate conferences, product launches, concerts and special events across NYC/NJ/CT.",
        "facebook": "",
        "instagram": "phototeknyc",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": [
            "https://phototeknyc.com/led-video-wall-rental/",
            "https://phototeknyc.com/contact/",
        ],
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
