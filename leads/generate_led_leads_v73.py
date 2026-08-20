"""
generate_led_leads_v73.py
USA verified LED display / LED video wall batch: nos 882-888.
"""
import ast
import os
import re

BASE = os.path.dirname(__file__)


def _load(path):
    return open(path, encoding="utf-8").read()


src = _load(os.path.join(BASE, "generate_led_leads_v4.py"))
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", src, re.M | re.S).group(1))

for n in range(5, 73):
    path = os.path.join(BASE, f"generate_led_leads_v{n}.py")
    if not os.path.exists(path):
        continue
    text = _load(path)
    m = re.search(r"^new_entries = (\[.+?^\])", text, re.M | re.S)
    if m:
        leads.extend(ast.literal_eval(m.group(1)))


new_entries = [
    {
        "no": 882,
        "country": "USA",
        "region": "North America",
        "company_en": "Lead Innovations",
        "company_local": "Lead Innovations",
        "city": "Bellevue, NE",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+1 402 809 7502",
        "website": "leadinnovations.com/led-trailer-omaha",
        "business": "Verified LED target: Omaha / Bellevue mobile digital billboard and outdoor LED video wall company offering LED trailer rentals, outdoor TV screen rentals, and customizable indoor/outdoor LED video walls.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": [
            "https://www.leadinnovations.com/led-trailer-omaha",
            "https://www.leadinnovations.com/contact",
        ],
    },
    {
        "no": 883,
        "country": "USA",
        "region": "North America",
        "company_en": "Lehigh Valley Events & Productions",
        "company_local": "Lehigh Valley Events & Productions, LLC",
        "city": "Bethlehem, PA",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+1 610 390 2861",
        "website": "lehighvalleyproductions.com",
        "business": "Verified LED target: Lehigh Valley event production company with LED walls for events plus AV, staging, lasers and event production services; contact page says call or text.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://www.lehighvalleyproductions.com/contact"],
    },
    {
        "no": 884,
        "country": "USA",
        "region": "North America",
        "company_en": "American Movie Company",
        "company_local": "American Movie Company",
        "city": "New York, NY",
        "contact_name": "",
        "title": "",
        "email": "info@americanmovieco.com",
        "phone_whatsapp": "+1 212 219 1075",
        "website": "americanmovieco.com/xr-led-wall-studio",
        "business": "Verified LED target: NYC film and virtual production company offering XR LED wall studio, 27ft LED video wall, curved LED wall cyc, LED ceiling and LED wall installation/rental capabilities.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://www.americanmovieco.com/xr-led-wall-studio"],
    },
    {
        "no": 885,
        "country": "USA",
        "region": "North America",
        "company_en": "SOFLO Main Events",
        "company_local": "SOFLO Main Events",
        "city": "Hialeah, FL",
        "contact_name": "",
        "title": "",
        "email": "info@soflomainevents.com",
        "phone_whatsapp": "+1 305 714 0402",
        "website": "soflomainevents.com",
        "business": "Verified LED target: Miami / South Florida event production and audiovisual company listing LED video wall service alongside audio, lighting, staging and event production.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": [
            "https://soflomainevents.com/",
            "https://www.soflomainevents.com/contact/",
        ],
    },
    {
        "no": 886,
        "country": "USA",
        "region": "North America",
        "company_en": "Pure AV",
        "company_local": "Pure Audio Visual Inc",
        "city": "Las Vegas, NV",
        "contact_name": "",
        "title": "",
        "email": "info@pureav.co",
        "phone_whatsapp": "+1 800 929 7089",
        "website": "pureav.co",
        "business": "Verified LED target: Las Vegas AV company offering LED/LCD video wall rentals, LED video panels including 2mm curvable, 4mm indoor and 7mm outdoor panels for events, trade shows and conferences.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://pureav.co/"],
    },
    {
        "no": 887,
        "country": "USA",
        "region": "North America",
        "company_en": "Digital Sign Distributors",
        "company_local": "Digital Sign Distributors LLC",
        "city": "Tampa, FL",
        "contact_name": "",
        "title": "",
        "email": "info@digitalsigndistributors.com",
        "phone_whatsapp": "+1 813 547 5008",
        "website": "digitalsigndistributors.com",
        "business": "Verified LED target: Florida LED signage distributor offering indoor LED displays, outdoor LED billboards, LED video wall systems, mobile demo service and mobile LED sign trailer rentals.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://digitalsigndistributors.com/"],
    },
    {
        "no": 888,
        "country": "USA",
        "region": "North America",
        "company_en": "DVS LED Systems",
        "company_local": "DVS LED Systems",
        "city": "Dania Beach, FL",
        "contact_name": "",
        "title": "",
        "email": "sales@dvsledsystems.com",
        "phone_whatsapp": "+1 813 563 8005",
        "website": "dvsledsystems.com",
        "business": "Verified LED target: Florida direct-view LED display systems company with LED video wall panels, showroom, dealer channel and sales/support contact for LED systems.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": [
            "https://dvsledsystems.com/contact/",
            "https://dvsledsystems.com/frequently-asked-questions/",
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
