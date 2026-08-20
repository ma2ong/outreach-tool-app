"""
generate_led_leads_v56.py
USA verified LED display batch: nos 759-768 (10 leads)

Rule: only include companies with explicit LED display / LED screen / LED wall / video wall rental,
sales, installation, or integration evidence on their own site.
"""
import ast
import os
import re

_base = os.path.dirname(__file__)


def _load(path):
    return open(path, encoding="utf-8").read()


_v4_src = _load(os.path.join(_base, "generate_led_leads_v4.py"))
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", _v4_src, re.M | re.S).group(1))

for _vname in (
    "v5", "v6", "v7", "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", "v16",
    "v17", "v18", "v19", "v20", "v21", "v22", "v23", "v24", "v25", "v26", "v27",
    "v28", "v29", "v30", "v31", "v32", "v33", "v34", "v35", "v36", "v37", "v38",
    "v39", "v40", "v41", "v42", "v43", "v44", "v45", "v46", "v47", "v48", "v49",
    "v50", "v51", "v52", "v53", "v54", "v55",
):
    _path = os.path.join(_base, f"generate_led_leads_{_vname}.py")
    if not os.path.exists(_path):
        continue
    _src = _load(_path)
    _m = re.search(r"^new_entries = (\[.+?^\])", _src, re.M | re.S)
    if _m:
        leads.extend(ast.literal_eval(_m.group(1)))


new_entries = [
    {
        "no": 759,
        "country": "USA",
        "region": "North America",
        "company_en": "Eden USA",
        "company_local": "Eden USA",
        "city": "Corona / Los Angeles, CA",
        "contact_name": "",
        "title": "",
        "email": "sales@edenusa.com",
        "phone_whatsapp": "+1 951 505 6967",
        "website": "edenusa.com/rent-video-wall/rent-video-wall",
        "business": "Verified LED target: dedicated rent-video-wall page; LED video wall rentals, LED screen rental, modular panels, indoor/outdoor video wall configurations for events. IG @edenusa.la, FB edenusainc.",
        "facebook": "edenusainc",
        "instagram": "edenusa.la",
        "linkedin": "",
        "target_fit": "verified_led_display",
    },
    {
        "no": 760,
        "country": "USA",
        "region": "North America",
        "company_en": "EuroLedwall USA",
        "company_local": "EuroLedwall USA",
        "city": "Los Angeles, CA",
        "contact_name": "",
        "title": "",
        "email": "info@euroledwallusa.com",
        "phone_whatsapp": "",
        "website": "euroledwallusa.com/ledwall-los-angeles",
        "business": "Verified LED target: specializes in LED wall and LED screen rentals for trade shows and fairs across the United States. IG @euroledwall, FB Euroledwall.",
        "facebook": "Euroledwall",
        "instagram": "euroledwall",
        "linkedin": "",
        "target_fit": "verified_led_display",
    },
    {
        "no": 761,
        "country": "USA",
        "region": "North America",
        "company_en": "Fidelis Sound & Lighting",
        "company_local": "Fidelis Sound & Lighting",
        "city": "Austin, TX",
        "contact_name": "Shawn",
        "title": "",
        "email": "info@fidelisatx.com",
        "phone_whatsapp": "(512) 762-9687",
        "website": "fidelisatx.com/led-video-wall-rental-austin-texas",
        "business": "Verified LED target: dedicated LED Video Wall Rental Austin page; LED wall rental, video walls, corporate event production, installations and rentals in Texas. IG @fidelisatx, FB fidelisatx.",
        "facebook": "fidelisatx",
        "instagram": "fidelisatx",
        "linkedin": "",
        "target_fit": "verified_led_display",
    },
    {
        "no": 762,
        "country": "USA",
        "region": "North America",
        "company_en": "AV America Florida",
        "company_local": "AV America",
        "city": "Orlando / Miami, FL",
        "contact_name": "",
        "title": "",
        "email": "info@av-america.com",
        "phone_whatsapp": "(321) 321-2922",
        "website": "fl.av-america.com",
        "business": "Verified LED target: site lists LED Wall Rental, LED video wall, giant LED wall rental, LED walls, projection mapping and AV production in Florida. IG @1avamerica, FB 1AvAmerica.",
        "facebook": "1AvAmerica",
        "instagram": "1avamerica",
        "linkedin": "",
        "target_fit": "verified_led_display",
    },
    {
        "no": 763,
        "country": "USA",
        "region": "North America",
        "company_en": "Digital Art Video",
        "company_local": "Digital Art Video",
        "city": "New Hyde Park / New York, NY",
        "contact_name": "",
        "title": "",
        "email": "production@digitalartvideo.com",
        "phone_whatsapp": "(718) 457-5388",
        "website": "digitalartvideo.com/usa/faq",
        "business": "Verified LED target: FAQ states LED wall rental and installation for conferences, concerts, corporate presentations and brand activations. IG @digitalartvideo, FB DigitalartVideo.",
        "facebook": "DigitalartVideo",
        "instagram": "digitalartvideo",
        "linkedin": "",
        "target_fit": "verified_led_display",
    },
    {
        "no": 764,
        "country": "USA",
        "region": "North America",
        "company_en": "One World Rental USA",
        "company_local": "One World Rental",
        "city": "Phoenix, AZ / USA nationwide",
        "contact_name": "",
        "title": "",
        "email": "sales@oneworldrental.com",
        "phone_whatsapp": "+1 602 737 0011",
        "website": "oneworldrental.com/audio-visual-hire",
        "business": "Verified LED target: AV hire page lists LED video walls, LED wall rental, LED display, LED screen and digital signage rental services across the USA. IG @oneworldrental.",
        "facebook": "",
        "instagram": "oneworldrental",
        "linkedin": "",
        "target_fit": "verified_led_display",
    },
    {
        "no": 765,
        "country": "USA",
        "region": "North America",
        "company_en": "Los Angeles LED Video Walls",
        "company_local": "Los Angeles LED Video Walls",
        "city": "Los Angeles, CA",
        "contact_name": "",
        "title": "",
        "email": "info@losangelesledvideowalls.com",
        "phone_whatsapp": "(213) 267-2151",
        "website": "losangelesledvideowalls.com",
        "business": "Verified LED target: dedicated LED video wall rental site for Los Angeles; rental, sales and service; trade shows, corporate events, exhibits, conferences and film/photography LED walls.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
    },
    {
        "no": 766,
        "country": "USA",
        "region": "North America",
        "company_en": "Pixals LED Screen Rental Los Angeles",
        "company_local": "Pixals",
        "city": "Los Angeles, CA",
        "contact_name": "",
        "title": "",
        "email": "hello@pixals.net",
        "phone_whatsapp": "",
        "website": "pixals.net/los-angeles/led-screen-rental",
        "business": "Verified LED target: dedicated LED screen rental page; LED video wall rental, modular LED panel rental, LED screen rental for film, fashion, concerts and brand activations. IG @pixals360.",
        "facebook": "",
        "instagram": "pixals360",
        "linkedin": "",
        "target_fit": "verified_led_display",
    },
    {
        "no": 767,
        "country": "USA",
        "region": "North America",
        "company_en": "Los Angeles Video Walls",
        "company_local": "Los Angeles Video Walls",
        "city": "Los Angeles, CA",
        "contact_name": "",
        "title": "",
        "email": "info@ledwallrentallosangeles.com",
        "phone_whatsapp": "",
        "website": "ledwallrentallosangeles.com",
        "business": "Verified LED target: LED screen rental in Los Angeles; premium LED screen rentals, LED video walls, jumbotrons, mobile LED trailers, digital billboard vans and event display solutions.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
    },
    {
        "no": 768,
        "country": "USA",
        "region": "North America",
        "company_en": "SergeiSolutions",
        "company_local": "SergeiSolutions",
        "city": "Los Angeles, CA",
        "contact_name": "Sergei",
        "title": "",
        "email": "info@sergeisolutions.com",
        "phone_whatsapp": "+1 818 277 3201",
        "website": "sergeisolutions.com",
        "business": "Verified LED target: luxury indoor LED video walls and outdoor pool LED screen installations across Beverly Hills, Malibu, Bel Air and greater Los Angeles. WhatsApp wa.me/18182773201.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
    },
]

seen_keys = set()
for lead in leads:
    for key in ("website", "email", "instagram", "facebook"):
        val = str(lead.get(key, "")).strip().lower()
        if val:
            seen_keys.add(val)

for entry in new_entries:
    for key in ("website", "email", "instagram", "facebook"):
        val = str(entry.get(key, "")).strip().lower()
        if val and val in seen_keys:
            raise SystemExit(f"Duplicate {key} found: {val}")

leads.extend(new_entries)

if __name__ == "__main__":
    usa_count = sum(1 for x in leads if x.get("country") == "USA")
    print(f"Total leads: {len(leads)}")
    print(f"USA leads: {usa_count}")
    print("New v56 entries:")
    for item in new_entries:
        print(f"  {item['no']} | {item['company_en']} | {item['email']} | IG:{item['instagram']} | FB:{item['facebook']} | WA:{item['phone_whatsapp']}")
