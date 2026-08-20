"""
generate_led_leads_v63.py
USA verified LED display batch: nos 804-813.
"""
import ast
import os
import re

BASE = os.path.dirname(__file__)


def _load(path):
    return open(path, encoding="utf-8").read()


src = _load(os.path.join(BASE, "generate_led_leads_v4.py"))
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", src, re.M | re.S).group(1))

for n in range(5, 63):
    path = os.path.join(BASE, f"generate_led_leads_v{n}.py")
    if not os.path.exists(path):
        continue
    text = _load(path)
    m = re.search(r"^new_entries = (\[.+?^\])", text, re.M | re.S)
    if m:
        leads.extend(ast.literal_eval(m.group(1)))


new_entries = [
    {
        "no": 804,
        "country": "USA",
        "region": "North America",
        "company_en": "Mobile Stage USA",
        "company_local": "Mobile Stage USA",
        "city": "Nationwide USA",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+1 888 855 1641",
        "website": "mobilestageusa.com/led-video-wall-rentals",
        "business": "Verified LED target: US live event company with a dedicated LED video wall rentals page for custom indoor/outdoor LED video wall display packages nationwide.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 805,
        "country": "USA",
        "region": "North America",
        "company_en": "SRXTeK",
        "company_local": "SRXTeK",
        "city": "Arlington Heights, IL",
        "contact_name": "",
        "title": "",
        "email": "info@srxtek.com",
        "phone_whatsapp": "+1 847 275 3456",
        "website": "srxtek.com",
        "business": "Verified LED target: USA-based LED wall and virtual production company offering LED wall manufacturing, leasing, rental, LED stage rentals and event technology.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 806,
        "country": "USA",
        "region": "North America",
        "company_en": "LED Exhibits",
        "company_local": "LED Exhibits",
        "city": "Orlando, FL",
        "contact_name": "",
        "title": "",
        "email": "info@ledexhibits.com",
        "phone_whatsapp": "+1 888 895 3372",
        "website": "ledexhibits.com",
        "business": "Verified LED target: Orlando company specializing in LED video wall trade show exhibit rentals and sales, including LED display video wall rental options.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 807,
        "country": "USA",
        "region": "North America",
        "company_en": "Grant's Tech",
        "company_local": "Grant's Tech",
        "city": "Delaware / Westerville, OH",
        "contact_name": "",
        "title": "",
        "email": "info@grantstech.net",
        "phone_whatsapp": "+1 740 206 7245",
        "website": "grantstech.net/copy-of-live-events",
        "business": "Verified LED target: Central Ohio company with a dedicated LED Video Walls page for LED video wall rental, sales, installation and event services.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 808,
        "country": "USA",
        "region": "North America",
        "company_en": "Summit Prestige",
        "company_local": "Summit Prestige",
        "city": "Ridgeley, WV",
        "contact_name": "",
        "title": "",
        "email": "support@summitprestige.com",
        "phone_whatsapp": "+1 301 707 5785",
        "website": "summitprestige.com",
        "business": "Verified LED target: US ecommerce company listing LED video wall rental package products and contact details for display package inquiries.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 809,
        "country": "USA",
        "region": "North America",
        "company_en": "The Tekk Group Corporation",
        "company_local": "The Tekk Group",
        "city": "Las Vegas, NV",
        "contact_name": "",
        "title": "",
        "email": "hire@thetekkgroup.com",
        "phone_whatsapp": "+1 702 851 8351",
        "website": "thetekkgroup.com/video-wall-rental",
        "business": "Verified LED target: video wall rental supplier with a listed USA office in Las Vegas and services for video wall rental delivery and setup across major US cities.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 810,
        "country": "USA",
        "region": "North America",
        "company_en": "Profigroup",
        "company_local": "Profigroup",
        "city": "Seattle, WA",
        "contact_name": "",
        "title": "",
        "email": "info@profigroup.us",
        "phone_whatsapp": "+1 253 349 7753",
        "website": "profigroup.us/tvs-and-led-panels",
        "business": "Verified LED target: Seattle event rental company listing LED screens, video walls, TVs and LED panel rental services with NovaStar LED video wall controller inventory.",
        "facebook": "profigroupus",
        "instagram": "profigroupus",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 811,
        "country": "USA",
        "region": "North America",
        "company_en": "Big Wheel Digital Media",
        "company_local": "Big Wheel Digital Media",
        "city": "Broken Arrow / Tulsa, OK",
        "contact_name": "",
        "title": "",
        "email": "info@bigwheeldigitalmedia.com",
        "phone_whatsapp": "+1 918 921 4818",
        "website": "bigwheeldigitalmedia.com/big-led-screens",
        "business": "Verified LED target: Oklahoma company with Big LED Screens page offering LED video wall screen systems for churches, casinos, rental use, touring and streaming.",
        "facebook": "bigwheeldigitalmedia",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 812,
        "country": "USA",
        "region": "North America",
        "company_en": "Mobile Technology Graphics",
        "company_local": "MTG Displays",
        "city": "Lehigh Valley, PA / Tampa, FL",
        "contact_name": "",
        "title": "",
        "email": "info@mtgsigns.com",
        "phone_whatsapp": "+1 877 392 4220",
        "website": "mtgdisplays.com",
        "business": "Verified LED target: nationwide indoor and outdoor LED video wall rental company offering mobile jumbotrons, indoor LED walls and LED poster rentals.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 813,
        "country": "USA",
        "region": "North America",
        "company_en": "HB Live",
        "company_local": "HB Live",
        "city": "North Haven, CT",
        "contact_name": "",
        "title": "",
        "email": "info@hblive.com",
        "phone_whatsapp": "+1 203 234 8107",
        "website": "hblive.com/event-technology/led-wall-rental",
        "business": "Verified LED target: Connecticut event production company with a dedicated LED Wall Rentals page for indoor and outdoor LED wall rentals and event displays.",
        "facebook": "HBLiveInc",
        "instagram": "hbliveinc",
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
        print(f"{item['no']} | {item['company_en']} | email:{item['email']} | IG:{item['instagram']} | FB:{item['facebook']} | WA:{item['phone_whatsapp']} | wav:{item.get('whatsapp_verified')}")
