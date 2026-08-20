"""
generate_led_leads_v61.py
USA verified LED display batch: nos 792-797.
"""
import ast
import os
import re

BASE = os.path.dirname(__file__)


def _load(path):
    return open(path, encoding="utf-8").read()


src = _load(os.path.join(BASE, "generate_led_leads_v4.py"))
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", src, re.M | re.S).group(1))

for n in range(5, 61):
    path = os.path.join(BASE, f"generate_led_leads_v{n}.py")
    if not os.path.exists(path):
        continue
    text = _load(path)
    m = re.search(r"^new_entries = (\[.+?^\])", text, re.M | re.S)
    if m:
        leads.extend(ast.literal_eval(m.group(1)))


new_entries = [
    {
        "no": 792,
        "country": "USA",
        "region": "North America",
        "company_en": "Easy Audio Rental",
        "company_local": "Easy Audio Rental / TC Rentals LLC",
        "city": "Olathe / Kansas City, KS",
        "contact_name": "James Hansen",
        "title": "",
        "email": "james@jhansen.net",
        "phone_whatsapp": "+1 913 219 7475",
        "website": "easyaudiorental.com/video-wall",
        "business": "Verified LED target: Kansas City LED video wall rental page lists professional LED display rental services and turn-key 12-foot LED display wall packages.",
        "facebook": "easyaudiorental",
        "instagram": "easy_audio_rental_video_walls",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 793,
        "country": "USA",
        "region": "North America",
        "company_en": "Full Swing Productions",
        "company_local": "Full Swing Productions",
        "city": "Shakopee / Minneapolis, MN",
        "contact_name": "",
        "title": "",
        "email": "admin@fullswingpro.com",
        "phone_whatsapp": "+1 316 641 8913",
        "website": "fullswingpro.com",
        "business": "Verified LED target: Minnesota full-service LED provider specializing in high-resolution LED panels, video walls, digital signage, rentals, fixed installations and trade show displays.",
        "facebook": "61556137492975",
        "instagram": "full.swing.pro",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 794,
        "country": "USA",
        "region": "North America",
        "company_en": "Queen City Screens",
        "company_local": "Queen City Screens",
        "city": "Cincinnati, OH",
        "contact_name": "Shaun / Trace",
        "title": "",
        "email": "shaun@queencityscreens.com",
        "phone_whatsapp": "+1 513 275 8550",
        "website": "queencityscreens.com",
        "business": "Verified LED target: Cincinnati local leader of LED screen trailers and video walls for sporting events, concerts, social events, fundraisers and watch parties.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
        "secondary_email": "trace@queencityscreens.com",
        "secondary_phone": "+1 513 545 4754",
    },
    {
        "no": 795,
        "country": "USA",
        "region": "North America",
        "company_en": "Livestream Media Network",
        "company_local": "Livestream Media Network",
        "city": "San Antonio, TX",
        "contact_name": "",
        "title": "Sales",
        "email": "sales@livestreammedianetwork.com",
        "phone_whatsapp": "+1 210 993 9500",
        "website": "livestreammedianetwork.com",
        "business": "Verified LED target: San Antonio production company whose site lists LED video wall rentals / LEDi Video Wall Rentals, 19ft x 9ft 3.9mm LEDi wall pricing, and multi-cam livestream production.",
        "facebook": "livestreammedianetwork",
        "instagram": "livestreammedianetwork",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 796,
        "country": "USA",
        "region": "North America",
        "company_en": "OVOMEDIA Audio / Video Services",
        "company_local": "OVOAUDIOVIDEO",
        "city": "Myakka City / Sarasota, FL",
        "contact_name": "",
        "title": "",
        "email": "ovoaudiovideo@gmail.com",
        "phone_whatsapp": "+1 813 545 3312",
        "website": "ovomedia.live",
        "business": "Verified LED target: Central Florida LED video wall rental service featuring 4K 1.9-pixel indoor LED walls and high-resolution LED wall rentals since 2013.",
        "facebook": "",
        "instagram": "ovomedia.live",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 797,
        "country": "USA",
        "region": "North America",
        "company_en": "One Way Event Productions",
        "company_local": "One Way Event Productions",
        "city": "New York, NY",
        "contact_name": "",
        "title": "",
        "email": "WhatsUp@onewayep.com",
        "phone_whatsapp": "+1 914 770 7786",
        "website": "onewayeventproductions.com/led-rentals",
        "business": "Verified LED target: NYC AV/event production company with LED video wall and LED rentals pages for indoor/outdoor LED displays, LED totems and custom LED trade show booths.",
        "facebook": "1wayav",
        "instagram": "oneway_ep",
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
