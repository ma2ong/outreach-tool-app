"""
generate_led_leads_v67.py
USA verified LED display / LED video wall batch: nos 842-850.
"""
import ast
import os
import re

BASE = os.path.dirname(__file__)


def _load(path):
    return open(path, encoding="utf-8").read()


src = _load(os.path.join(BASE, "generate_led_leads_v4.py"))
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", src, re.M | re.S).group(1))

for n in range(5, 67):
    path = os.path.join(BASE, f"generate_led_leads_v{n}.py")
    if not os.path.exists(path):
        continue
    text = _load(path)
    m = re.search(r"^new_entries = (\[.+?^\])", text, re.M | re.S)
    if m:
        leads.extend(ast.literal_eval(m.group(1)))


new_entries = [
    {
        "no": 842,
        "country": "USA",
        "region": "North America",
        "company_en": "Crispy Audio",
        "company_local": "Crispy Audio",
        "city": "San Francisco Bay Area, CA",
        "contact_name": "",
        "title": "",
        "email": "info@crispyaudio.com",
        "phone_whatsapp": "+1 925 222 4155",
        "website": "crispyaudio.com",
        "business": "Verified LED target: Bay Area AV rental and event production company offering high-resolution LED wall and video wall rental for corporate events, concerts, private parties and brand activations.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 843,
        "country": "USA",
        "region": "North America",
        "company_en": "PEAK Technologies",
        "company_local": "PEAK Technologies",
        "city": "Las Vegas, NV",
        "contact_name": "",
        "title": "",
        "email": "info@peakt.com",
        "phone_whatsapp": "",
        "website": "peakt.com",
        "business": "Verified LED target: Las Vegas trade show and corporate event provider building custom LED video walls with 1.2mm to 3.9mm pixel pitch, on-site engineers and local Vegas warehouse support.",
        "facebook": "PEAKtech.pro",
        "instagram": "peaktechnologies",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 844,
        "country": "USA",
        "region": "North America",
        "company_en": "Las Vegas LED Walls",
        "company_local": "Las Vegas LED Video Walls",
        "city": "Las Vegas, NV",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+1 702 351 9986",
        "website": "lasvegasledwalls.com",
        "business": "Verified LED target: local Las Vegas LED video wall rental company serving Southern Nevada with indoor and outdoor LED walls for trade shows, concerts, festivals, church events and corporate events.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 845,
        "country": "USA",
        "region": "North America",
        "company_en": "Murray Scott Production Services",
        "company_local": "MSPS Global",
        "city": "Phoenix, AZ",
        "contact_name": "",
        "title": "",
        "email": "info@mspsglobal.com",
        "phone_whatsapp": "+1 602 600 2056",
        "website": "mspsglobal.com",
        "business": "Verified LED target: Phoenix live and virtual event production company specializing in LED wall rental, digital display screen rental and high-broadcast-quality rental LED video walls for corporate events.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 846,
        "country": "USA",
        "region": "North America",
        "company_en": "Brightlight Film",
        "company_local": "American Brightlight Film Productions",
        "city": "Los Angeles, CA",
        "contact_name": "",
        "title": "",
        "email": "info@Brightlightfilm.us",
        "phone_whatsapp": "+1 929 300 1763",
        "website": "brightlightfilm.us",
        "business": "Verified LED target: Los Angeles virtual production studio with advanced curved LED wall, P1.53 GOB LED panels, chroma studio and LED video wall rental for cinematic production.",
        "facebook": "profile.php?id=61580212823419",
        "instagram": "american_brightlight_film",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 847,
        "country": "USA",
        "region": "North America",
        "company_en": "Riverside LED Video Walls",
        "company_local": "Riverside LED Video Walls",
        "city": "Riverside / Southern California",
        "contact_name": "",
        "title": "",
        "email": "info@riversideledvideowalls.com",
        "phone_whatsapp": "+1 909 527 6761",
        "website": "riversideledvideowalls.com",
        "business": "Verified LED target: Southern California LED video wall rental and sales company offering indoor, outdoor and curved LED video walls for trade shows, corporate meetings, concerts and festivals.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 848,
        "country": "USA",
        "region": "North America",
        "company_en": "Audio Design Rentals",
        "company_local": "Audio Design Rentals",
        "city": "San Diego, CA",
        "contact_name": "",
        "title": "",
        "email": "info@audiodesignrentals.com",
        "phone_whatsapp": "+1 619 286 4580",
        "website": "audiodesignrentals.com",
        "business": "Verified LED target: San Diego AV rental company with thousands of indoor/outdoor LED video wall panels, curved and creative LED builds, LED columns and large-format LED backdrops.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 849,
        "country": "USA",
        "region": "North America",
        "company_en": "RCC Events",
        "company_local": "Red Carpet Connections Events",
        "city": "Los Angeles, CA",
        "contact_name": "",
        "title": "",
        "email": "info@rccevent.com",
        "phone_whatsapp": "+1 818 983 5788",
        "website": "rccevent.com",
        "business": "Verified LED target: Los Angeles event rental company specializing in LED video screen and LED video wall rentals for premieres, live events, concerts, conferences and festivals.",
        "facebook": "RedCarpetConnectionsEventRentals",
        "instagram": "rccevent",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 850,
        "country": "USA",
        "region": "North America",
        "company_en": "Angels Music Productions",
        "company_local": "Angels Music Productions",
        "city": "Los Angeles / Orange County, CA",
        "contact_name": "",
        "title": "",
        "email": "info@angelsmusic.net",
        "phone_whatsapp": "+1 949 394 2572",
        "website": "angelsmusic.net",
        "business": "Verified LED target: Southern California event production company with a dedicated LED screen rental page for P3.9 and P2.6 LED screen / video wall rental in Los Angeles.",
        "facebook": "angelsmusicdjs",
        "instagram": "angelsmusicproductions",
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
