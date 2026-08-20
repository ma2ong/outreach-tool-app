"""
generate_led_leads_v68.py
USA verified LED display / LED video wall batch: nos 851-860.
"""
import ast
import os
import re

BASE = os.path.dirname(__file__)


def _load(path):
    return open(path, encoding="utf-8").read()


src = _load(os.path.join(BASE, "generate_led_leads_v4.py"))
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", src, re.M | re.S).group(1))

for n in range(5, 68):
    path = os.path.join(BASE, f"generate_led_leads_v{n}.py")
    if not os.path.exists(path):
        continue
    text = _load(path)
    m = re.search(r"^new_entries = (\[.+?^\])", text, re.M | re.S)
    if m:
        leads.extend(ast.literal_eval(m.group(1)))


new_entries = [
    {
        "no": 851,
        "country": "USA",
        "region": "North America",
        "company_en": "Staging Rental NYC",
        "company_local": "Staging Rental NYC",
        "city": "Brooklyn / New York, NY",
        "contact_name": "",
        "title": "",
        "email": "info@stagingrentalnyc.com",
        "phone_whatsapp": "+1 212 419 0119",
        "website": "stagingrentalnyc.com",
        "business": "Verified LED target: New York staging rental company offering indoor and outdoor LED video wall rental, custom LED wall shapes, LED backdrops and LED display products for live shows and activations.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 852,
        "country": "USA",
        "region": "North America",
        "company_en": "LED Wall Masters",
        "company_local": "LED Video Wall Rental NYC",
        "city": "New York, NY",
        "contact_name": "",
        "title": "",
        "email": "info@led-video-wall-rental.com",
        "phone_whatsapp": "+1 646 779 2675",
        "website": "led-video-wall-rental.com",
        "business": "Verified LED target: New York LED video wall rental company offering outdoor LED walls, indoor LED walls, mobile LED walls, large LED walls, custom LED screens and LED totem panels.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 853,
        "country": "USA",
        "region": "North America",
        "company_en": "Eminence AV",
        "company_local": "Eminence AV",
        "city": "Orlando, FL",
        "contact_name": "",
        "title": "",
        "email": "info@eminenceent.com",
        "phone_whatsapp": "+1 407 686 1017",
        "website": "eminenceav.com",
        "business": "Verified LED target: Orlando AV company with LED video wall rentals, P2.9 LED screen packages, delivery, setup, operation and custom LED solutions for events.",
        "facebook": "eminenceav",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 854,
        "country": "USA",
        "region": "North America",
        "company_en": "IMAGINI",
        "company_local": "IMAGINI LED",
        "city": "Orlando, FL",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "",
        "website": "imaginiled.com",
        "business": "Verified LED target: Orlando LED video wall rental and sales company providing LED walls for conferences, concerts, churches, trade shows and corporate events, including rental packages and permanent installation sales.",
        "facebook": "imaginiled",
        "instagram": "imaginiled",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 855,
        "country": "USA",
        "region": "North America",
        "company_en": "AV Event Rental",
        "company_local": "Event Production Services",
        "city": "New Jersey / Tri-State Area",
        "contact_name": "",
        "title": "",
        "email": "info@aveventrental.com",
        "phone_whatsapp": "+1 732 547 5423",
        "website": "aveventrental.com",
        "business": "Verified LED target: New Jersey event production company listing LED video walls among its core AV rental services for events in New Jersey and the Tri-State Area.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 856,
        "country": "USA",
        "region": "North America",
        "company_en": "Karana Audio Visual Services",
        "company_local": "Karana Audio Visual",
        "city": "Houston, TX",
        "contact_name": "",
        "title": "",
        "email": "info@karana-audiovisual.com",
        "phone_whatsapp": "+1 281 780 5625",
        "website": "karana-audiovisual.com",
        "business": "Verified LED target: Houston audio visual company offering LED video screens, LED video walls, LED columns and P3.9mm LED panels for sports, music, corporate events and staged designs.",
        "facebook": "karanaAV",
        "instagram": "karana.audiovisual",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 857,
        "country": "USA",
        "region": "North America",
        "company_en": "Nocturnal Audio Visual",
        "company_local": "Nocturnal Audio Visual Inc",
        "city": "San Antonio, TX",
        "contact_name": "",
        "title": "",
        "email": "Avtechray1@gmail.com",
        "phone_whatsapp": "+1 210 833 4156",
        "website": "nocturnalaudiovisual.com",
        "business": "Verified LED target: San Antonio AV, lighting and LED video wall rental / production company providing LED video walls and LED wall services for events.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 858,
        "country": "USA",
        "region": "North America",
        "company_en": "Achieve AV",
        "company_local": "Achieve AV",
        "city": "Dallas, TX",
        "contact_name": "",
        "title": "",
        "email": "info@achieveav.com",
        "phone_whatsapp": "+1 214 884 5951",
        "website": "achieveav.com",
        "business": "Verified LED target: Dallas AV company providing live event production, commercial AV installation, LED video wall rental, mobile stages and LED video wall technology for events and installations.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 859,
        "country": "USA",
        "region": "North America",
        "company_en": "Intech Solutions Houston",
        "company_local": "Houston Audiovisual Equipment Installation",
        "city": "Houston, TX",
        "contact_name": "",
        "title": "",
        "email": "info@intechsolutions.com",
        "phone_whatsapp": "+1 832 734 6518",
        "website": "itsavvideowallinstallationhouston.com",
        "business": "Verified LED target: Houston audiovisual equipment installation and rental company offering LED video wall installation and LED video wall rental services for residential and commercial projects.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 860,
        "country": "USA",
        "region": "North America",
        "company_en": "Multimedia Audio Visual",
        "company_local": "Multimedia Audio Visual",
        "city": "Englewood / Denver, CO",
        "contact_name": "",
        "title": "",
        "email": "info@multimediaav.com",
        "phone_whatsapp": "+1 303 623 2324",
        "website": "multimediaav.com",
        "business": "Verified LED target: Denver-area AV rental company with LED video wall rentals, indoor HD LED panels and modular LED configurations for event AV needs.",
        "facebook": "",
        "instagram": "",
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
