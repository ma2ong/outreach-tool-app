"""
generate_led_leads_v80.py
USA verified LED display / LED video wall integrators & dealers: nos 925-929.
Vertical focus: casino/hospitality & corporate-lobby AV integrators, pro-video
LED video wall dealers.
"""
import ast
import os
import re

BASE = os.path.dirname(__file__)


def _load(path):
    return open(path, encoding="utf-8").read()


src = _load(os.path.join(BASE, "generate_led_leads_v4.py"))
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", src, re.M | re.S).group(1))

for n in range(5, 80):
    path = os.path.join(BASE, f"generate_led_leads_v{n}.py")
    if not os.path.exists(path):
        continue
    text = _load(path)
    m = re.search(r"^new_entries = (\[.+?^\])", text, re.M | re.S)
    if m:
        leads.extend(ast.literal_eval(m.group(1)))


new_entries = [
    {
        "no": 925,
        "country": "USA",
        "region": "North America",
        "company_en": "Alpha Video & Audio",
        "company_local": "Alpha (AlphaX)",
        "city": "Eden Prairie, MN",
        "contact_name": "",
        "title": "",
        "email": "boxsales@alphax.us",
        "phone_whatsapp": "",
        "website": "alphax.us",
        "business": "Verified LED target: Minneapolis-area AV integrator (Alpha Video & Audio) offering end-to-end LED video wall design, integration and service for casinos, corporate and sports venues (e.g. Muckleshoot Casino exterior LED). Email confirmed from alphax.us/contact.",
        "facebook": "",
        "instagram": "",
        "linkedin": "alpha-video-&-audio-inc-",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://alphax.us/led-video-walls/", "https://alphax.us/contact"],
    },
    {
        "no": 926,
        "country": "USA",
        "region": "North America",
        "company_en": "Texadia Systems",
        "company_local": "Texadia Systems",
        "city": "Addison, TX (Dallas-Fort Worth)",
        "contact_name": "",
        "title": "",
        "email": "support@texadiasystems.com",
        "phone_whatsapp": "",
        "website": "texadiasystems.com",
        "business": "Verified LED target: Dallas-Fort Worth commercial AV integrator installing direct-view LED video walls for corporate lobbies and commercial spaces. Email confirmed from texadiasystems.com/contact. Instagram @texadiasystems.",
        "facebook": "",
        "instagram": "texadiasystems",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://texadiasystems.com/commercial/solutions/video-walls", "https://texadiasystems.com/contact"],
    },
    {
        "no": 927,
        "country": "USA",
        "region": "North America",
        "company_en": "Ford AV",
        "company_local": "Ford Audio-Video",
        "city": "Oklahoma City, OK (Dallas & Houston offices)",
        "contact_name": "",
        "title": "",
        "email": "sales@fordav.com",
        "phone_whatsapp": "",
        "website": "fordav.com",
        "business": "Verified LED target: national AV integrator (offices in OK, TX Dallas/Houston + nationwide) installing dvLED video walls for corporate HQs (e.g. Peterbilt Motors Denton TX). Email confirmed from fordav.com/contact. Instagram @fordav.",
        "facebook": "",
        "instagram": "fordav",
        "linkedin": "ford-audio-video-systems",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://www.fordav.com/locations/dallas/", "https://www.fordav.com/contact"],
    },
    {
        "no": 928,
        "country": "USA",
        "region": "North America",
        "company_en": "E.C. Pro Video",
        "company_local": "EC Pro Video Systems",
        "city": "New York, NY",
        "contact_name": "",
        "title": "",
        "email": "info@ecprovideo.com",
        "phone_whatsapp": "",
        "website": "ecprostore.com",
        "business": "Verified LED target: NYC (Midtown Manhattan) pro-video / broadcast / LED video wall dealer offering sales, rentals, systems integration and design. Email confirmed from ecprostore.com/pages/contact-us. Instagram @ecprovideo.",
        "facebook": "",
        "instagram": "ecprovideo",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://ecprostore.com/pages/led", "https://ecprostore.com/pages/contact-us"],
    },
    {
        "no": 929,
        "country": "USA",
        "region": "North America",
        "company_en": "Clearwing Systems Integration",
        "company_local": "Clearwing",
        "city": "Milwaukee, WI",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "",
        "website": "clearwing.com",
        "business": "Verified LED target: Milwaukee WI AV/lighting/audio systems integrator serving hotels, casinos and resorts with LED video wall and AV solutions. No public email (contact form only) -> IG DM channel. Instagram @clearwing.official.",
        "facebook": "",
        "instagram": "clearwing.official",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://clearwing.com/systems-hotels-casinos-resorts", "https://clearwing.com/contact"],
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
