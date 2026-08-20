"""
generate_led_leads_v62.py
USA verified LED display batch: nos 798-803.
"""
import ast
import os
import re

BASE = os.path.dirname(__file__)


def _load(path):
    return open(path, encoding="utf-8").read()


src = _load(os.path.join(BASE, "generate_led_leads_v4.py"))
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", src, re.M | re.S).group(1))

for n in range(5, 62):
    path = os.path.join(BASE, f"generate_led_leads_v{n}.py")
    if not os.path.exists(path):
        continue
    text = _load(path)
    m = re.search(r"^new_entries = (\[.+?^\])", text, re.M | re.S)
    if m:
        leads.extend(ast.literal_eval(m.group(1)))


new_entries = [
    {
        "no": 798,
        "country": "USA",
        "region": "North America",
        "company_en": "LED Screen Rentals",
        "company_local": "LED Screen Rentals",
        "city": "Los Angeles / nationwide",
        "contact_name": "",
        "title": "Sales",
        "email": "sales@ledscreenrentals.net",
        "phone_whatsapp": "+1 833 403 0420",
        "website": "ledscreenrentals.net",
        "business": "Verified LED target: site is dedicated to LED screen, LED display and LED wall rentals, including mobile LED screens and modular indoor/outdoor LED screen rentals.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 799,
        "country": "USA",
        "region": "North America",
        "company_en": "Legion LED Trucks",
        "company_local": "Legion LED Trucks LLC",
        "city": "Bellevue, NE",
        "contact_name": "Jerry Teeter",
        "title": "CEO / Founder",
        "email": "",
        "phone_whatsapp": "+1 866 792 9533",
        "website": "ledtrucks.com",
        "business": "Verified LED target: US manufacturer and seller of mobile LED billboard trucks and LED trailers; site lists new/used LED trucks and trailers and LED screen truck education.",
        "facebook": "ledtrucks",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 800,
        "country": "USA",
        "region": "North America",
        "company_en": "FunFlicks Kentucky",
        "company_local": "FunFlicks LED & Inflatable Screen Rentals of Kentucky",
        "city": "Lexington / Louisville, KY",
        "contact_name": "Eric Thomas",
        "title": "Owner",
        "email": "funflickskentunky@gmail.com",
        "phone_whatsapp": "+1 859 869 9669",
        "website": "funflicks.com/projector-screen-rental-lexington",
        "business": "Verified LED target: Kentucky FunFlicks pages list LED screen rentals, local Lexington/Louisville LED screen service, trailer LED screens and local owner/contact details.",
        "facebook": "funflicks",
        "instagram": "funflicksusa",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 801,
        "country": "USA",
        "region": "North America",
        "company_en": "Royal AV Solutions",
        "company_local": "Royal AV Solutions",
        "city": "Seattle / Bellevue, WA",
        "contact_name": "",
        "title": "",
        "email": "info@royalavsolutions.com",
        "phone_whatsapp": "+1 206 580 3040",
        "website": "royalavsolutions.com",
        "business": "Verified LED target: Seattle / PNW event AV production company whose contact and service pages reference LED video wall rental and video wall rental for corporate events and productions.",
        "facebook": "royalavsolutions",
        "instagram": "royalavsolutions",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 802,
        "country": "USA",
        "region": "North America",
        "company_en": "Game Craze Party Rentals",
        "company_local": "Game Craze Party Rentals / FunFlicks Outdoor Movies",
        "city": "Norton / Akron / Cleveland, OH",
        "contact_name": "",
        "title": "",
        "email": "office@gamecrazeparty.com",
        "phone_whatsapp": "+1 330 752 2351",
        "website": "gamecrazeparty.com/rentals/led-screens/led-video-wall",
        "business": "Verified LED target: Northeast Ohio LED video wall rental page lists 14ft x 8ft professional LED video walls for corporate presentations, schools, churches, trade shows and outdoor events.",
        "facebook": "GameCrazeParty",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 803,
        "country": "USA",
        "region": "North America",
        "company_en": "Freedom Fun USA Dayton",
        "company_local": "Freedom Fun USA - Dayton",
        "city": "Franklin / Dayton, OH",
        "contact_name": "",
        "title": "",
        "email": "dayton@freedomfunusa.com",
        "phone_whatsapp": "+1 937 970 4386",
        "website": "freedomfunusa.com/category/led-screen-rentals-dayton-ohio",
        "business": "Verified LED target: Dayton LED Screen & Video Wall Rentals page lists 17ft x 10ft and 23ft x 13ft mobile LED screen rentals, event operators, and local Dayton contact details.",
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
