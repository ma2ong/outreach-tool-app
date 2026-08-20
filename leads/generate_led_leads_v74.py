"""
generate_led_leads_v74.py
USA verified LED display / LED video wall batch: nos 889-893.
"""
import ast
import os
import re

BASE = os.path.dirname(__file__)


def _load(path):
    return open(path, encoding="utf-8").read()


src = _load(os.path.join(BASE, "generate_led_leads_v4.py"))
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", src, re.M | re.S).group(1))

for n in range(5, 74):
    path = os.path.join(BASE, f"generate_led_leads_v{n}.py")
    if not os.path.exists(path):
        continue
    text = _load(path)
    m = re.search(r"^new_entries = (\[.+?^\])", text, re.M | re.S)
    if m:
        leads.extend(ast.literal_eval(m.group(1)))


new_entries = [
    {
        "no": 889,
        "country": "USA",
        "region": "North America",
        "company_en": "Iowa Media",
        "company_local": "Iowa Media",
        "city": "Waterloo, IA",
        "contact_name": "Matt",
        "title": "",
        "email": "matt@iowa-media.com",
        "phone_whatsapp": "+1 319 290 1644",
        "website": "iowa-media.com",
        "business": "Verified LED target: Waterloo, Iowa LED video wall rental and install company offering customizable LED video walls and screens for concerts, conferences, festivals and indoor/outdoor events.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://iowa-media.com/", "https://iowa-media.com/install/"],
    },
    {
        "no": 890,
        "country": "USA",
        "region": "North America",
        "company_en": "Assorted Studios",
        "company_local": "Assorted Studios",
        "city": "Harrisburg, PA",
        "contact_name": "Jesse",
        "title": "",
        "email": "Assortedstudios@gmail.com",
        "phone_whatsapp": "+1 717 916 3050",
        "website": "assortedstudios.com/harrisburg-led-panel-rentals",
        "business": "Verified LED target: Harrisburg, Pennsylvania AV production and rental company offering LED screen and video wall rentals within 500 miles of its warehouse, with LED wall delivery, setup and technician support.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": [
            "https://www.assortedstudios.com/harrisburg-led-panel-rentals",
            "https://www.assortedstudios.com/",
        ],
    },
    {
        "no": 891,
        "country": "USA",
        "region": "North America",
        "company_en": "Blue Sky Productions",
        "company_local": "Blue Sky Productions",
        "city": "Cedar Rapids, IA",
        "contact_name": "",
        "title": "",
        "email": "info@blueskypd.com",
        "phone_whatsapp": "+1 319 214 0460",
        "website": "blueskypd.com",
        "business": "Verified LED target: Iowa video and audio production/equipment rental company renting LED video walls, projection systems, PA systems and event production gear; site says call/text for quotes.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://www.blueskypd.com/"],
    },
    {
        "no": 892,
        "country": "USA",
        "region": "North America",
        "company_en": "Crescent Event Productions",
        "company_local": "Crescent Event Productions, Inc.",
        "city": "Nashville, TN / Charlotte, NC / Atlanta, GA",
        "contact_name": "",
        "title": "",
        "email": "hello@crescentevents.com",
        "phone_whatsapp": "+1 800 579 2737",
        "website": "crescentevents.com/video-systems",
        "business": "Verified LED target: event production company serving Nashville, Charlotte and Atlanta with LED wall rental, video systems, projection, staging, lighting and event production services.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": [
            "https://crescentevents.com/video-systems/",
            "https://crescentevents.com/locations/charlotte-nc/",
        ],
    },
    {
        "no": 893,
        "country": "USA",
        "region": "North America",
        "company_en": "L/A Music Productions",
        "company_local": "LA Music Productions",
        "city": "Lewiston/Auburn, ME",
        "contact_name": "",
        "title": "",
        "email": "lamusicproductions@yahoo.com",
        "phone_whatsapp": "+1 207 783 0058",
        "website": "lamusicproductionsofmaine.com",
        "business": "Verified LED target: Maine production company offering LED video wall rental displays for concerts, schools, business meetings and houses of worship, plus permanent LED installs for scoreboards and business signs.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://www.lamusicproductionsofmaine.com/"],
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
