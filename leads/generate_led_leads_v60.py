"""
generate_led_leads_v60.py
USA verified LED display batch: nos 784-791.
"""
import ast
import os
import re

BASE = os.path.dirname(__file__)


def _load(path):
    return open(path, encoding="utf-8").read()


src = _load(os.path.join(BASE, "generate_led_leads_v4.py"))
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", src, re.M | re.S).group(1))

for n in range(5, 60):
    path = os.path.join(BASE, f"generate_led_leads_v{n}.py")
    if not os.path.exists(path):
        continue
    text = _load(path)
    m = re.search(r"^new_entries = (\[.+?^\])", text, re.M | re.S)
    if m:
        leads.extend(ast.literal_eval(m.group(1)))


new_entries = [
    {
        "no": 784,
        "country": "USA",
        "region": "North America",
        "company_en": "Evix Rentals",
        "company_local": "Evix Rentals",
        "city": "New Jersey / New York",
        "contact_name": "",
        "title": "",
        "email": "info@evixrentals.com",
        "phone_whatsapp": "+1 908 801 6359",
        "website": "evixrentals.com",
        "business": "Verified LED target: professional LED wall rentals in NJ and NY; 2.5 pixel pitch LED wall rental with delivery, setup, teardown and on-site support.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 785,
        "country": "USA",
        "region": "North America",
        "company_en": "AVPLED",
        "company_local": "AVP LED Technology",
        "city": "Hialeah / Miami / Orlando, FL",
        "contact_name": "",
        "title": "",
        "email": "info@avpled.com",
        "phone_whatsapp": "+1 786 348 4240",
        "website": "avpled.com",
        "business": "Verified LED target: South Florida AV production with LED wall rentals, indoor P2.6 and outdoor P4.8 LED video wall inventory; official WhatsApp link api.whatsapp.com/send?phone=7863484240.",
        "facebook": "avpledtech",
        "instagram": "avp.led",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": True,
        "whatsapp_link": "https://api.whatsapp.com/send?phone=7863484240",
    },
    {
        "no": 786,
        "country": "USA",
        "region": "North America",
        "company_en": "Stage Kings",
        "company_local": "Stage Kings Inc.",
        "city": "New York, NY",
        "contact_name": "",
        "title": "",
        "email": "info@StageKings.com",
        "phone_whatsapp": "+1 212 924 2147",
        "website": "stagekings.com/led-screen-rental",
        "business": "Verified LED target: NYC LED screen rental and integrated video wall rental systems for indoor/outdoor events, brand activations, trade shows and live productions.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 787,
        "country": "USA",
        "region": "North America",
        "company_en": "DJ Peoples",
        "company_local": "DJ Peoples",
        "city": "Miami / Fort Lauderdale, FL",
        "contact_name": "",
        "title": "",
        "email": "Rentals@DJPeoples.com",
        "phone_whatsapp": "+1 786 655 8386",
        "website": "djpeoples.com",
        "business": "Verified LED target: Miami event production and AV rentals with LED video wall packages, LED video wall rental and visual rental services.",
        "facebook": "",
        "instagram": "djpeoples",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 788,
        "country": "USA",
        "region": "North America",
        "company_en": "Geeksblock AV Services",
        "company_local": "Geeksblock",
        "city": "Miami, FL",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+1 786 305 4635",
        "website": "geeksblock.com/av-services",
        "business": "Verified LED target: Miami AV services page lists LED video wall rental with P2.97 outdoor LED wall, IP65 rating and event AV packages.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 789,
        "country": "USA",
        "region": "North America",
        "company_en": "FreqMode AV",
        "company_local": "FreqMode",
        "city": "Dallas, TX",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+1 214 327 3697",
        "website": "freqmodeav.com",
        "business": "Verified LED target: Dallas LED walls and pro audio company; site lists LED screen rates, LED video walls and official wa.me chat link.",
        "facebook": "",
        "instagram": "freqmode.av",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": True,
        "whatsapp_link": "https://wa.me/12143273697",
    },
    {
        "no": 790,
        "country": "USA",
        "region": "North America",
        "company_en": "ByteGraph Productions Audio Visual",
        "company_local": "ByteGraph Productions Audio Visual",
        "city": "Atlanta, GA / Dallas, TX / Santa Clara, CA",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+1 770 360 7777",
        "website": "bytegraph.com/led-walls",
        "business": "Verified LED target: LED screen, LED wall and video wall rentals available in Atlanta, Dallas, Chicago and New York; inventory includes 4mm indoor/outdoor LED wall and 2.8mm/2.0mm indoor LED wall.",
        "facebook": "ByteGraph",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 791,
        "country": "USA",
        "region": "North America",
        "company_en": "Visualize Productions",
        "company_local": "Visualize Productions",
        "city": "Adkins / San Antonio, TX",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+1 702 858 2904",
        "website": "visualizeproductions.co",
        "business": "Verified LED target: LED wall rentals trusted by AV companies; serves San Antonio, Austin, Corpus Christi, Houston, Dallas and El Paso; lists MR RS Series R2S 2.6P LED wall pricing and video wall technician support.",
        "facebook": "",
        "instagram": "",
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
