"""
generate_led_leads_v70.py
USA verified LED display / LED video wall batch: nos 867-871.
"""
import ast
import os
import re

BASE = os.path.dirname(__file__)


def _load(path):
    return open(path, encoding="utf-8").read()


src = _load(os.path.join(BASE, "generate_led_leads_v4.py"))
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", src, re.M | re.S).group(1))

for n in range(5, 70):
    path = os.path.join(BASE, f"generate_led_leads_v{n}.py")
    if not os.path.exists(path):
        continue
    text = _load(path)
    m = re.search(r"^new_entries = (\[.+?^\])", text, re.M | re.S)
    if m:
        leads.extend(ast.literal_eval(m.group(1)))


new_entries = [
    {
        "no": 867,
        "country": "USA",
        "region": "North America",
        "company_en": "Metat3ch",
        "company_local": "MetaT3ch",
        "city": "Nationwide USA",
        "contact_name": "",
        "title": "",
        "email": "info@metat3ch.com",
        "phone_whatsapp": "+1 469 232 7039",
        "website": "metat3ch.com",
        "business": "Verified LED target: event production and scenic company specializing in LED video walls, LED displays, LED floor systems, LED video wall rental, repairs and visual systems for trade shows, corporate events and live production.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 868,
        "country": "USA",
        "region": "North America",
        "company_en": "Reventals",
        "company_local": "Reventals",
        "city": "New Orleans / Nationwide USA",
        "contact_name": "",
        "title": "",
        "email": "info@reventals.com",
        "phone_whatsapp": "+1 888 857 0071",
        "website": "reventals.com",
        "business": "Verified LED target: event rental marketplace / provider with a dedicated LED Video Wall rental listing for New Orleans and surrounding areas, plus quote support for other cities.",
        "facebook": "reventals",
        "instagram": "reventals",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 869,
        "country": "USA",
        "region": "North America",
        "company_en": "GC Event Studio",
        "company_local": "GC Event Studio",
        "city": "Los Angeles, CA / Nationwide",
        "contact_name": "",
        "title": "",
        "email": "hey@gceventstudio.com",
        "phone_whatsapp": "+1 844 844 4160",
        "website": "gceventstudio.com",
        "business": "Verified LED target: event studio with a dedicated LED Video Wall Rentals page for corporate events, brand activations, weddings and concerts, including turnkey LED video wall setup and support.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 870,
        "country": "USA",
        "region": "North America",
        "company_en": "Fox Audio Visual",
        "company_local": "Fox Audio Visual",
        "city": "North Charleston, SC",
        "contact_name": "Joseph",
        "title": "",
        "email": "joseph@foxaudiovisual.com",
        "phone_whatsapp": "+1 843 608 9473",
        "website": "foxaudiovisual.com",
        "business": "Verified LED target: Charleston AV production company offering LED wall rentals, mobile LED video displays, live streaming and event production services across South Carolina, Georgia and the Southeast.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 871,
        "country": "USA",
        "region": "North America",
        "company_en": "Eciruam",
        "company_local": "Eciruam LLC",
        "city": "Las Vegas, NV",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+1 702 900 9795",
        "website": "eciruam.com",
        "business": "Verified LED target: Las Vegas event production company listed for custom stage set design, AV recording, live streaming, pro lighting and audio equipment, and LED video wall rental.",
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
