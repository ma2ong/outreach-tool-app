"""
generate_led_leads_v65.py
USA verified LED display / mobile LED truck batch: nos 824-832.
"""
import ast
import os
import re

BASE = os.path.dirname(__file__)


def _load(path):
    return open(path, encoding="utf-8").read()


src = _load(os.path.join(BASE, "generate_led_leads_v4.py"))
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", src, re.M | re.S).group(1))

for n in range(5, 65):
    path = os.path.join(BASE, f"generate_led_leads_v{n}.py")
    if not os.path.exists(path):
        continue
    text = _load(path)
    m = re.search(r"^new_entries = (\[.+?^\])", text, re.M | re.S)
    if m:
        leads.extend(ast.literal_eval(m.group(1)))


new_entries = [
    {
        "no": 824,
        "country": "USA",
        "region": "North America",
        "company_en": "MVS Media Group",
        "company_local": "MVS Media Group",
        "city": "Hallandale Beach, FL / Nationwide USA",
        "contact_name": "Alex",
        "title": "",
        "email": "sales@mvsmediagroup.com",
        "phone_whatsapp": "+1 877 728 9631",
        "website": "mvsmediagroup.com",
        "business": "Verified LED target: US mobile digital billboard company with high-resolution LED trucks, live streaming capability, nationwide truck coverage and mobile LED billboard campaigns.",
        "facebook": "MOBILELEDBILLBOARD",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 825,
        "country": "USA",
        "region": "North America",
        "company_en": "LEDTRUCK.COM",
        "company_local": "LEDTRUCK.COM",
        "city": "Yonkers, NY / Los Angeles, CA",
        "contact_name": "",
        "title": "",
        "email": "sales@ledtruck.com",
        "phone_whatsapp": "+1 213 814 3138",
        "website": "ledtruck.com",
        "business": "Verified LED target: LED truck advertising company with United States offices in New York and Los Angeles, offering mobile digital billboard campaigns on LED trucks.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 826,
        "country": "USA",
        "region": "North America",
        "company_en": "Mobile LED Trucks",
        "company_local": "Mobile LED Trucks",
        "city": "Moreno Valley, CA / Nationwide USA",
        "contact_name": "",
        "title": "",
        "email": "info@mobileledtrucks.com",
        "phone_whatsapp": "+1 437 979 4769",
        "website": "mobileledtrucks.com",
        "business": "Verified LED target: US-based digital advertising company specializing in mobile LED billboard trucks, LED media vans and mobile screen campaigns across major US markets.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 827,
        "country": "USA",
        "region": "North America",
        "company_en": "Advanced Mobile LED",
        "company_local": "Advanced Mobile LED",
        "city": "Pompano Beach, FL",
        "contact_name": "Allen Simkovitch",
        "title": "Director of Sales",
        "email": "allen@advancedmobileled.com",
        "phone_whatsapp": "+1 786 580 8624",
        "website": "advancedmobileled.com",
        "business": "Verified LED target: Florida mobile digital billboard company with a fleet of custom-built LED advertising vehicles for local, regional and national campaigns.",
        "facebook": "advancedmobileled",
        "instagram": "advancedmobileled",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 828,
        "country": "USA",
        "region": "North America",
        "company_en": "Unlimited Mobile LED",
        "company_local": "Unlimited Mobile LED",
        "city": "Miami, FL",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+1 786 389 1438",
        "website": "unlimitedmobileled.com",
        "business": "Verified LED target: Miami company providing static and digital LED mobile billboard trucks, live TV broadcasting capability and mobile LED truck advertising.",
        "facebook": "",
        "instagram": "unlimitedmobileled",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 829,
        "country": "USA",
        "region": "North America",
        "company_en": "DMS LED Trucks",
        "company_local": "DMS LED Trucks",
        "city": "New York / New Jersey / Northeast USA",
        "contact_name": "",
        "title": "",
        "email": "info@dmsledtruck.com",
        "phone_whatsapp": "+1 516 912 8940",
        "website": "dmsledtruck.com",
        "business": "Verified LED target: digital outdoor advertising company using mobile advertising vehicles built with full-color LED screen technology and multiple digital screens.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 830,
        "country": "USA",
        "region": "North America",
        "company_en": "Lux Media",
        "company_local": "Lux Media",
        "city": "Dallas, TX / Nationwide USA",
        "contact_name": "",
        "title": "",
        "email": "ads@theluxtruck.com",
        "phone_whatsapp": "+1 469 389 0046",
        "website": "theluxtruck.com",
        "business": "Verified LED target: Dallas-based mobile LED billboard truck advertising company serving all 50 states with high-resolution digital LED billboard trucks.",
        "facebook": "",
        "instagram": "luxmediaads",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 831,
        "country": "USA",
        "region": "North America",
        "company_en": "Nomadic Genius",
        "company_local": "Nomadic Genius",
        "city": "Nashville, TN / Multi-state USA",
        "contact_name": "Regis",
        "title": "",
        "email": "regis@nomadicgenius.com",
        "phone_whatsapp": "+1 615 336 6678",
        "website": "nomadicgenius.com",
        "business": "Verified LED target: Nashville mobile billboard company specializing in LED mobile billboards, LED billboard truck advertising and a LED billboard truck sales division.",
        "facebook": "nomadicgeniusadvertisingcompany",
        "instagram": "the_billboard_guy",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 832,
        "country": "USA",
        "region": "North America",
        "company_en": "American Guerrilla Marketing",
        "company_local": "American Guerrilla Marketing",
        "city": "Brooklyn, NY / Nationwide USA",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+1 917 444 1065",
        "website": "americanguerillamarketing.com",
        "business": "Verified LED target: US guerrilla marketing agency with dedicated LED billboard truck services, mobile LED advertising trucks and WhatsApp contact option for LED billboard truck inquiries.",
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
