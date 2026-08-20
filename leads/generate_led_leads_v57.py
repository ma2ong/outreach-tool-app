"""
generate_led_leads_v57.py
USA verified LED display batch: nos 769, 771-774 (5 leads)

Only verified LED display / LED screen / LED wall / video wall businesses are included.
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
    "v50", "v51", "v52", "v53", "v54", "v55", "v56",
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
        "no": 769,
        "country": "USA",
        "region": "North America",
        "company_en": "XR Stages LA",
        "company_local": "XR Stages LA",
        "city": "North Hollywood, CA",
        "contact_name": "",
        "title": "",
        "email": "contact@xrstagela.com",
        "phone_whatsapp": "+1 818 641 0220",
        "website": "xrstagela.com",
        "business": "Verified LED target: XR LED virtual production stage in North Hollywood with 30ft panoramic LED video wall, LED screen, LED wall rentals/sales/installations. Website states Phone/Text/WhatsApp 24/7: 818-641-0220.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": True,
    },
    {
        "no": 771,
        "country": "USA",
        "region": "North America",
        "company_en": "Smart LED Inc.",
        "company_local": "Smart LED Inc.",
        "city": "California, USA",
        "contact_name": "Sergio",
        "title": "",
        "email": "sergio@smartledinc.com",
        "phone_whatsapp": "1-800-762-0796",
        "website": "smartledinc.com",
        "business": "Verified LED target: direct-view indoor LED video wall display products, LED wall, LED screen and jumbotron display sales. Email sergio@smartledinc.com from product page.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 772,
        "country": "USA",
        "region": "North America",
        "company_en": "Los Angeles LED Rental",
        "company_local": "Los Angeles LED Rental",
        "city": "Los Angeles / Irvine, CA",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+1 949 338 6489",
        "website": "losangelesled.com",
        "business": "Verified LED target: Los Angeles LED Rental specializes in LED screen rental, LED video wall rental, LED display wall solutions, mobile LED wall rental and LED wall installs. IG @losangelesled, FB losangelesled.",
        "facebook": "losangelesled",
        "instagram": "losangelesled",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 773,
        "country": "USA",
        "region": "North America",
        "company_en": "Unity Logics",
        "company_local": "Unity Logics",
        "city": "Ontario / Los Angeles, CA",
        "contact_name": "",
        "title": "",
        "email": "info@unitylogics.com",
        "phone_whatsapp": "(951) 268-7773",
        "website": "unitylogics.com/los-angeles/led-screen-rental",
        "business": "Verified LED target: dedicated LED Screen Rental Los Angeles page; indoor LED walls, outdoor LED walls, mobile LED screens and custom LED video walls. IG @unitylogics, FB unitylogics.",
        "facebook": "unitylogics",
        "instagram": "unitylogics",
        "linkedin": "company/unity-logics",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 774,
        "country": "USA",
        "region": "North America",
        "company_en": "Show Production Miami",
        "company_local": "Show Production Miami",
        "city": "Miami, FL",
        "contact_name": "",
        "title": "",
        "email": "info@showproductionmiami.com",
        "phone_whatsapp": "+1 786 332 8646",
        "website": "showproductionmiami.com/av-equipment-rental",
        "business": "Verified LED target: AV rental page lists LED Screen Rental Miami, high-resolution LED video walls and displays. Website has WhatsApp link wa.me/17863328646. IG @showproductionmiami, FB showproductionmiami.",
        "facebook": "showproductionmiami",
        "instagram": "showproductionmiami",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": True,
        "whatsapp_link": "https://wa.me/17863328646",
    },
]

seen = set()
for lead in leads:
    for key in ("website", "email", "instagram", "facebook"):
        val = str(lead.get(key, "")).strip().lower()
        if val:
            seen.add(val)

for entry in new_entries:
    for key in ("website", "email", "instagram", "facebook"):
        val = str(entry.get(key, "")).strip().lower()
        if val and val in seen:
            raise SystemExit(f"Duplicate {key} found: {val}")

leads.extend(new_entries)

if __name__ == "__main__":
    usa_count = sum(1 for item in leads if item.get("country") == "USA")
    print(f"Total leads: {len(leads)}")
    print(f"USA leads: {usa_count}")
    for item in new_entries:
        print(f"{item['no']} | {item['company_en']} | email:{item['email']} | IG:{item['instagram']} | FB:{item['facebook']} | WA:{item.get('whatsapp_verified')}")
