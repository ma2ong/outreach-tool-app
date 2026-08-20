"""
generate_led_leads_v64.py
USA verified LED display batch: nos 814-823.
"""
import ast
import os
import re

BASE = os.path.dirname(__file__)


def _load(path):
    return open(path, encoding="utf-8").read()


src = _load(os.path.join(BASE, "generate_led_leads_v4.py"))
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", src, re.M | re.S).group(1))

for n in range(5, 64):
    path = os.path.join(BASE, f"generate_led_leads_v{n}.py")
    if not os.path.exists(path):
        continue
    text = _load(path)
    m = re.search(r"^new_entries = (\[.+?^\])", text, re.M | re.S)
    if m:
        leads.extend(ast.literal_eval(m.group(1)))


new_entries = [
    {
        "no": 814,
        "country": "USA",
        "region": "North America",
        "company_en": "Trailex LED Event Solutions",
        "company_local": "Trailex LED Event Solutions",
        "city": "Canfield, OH",
        "contact_name": "",
        "title": "",
        "email": "trailex1@aol.com",
        "phone_whatsapp": "+1 330 207 0818",
        "website": "trailexled.com",
        "business": "Verified LED target: Ohio company focused on FrontRow LED Display Trailers, high-resolution LED display trailers, mobile exposure LED panels and LED screen event solutions.",
        "facebook": "",
        "instagram": "trailexled_events",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 815,
        "country": "USA",
        "region": "North America",
        "company_en": "LED3",
        "company_local": "LED3 Displays",
        "city": "Canfield, OH",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+1 330 533 6988",
        "website": "led3showroom.com",
        "business": "Verified LED target: Ohio LED display company offering fixed indoor/outdoor LED displays, mobile LED displays, rental LED/staging, LED service and repair.",
        "facebook": "LED3Displays",
        "instagram": "led3displays",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 816,
        "country": "USA",
        "region": "North America",
        "company_en": "Big Screens On The Go",
        "company_local": "Big Screens On The Go",
        "city": "Fort Worth, TX",
        "contact_name": "",
        "title": "",
        "email": "GoBig@BigScreensOnTheGo.com",
        "phone_whatsapp": "+1 888 830 8011",
        "website": "bigscreensonthego.com",
        "business": "Verified LED target: full-service LED Jumbotron provider specializing in big screen LED display rentals and sales of LED video screens and mobile LED video trailers.",
        "facebook": "gobigscreens",
        "instagram": "bigscreensonthego",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 817,
        "country": "USA",
        "region": "North America",
        "company_en": "Brands In Motion",
        "company_local": "Brands In Motion",
        "city": "Nationwide USA",
        "contact_name": "",
        "title": "",
        "email": "info@BrandsInMotion.com",
        "phone_whatsapp": "+1 888 708 5558",
        "website": "brandsinmotion.com",
        "business": "Verified LED target: US digital mobile billboard network using high-visibility Jumbotron video screens and multiple LED screens on mobile advertising vehicles.",
        "facebook": "BrandsInMotionUSA",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 818,
        "country": "USA",
        "region": "North America",
        "company_en": "Rolling Outdoor Media",
        "company_local": "Rolling Outdoor Media",
        "city": "Los Angeles, CA",
        "contact_name": "",
        "title": "",
        "email": "info@rollingoutdoormedia.com",
        "phone_whatsapp": "+1 818 452 6526",
        "website": "rollingoutdoormedia.com",
        "business": "Verified LED target: US mobile billboard company using vehicles equipped with high-resolution LED display screens for dynamic mobile advertising.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 819,
        "country": "USA",
        "region": "North America",
        "company_en": "Mobile Billboard Miami",
        "company_local": "Mobile Billboard Miami",
        "city": "Hollywood / West Park, FL",
        "contact_name": "Steven Baptiste",
        "title": "",
        "email": "info@mobilebillboardmiami.com",
        "phone_whatsapp": "+1 305 814 5880",
        "website": "mobilebillboardmiami.com",
        "business": "Verified LED target: Florida company delivering digital LED billboard truck advertising, LED mobile billboard campaigns and mobile LED screen rental services.",
        "facebook": "mobilebillboardmiami",
        "instagram": "mobilebillboardmiami",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 820,
        "country": "USA",
        "region": "North America",
        "company_en": "DAT Media FL",
        "company_local": "DAT Media FL",
        "city": "Orlando, FL",
        "contact_name": "",
        "title": "",
        "email": "Info@bestadvertisingtruck.com",
        "phone_whatsapp": "+1 407 559 7065",
        "website": "datmediafl.com",
        "business": "Verified LED target: Central Florida mobile digital LED billboard advertising truck company using mobile LED billboard trucks for campaigns and events.",
        "facebook": "datmediafl",
        "instagram": "datmediafl",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 821,
        "country": "USA",
        "region": "North America",
        "company_en": "LED Truck Media",
        "company_local": "LED Truck Media",
        "city": "Canoga Park, CA",
        "contact_name": "",
        "title": "",
        "email": "sales@ledtruckmedia.com",
        "phone_whatsapp": "+1 917 224 3633",
        "website": "ledtruckmedia.com",
        "business": "Verified LED target: California-based mobile LED billboard truck and digital outdoor media company with mobile LED advertising trucks and high-impact LED display campaigns.",
        "facebook": "ledtruckmediaagency",
        "instagram": "ledtruckmedia",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 822,
        "country": "USA",
        "region": "North America",
        "company_en": "Lime Media",
        "company_local": "Lime Media",
        "city": "Rockwall, TX",
        "contact_name": "",
        "title": "",
        "email": "info@lime-media.com",
        "phone_whatsapp": "+1 972 475 1200",
        "website": "lime-media.com/services/led-billboard-trucks",
        "business": "Verified LED target: US experiential marketing company with nationwide mobile LED billboard truck advertising and one of the largest mobile LED truck fleets.",
        "facebook": "",
        "instagram": "limemediagroupinc",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 823,
        "country": "USA",
        "region": "North America",
        "company_en": "Ad Runner Trucks",
        "company_local": "Ad Runner",
        "city": "Seattle / Tacoma, WA",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+1 253 350 0804",
        "website": "adrunnertrucks.com",
        "business": "Verified LED target: mobile billboard truck company offering LED digital mobile billboard trucks across Seattle, Tacoma and West Coast markets.",
        "facebook": "runninads",
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
