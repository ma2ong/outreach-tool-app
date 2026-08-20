"""
generate_led_leads_v81.py
USA verified LED display / LED video wall integrators & dealers: nos 930-933.
Vertical focus: broadcast/studio, esports & education AV integrators, MicroLED dealer.
"""
import ast
import os
import re

BASE = os.path.dirname(__file__)


def _load(path):
    return open(path, encoding="utf-8").read()


src = _load(os.path.join(BASE, "generate_led_leads_v4.py"))
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", src, re.M | re.S).group(1))

for n in range(5, 81):
    path = os.path.join(BASE, f"generate_led_leads_v{n}.py")
    if not os.path.exists(path):
        continue
    text = _load(path)
    m = re.search(r"^new_entries = (\[.+?^\])", text, re.M | re.S)
    if m:
        leads.extend(ast.literal_eval(m.group(1)))


new_entries = [
    {
        "no": 930,
        "country": "USA",
        "region": "North America",
        "company_en": "Data Projections",
        "company_local": "Data Projections Inc.",
        "city": "Houston, TX",
        "contact_name": "",
        "title": "",
        "email": "DPIWeb@dataprojections.com",
        "phone_whatsapp": "",
        "website": "dataprojections.com",
        "business": "Verified LED target: Texas AV integrator (HQ Houston + Austin/San Antonio/Dallas/Nashville offices) designing and installing LED & traditional video walls for corporate, education and government clients. Email confirmed from dataprojections.com/contact-us.",
        "facebook": "",
        "instagram": "",
        "linkedin": "data-projections-inc-",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://www.dataprojections.com/Products/Video-Walls/", "https://www.dataprojections.com/contact-us"],
    },
    {
        "no": 931,
        "country": "USA",
        "region": "North America",
        "company_en": "Horizon AVL",
        "company_local": "Horizon AVL System Integration",
        "city": "Blackwood, NJ",
        "contact_name": "",
        "title": "",
        "email": "info@horizonavl.com",
        "phone_whatsapp": "",
        "website": "horizonavl.com",
        "business": "Verified LED target: NJ AV/broadcast/esports systems integrator delivering dvLED video walls for corporate, government, education and house-of-worship (e.g. Syracuse University Gaming & Esports Center). Email confirmed from horizonavl.com/contact. Instagram @horizonavl, Facebook horizonavl.",
        "facebook": "horizonavl",
        "instagram": "horizonavl",
        "linkedin": "horizon-avl",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://horizonavl.com/", "https://horizonavl.com/contact"],
    },
    {
        "no": 932,
        "country": "USA",
        "region": "North America",
        "company_en": "GHT Group",
        "company_local": "GHT Group",
        "city": "Atlanta, GA",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "",
        "website": "ghtgroup.com",
        "business": "Verified LED target: Atlanta GA MicroLED / direct-view LED video wall dealer & installer (authorized Just Video Walls brand). No public email (contact form only) -> IG DM channel. Instagram @ghtgroupatl.",
        "facebook": "",
        "instagram": "ghtgroupatl",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://ghtgroup.com/brands/just-video-walls", "https://ghtgroup.com/contact"],
    },
    {
        "no": 933,
        "country": "USA",
        "region": "North America",
        "company_en": "FORTE AV",
        "company_local": "FORTÉ",
        "city": "USA (multi-region)",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "",
        "website": "ourforte.com",
        "business": "Verified LED target: US AV integrator (est. 1974) handling broadcast, live streaming, sporting events and esports with LED video wall solutions. No public email (contact form only) -> IG DM channel. Instagram @ourforte1974.",
        "facebook": "",
        "instagram": "ourforte1974",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://www.ourforte.com/", "https://www.ourforte.com/contact"],
    },
]

leads.extend(new_entries)

if __name__ == "__main__":
    usa = sum(1 for row in leads if row.get("country") == "USA")
    print(f"Total leads: {len(leads)}")
    print(f"USA leads: {usa}")
    print(f"New entries: {len(new_entries)}")
    for row in new_entries:
        print(f"{row['no']} | {row['company_en']} | {row['city']} | {row['email'] or row['website']}")
