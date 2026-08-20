"""
generate_led_leads_v77.py
USA verified LED display / LED video wall integrators & AV firms: nos 905-909.
Vertical focus: AV integrators / fixed-install + cross-hire rental partners.
"""
import ast
import os
import re

BASE = os.path.dirname(__file__)


def _load(path):
    return open(path, encoding="utf-8").read()


src = _load(os.path.join(BASE, "generate_led_leads_v4.py"))
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", src, re.M | re.S).group(1))

for n in range(5, 77):
    path = os.path.join(BASE, f"generate_led_leads_v{n}.py")
    if not os.path.exists(path):
        continue
    text = _load(path)
    m = re.search(r"^new_entries = (\[.+?^\])", text, re.M | re.S)
    if m:
        leads.extend(ast.literal_eval(m.group(1)))


new_entries = [
    {
        "no": 905,
        "country": "USA",
        "region": "North America",
        "company_en": "Infinite AV Solutions",
        "company_local": "Infinite Audio Video Solutions",
        "city": "Little Silver, NJ",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+1 732 924 5900",
        "website": "i-av.com",
        "business": "Verified LED target: NJ full-service residential/commercial AV design and integration firm deploying LED video walls, displays, automation and control systems. Instagram @infiniteavsolutions, Facebook InfiniteAVSolutions.",
        "facebook": "InfiniteAVSolutions",
        "instagram": "infiniteavsolutions",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://i-av.com/contact-us/"],
    },
    {
        "no": 906,
        "country": "USA",
        "region": "North America",
        "company_en": "TimeLine ProAV",
        "company_local": "TimeLine ProAV",
        "city": "USA (multi-region)",
        "contact_name": "",
        "title": "",
        "email": "info@timelineproav.com",
        "phone_whatsapp": "",
        "website": "timelineproav.com",
        "business": "Verified LED target: AV supplier/integrator serving US corporate, sports bar and restaurant clients with LED video walls, digital signage and full audio-video systems (also operates in Canada and LatAm). Instagram @timelineproav.",
        "facebook": "timelineproav",
        "instagram": "timelineproav",
        "linkedin": "timelineproav",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://timelineproav.com/contact/", "https://timelineproav.com/solutions/sports-bar/"],
    },
    {
        "no": 907,
        "country": "USA",
        "region": "North America",
        "company_en": "Light It Up AV & Turf",
        "company_local": "Light It Up AV and Turf",
        "city": "Fort Worth, TX",
        "contact_name": "Drew Westbrook",
        "title": "",
        "email": "drewwestbrook14@gmail.com",
        "phone_whatsapp": "+1 817 747 7494",
        "website": "lightitupavturf.com",
        "business": "Verified LED target: DFW Texas certified LED video display installation/replacement contractor offering LED video walls and AV installs. Instagram/Facebook @light.it.up.av.and.turf.",
        "facebook": "light.it.up.av.and.turf",
        "instagram": "light.it.up.av.and.turf",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://lightitupavturf.com/led-video-displays/", "https://lightitupavturf.com/contact/"],
    },
    {
        "no": 908,
        "country": "USA",
        "region": "North America",
        "company_en": "ProCore Productions",
        "company_local": "ProCore Productions",
        "city": "Los Angeles, CA",
        "contact_name": "",
        "title": "",
        "email": "connect@procoreproductions.com",
        "phone_whatsapp": "+1 888 892 1790",
        "website": "procoreproductions.com",
        "business": "Verified LED target: Los Angeles event production and AV rental company offering LED wall rentals standalone or as part of full AV packages for concerts, corporate events and productions. Instagram @procorela.",
        "facebook": "",
        "instagram": "procorela",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://procoreproductions.com/services/led-wall-rental/"],
    },
    {
        "no": 909,
        "country": "USA",
        "region": "North America",
        "company_en": "Crunchy Tech",
        "company_local": "Crunchy Tech",
        "city": "Orlando, FL",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+1 321 285 8304",
        "website": "crunchytech.com",
        "business": "Verified LED target: Orlando FL AV company providing LED video wall equipment and installation. Instagram @crunchy_tech.",
        "facebook": "",
        "instagram": "crunchy_tech",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://crunchytech.com/led-video-walls/", "https://crunchytech.com/contact/"],
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
