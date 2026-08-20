"""
generate_led_leads_v79.py
USA verified LED display / LED video wall integrators & installers: nos 919-924.
Vertical focus: house-of-worship & commercial AV integrators, mid-city installers,
LED video wall dealer/reseller.
"""
import ast
import os
import re

BASE = os.path.dirname(__file__)


def _load(path):
    return open(path, encoding="utf-8").read()


src = _load(os.path.join(BASE, "generate_led_leads_v4.py"))
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", src, re.M | re.S).group(1))

for n in range(5, 79):
    path = os.path.join(BASE, f"generate_led_leads_v{n}.py")
    if not os.path.exists(path):
        continue
    text = _load(path)
    m = re.search(r"^new_entries = (\[.+?^\])", text, re.M | re.S)
    if m:
        leads.extend(ast.literal_eval(m.group(1)))


new_entries = [
    {
        "no": 919,
        "country": "USA",
        "region": "North America",
        "company_en": "CSAV Systems",
        "company_local": "CSAV Systems",
        "city": "Fairfield, NJ",
        "contact_name": "",
        "title": "",
        "email": "info@csavsystems.com",
        "phone_whatsapp": "",
        "website": "csavsystems.com",
        "business": "Verified LED target: NJ AV integrator that designs, integrates and installs LED video walls for houses of worship, corporate and commercial clients. Email confirmed from csavsystems.com/contact. Instagram @csav_systems.",
        "facebook": "",
        "instagram": "csav_systems",
        "linkedin": "csav-systems",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://csavsystems.com/church-guide-choosing-installing-led-video-wall/", "https://csavsystems.com/contact"],
    },
    {
        "no": 920,
        "country": "USA",
        "region": "North America",
        "company_en": "S&L Integrated",
        "company_local": "S&L Integrated Systems",
        "city": "Thomasville, GA",
        "contact_name": "",
        "title": "",
        "email": "info@slintegrated.com",
        "phone_whatsapp": "",
        "website": "slintegrated.com",
        "business": "Verified LED target: Southeast US AV integrator (founded 1999, HQ Thomasville GA + Atlanta) providing LED video wall design, integration and installation for houses of worship and corporate. Email confirmed from slintegrated.com/contact. Instagram @slintegrated, Facebook SLintegratedsystems.",
        "facebook": "SLintegratedsystems",
        "instagram": "slintegrated",
        "linkedin": "slintegrated",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://slintegrated.com/blog/led-video-walls-for-churches-transform-your-house-of-worship-experience/", "https://slintegrated.com/contact"],
    },
    {
        "no": 921,
        "country": "USA",
        "region": "North America",
        "company_en": "Commercial AV Services",
        "company_local": "Commercial AV Services",
        "city": "Glendale, AZ",
        "contact_name": "",
        "title": "",
        "email": "tomc@commercialavservices.com",
        "phone_whatsapp": "+1 602 626 5800",
        "website": "commercialavservices.com",
        "business": "Verified LED target: Arizona commercial AV integrator (Glendale AZ, serving AZ/CO/UT) offering LED video wall and commercial audiovisual installation. Email confirmed from commercialavservices.com/contact. Instagram @commercial_av_services.",
        "facebook": "",
        "instagram": "commercial_av_services",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://www.commercialavservices.com/commercial-audiovisual-installation/glendale-az", "https://www.commercialavservices.com/contact"],
    },
    {
        "no": 922,
        "country": "USA",
        "region": "North America",
        "company_en": "Above AVL",
        "company_local": "Above AVL",
        "city": "Nashville, TN",
        "contact_name": "",
        "title": "",
        "email": "gear@aboveavl.com",
        "phone_whatsapp": "",
        "website": "aboveavl.com",
        "business": "Verified LED target: Nashville TN AV company providing LED video wall installations for casinos, venues and commercial spaces (team nationwide). Email confirmed from aboveavl.com/pages/contact. Instagram @aboveavl.",
        "facebook": "",
        "instagram": "aboveavl",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://aboveavl.com/pages/installations", "https://aboveavl.com/pages/contact"],
    },
    {
        "no": 923,
        "country": "USA",
        "region": "North America",
        "company_en": "Video Walls 4 Less",
        "company_local": "Video Walls 4 Less",
        "city": "USA (multi-region)",
        "contact_name": "",
        "title": "",
        "email": "consulting@videowalls4less.com",
        "phone_whatsapp": "",
        "website": "videowalls4less.com",
        "business": "Verified LED target: US dealer/reseller/installer of LED video wall panels (indoor & outdoor), sourcing components directly from manufacturers and offering full/assisted/remote installation + financing. Email confirmed from videowalls4less.com/contact.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://videowalls4less.com/", "https://videowalls4less.com/contact"],
    },
    {
        "no": 924,
        "country": "USA",
        "region": "North America",
        "company_en": "CCI Solutions",
        "company_local": "CCI Solutions",
        "city": "Olympia, WA",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "",
        "website": "ccisolutions.com",
        "business": "Verified LED target: church/commercial AV retailer and integrator offering LED video wall installation (Olympia WA HQ; also serves Phoenix AZ). No public email surfaced -> IG DM channel. Instagram @ccisolutions.",
        "facebook": "",
        "instagram": "ccisolutions",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://www.ccisolutions.com/solutions/video", "https://www.ccisolutions.com/contact-us"],
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
