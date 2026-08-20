"""
generate_led_leads_v78.py
USA verified LED display / LED video wall integrators, cross-hire rental
partners & fixed-install firms: nos 910-918.
Vertical focus: sub-rental/cross-hire partners, digital-signage integrators,
sports-bar/restaurant fixed installs, MicroLED dealers.
"""
import ast
import os
import re

BASE = os.path.dirname(__file__)


def _load(path):
    return open(path, encoding="utf-8").read()


src = _load(os.path.join(BASE, "generate_led_leads_v4.py"))
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", src, re.M | re.S).group(1))

for n in range(5, 78):
    path = os.path.join(BASE, f"generate_led_leads_v{n}.py")
    if not os.path.exists(path):
        continue
    text = _load(path)
    m = re.search(r"^new_entries = (\[.+?^\])", text, re.M | re.S)
    if m:
        leads.extend(ast.literal_eval(m.group(1)))


new_entries = [
    {
        "no": 910,
        "country": "USA",
        "region": "North America",
        "company_en": "APG Rentals",
        "company_local": "APG Rentals",
        "city": "Orlando, FL",
        "contact_name": "",
        "title": "",
        "email": "rentals@apgrents.com",
        "phone_whatsapp": "+1 800 350 0562",
        "website": "apgrents.com",
        "business": "Verified LED target: cross-hire / sub-rental partner specializing in LED & LCD videowall and large-format display rentals nationwide (two decades, exclusive Sub-Rental Partner Program for staging companies). HQ Orlando FL + Toronto office. Email confirmed from apgrents.com/contact. Instagram @apgrentals.",
        "facebook": "",
        "instagram": "apgrentals",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://apgrents.com/contact/", "https://www.apgrents.com/"],
    },
    {
        "no": 911,
        "country": "USA",
        "region": "North America",
        "company_en": "Coffman Media",
        "company_local": "Coffman Media",
        "city": "Dublin, OH",
        "contact_name": "",
        "title": "",
        "email": "sales@coffmanmedia.com",
        "phone_whatsapp": "",
        "website": "coffmanmedia.com",
        "business": "Verified LED target: national digital-signage integrator offering end-to-end direct-view LED video wall design, installation and managed services across all 50 states. HQ Dublin OH. Email confirmed from coffmanmedia.com/contact-us.",
        "facebook": "",
        "instagram": "",
        "linkedin": "coffman-media",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://www.coffmanmedia.com/digital-signage/direct-view-led", "https://www.coffmanmedia.com/contact-us"],
    },
    {
        "no": 912,
        "country": "USA",
        "region": "North America",
        "company_en": "Soflo Systems",
        "company_local": "Soflo Systems Audio Visual",
        "city": "Miami, FL",
        "contact_name": "",
        "title": "",
        "email": "info@soflosystems.com",
        "phone_whatsapp": "",
        "website": "soflosystems.com",
        "business": "Verified LED target: Miami FL audio-visual integrator providing LED video wall installation for commercial and hospitality clients. Email confirmed from lunissystems.com/contact (brand also operates lunissystems.com).",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://lunissystems.com/audio-video-services/led-video-wall-installation-miami/", "https://lunissystems.com/contact"],
    },
    {
        "no": 913,
        "country": "USA",
        "region": "North America",
        "company_en": "Jireh Supplies",
        "company_local": "Jireh Supplies, Inc.",
        "city": "Lawrenceville, GA",
        "contact_name": "",
        "title": "",
        "email": "sales@jirehsupplies.com",
        "phone_whatsapp": "",
        "website": "jirehsupplies.com",
        "business": "Verified LED target: video wall installation, design and integration company serving GA, NC, SC, FL, AL, TN (education, houses of worship, commercial AV). HQ Lawrenceville GA. Email confirmed from jirehsupplies.com/contact-us. Facebook jirehsuppliesinc.",
        "facebook": "jirehsuppliesinc",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://www.jirehsupplies.com/video-wall-displays/", "https://www.jirehsupplies.com/contact-us"],
    },
    {
        "no": 914,
        "country": "USA",
        "region": "North America",
        "company_en": "BCI Integrated Solutions",
        "company_local": "BCI Integrated Solutions",
        "city": "Fort Lauderdale, FL",
        "contact_name": "",
        "title": "",
        "email": "service@bcifl.net",
        "phone_whatsapp": "",
        "website": "bcifl.net",
        "business": "Verified LED target: integrator installing Direct View LED video walls and digital signage; offices across FL, GA, TX, SD, ND, IA, MN, NE. Email confirmed from bcifl.net/contact-us.",
        "facebook": "",
        "instagram": "",
        "linkedin": "bci-integrated-solutions",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://bcifl.net/video-walls", "https://bcifl.net/contact-us"],
    },
    {
        "no": 915,
        "country": "USA",
        "region": "North America",
        "company_en": "ComSat AV",
        "company_local": "ComSat AV",
        "city": "San Diego, CA",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+1 619 795 9444",
        "website": "comsatav.com",
        "business": "Verified LED target: San Diego CA integrator specializing in museum-quality direct-view LED video walls, installed nationwide. No public email (contact form/phone only) -> IG/FB DM channel. Phone confirmed from comsatav.com/contact.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://comsatav.com/video-walls/", "https://comsatav.com/contact/"],
    },
    {
        "no": 916,
        "country": "USA",
        "region": "North America",
        "company_en": "McCann Systems",
        "company_local": "McCann Systems",
        "city": "Edgewood, NJ",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "",
        "website": "mccannsystems.com",
        "business": "Verified LED target: national AV integrator designing and installing custom-resolution LED video walls for corporate, sportsbook and hospitality venues. Contact-form only -> IG DM channel. Instagram @mccannsystems.",
        "facebook": "",
        "instagram": "mccannsystems",
        "linkedin": "mccann-systems",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://mccannsystems.com/led-video-walls/", "https://mccannsystems.com/contact-us/"],
    },
    {
        "no": 917,
        "country": "USA",
        "region": "North America",
        "company_en": "Just Video Walls",
        "company_local": "Just Video Walls",
        "city": "USA (multi-region)",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "",
        "website": "justvideowalls.com",
        "business": "Verified LED target: builds MicroLED / direct-view LED video wall systems for residential and commercial clients via a nationwide dealer network. Contact form only -> IG DM channel. Instagram @justvideowalls.",
        "facebook": "",
        "instagram": "justvideowalls",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://justvideowalls.com/", "https://justvideowalls.com/contact"],
    },
    {
        "no": 918,
        "country": "USA",
        "region": "North America",
        "company_en": "MSS Aesthetix",
        "company_local": "MSS Aesthetix",
        "city": "Houston, TX",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "",
        "website": "mssaesthetix.com",
        "business": "Verified LED target: Houston TX LED screen & video wall installation specialist for sports bars and venues. Contact form only -> IG/FB DM channel.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "source_urls": ["https://mssaesthetix.com/sports/", "https://mssaesthetix.com/contact"],
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
