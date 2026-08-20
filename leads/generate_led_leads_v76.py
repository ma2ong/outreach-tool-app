"""
generate_led_leads_v76.py
USA verified LED display / LED video wall batch: nos 901-904.
"""
import ast
import os
import re

BASE = os.path.dirname(__file__)


def _load(path):
    return open(path, encoding="utf-8").read()


src = _load(os.path.join(BASE, "generate_led_leads_v4.py"))
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", src, re.M | re.S).group(1))

for n in range(5, 76):
    path = os.path.join(BASE, f"generate_led_leads_v{n}.py")
    if not os.path.exists(path):
        continue
    text = _load(path)
    m = re.search(r"^new_entries = (\[.+?^\])", text, re.M | re.S)
    if m:
        leads.extend(ast.literal_eval(m.group(1)))


new_entries = [
    {
        "no": 901,
        "country": "USA",
        "region": "North America",
        "company_en": "AV Vegas",
        "company_local": "AV Vegas",
        "city": "Las Vegas, NV",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+1 702 878 5050",
        "website": "avvegas.com",
        "business": "Verified LED target: Las Vegas AV rental and production company offering modular LED video wall rentals with ground support/rigging and onsite technicians for trade shows, conventions and corporate events. Instagram @av_vegas.",
        "facebook": "",
        "instagram": "av_vegas",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://www.avvegas.com/production/video-wall-rental/"],
    },
    {
        "no": 902,
        "country": "USA",
        "region": "North America",
        "company_en": "Exhibit Experience",
        "company_local": "Exhibit Experience",
        "city": "Las Vegas, NV",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+1 800 511 0150",
        "website": "exhibitexperience.com",
        "business": "Verified LED target: Las Vegas trade show AV provider offering LED video wall rentals and lighting for last-minute and emergency trade show/convention setups nationwide. Instagram @exhibit.experience.",
        "facebook": "",
        "instagram": "exhibit.experience",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://exhibitexperience.com/las-vegas-led-video-wall-rentals-for-trade-shows-events/"],
    },
    {
        "no": 903,
        "country": "USA",
        "region": "North America",
        "company_en": "Sign On LLC",
        "company_local": "Sign-On LLC",
        "city": "Cape Coral, FL",
        "contact_name": "",
        "title": "",
        "email": "info@capeled.com",
        "phone_whatsapp": "+1 239 800 9454",
        "website": "signsandleds.com",
        "business": "Verified LED target: Florida full-service sign company, designer/fabricator/installer of outdoor LED signs and electronic message centers; top Watchfire LED sign dealer and service center in SWFL, also offering LED screen rental.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://signsandleds.com/", "https://signsandleds.com/led-signage/"],
    },
    {
        "no": 904,
        "country": "USA",
        "region": "North America",
        "company_en": "Visible Display",
        "company_local": "Visible Display",
        "city": "Nationwide (multi-city USA)",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "",
        "website": "visibledisplay.com",
        "business": "Verified LED target: Nationwide LED screen and mobile LED trailer rental company operating since 2005, serving events across Denver, Nashville, Portland, Seattle, Sacramento, Washington DC and 20+ US cities.",
        "facebook": "",
        "instagram": "",
        "linkedin": "visible-display",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://visibledisplay.com/led-screen-rental/", "https://visibledisplay.com/portfolio/"],
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
