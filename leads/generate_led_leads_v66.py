"""
generate_led_leads_v66.py
USA verified LED display / LED video wall batch: nos 833-841.
"""
import ast
import os
import re

BASE = os.path.dirname(__file__)


def _load(path):
    return open(path, encoding="utf-8").read()


src = _load(os.path.join(BASE, "generate_led_leads_v4.py"))
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", src, re.M | re.S).group(1))

for n in range(5, 66):
    path = os.path.join(BASE, f"generate_led_leads_v{n}.py")
    if not os.path.exists(path):
        continue
    text = _load(path)
    m = re.search(r"^new_entries = (\[.+?^\])", text, re.M | re.S)
    if m:
        leads.extend(ast.literal_eval(m.group(1)))


new_entries = [
    {
        "no": 833,
        "country": "USA",
        "region": "North America",
        "company_en": "Titan Production Group",
        "company_local": "Titan Production Group",
        "city": "Roswell / Cumming / Atlanta, GA",
        "contact_name": "",
        "title": "",
        "email": "info@titanproductiongroup.com",
        "phone_whatsapp": "+1 844 544 3786",
        "website": "titanproductiongroup.com",
        "business": "Verified LED target: Atlanta production company offering LED wall rental, P2.6mm LED video wall inventory, modular LED walls for indoor and outdoor events across the Southeast USA.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 834,
        "country": "USA",
        "region": "North America",
        "company_en": "BezaLED",
        "company_local": "BezaLED",
        "city": "USA",
        "contact_name": "",
        "title": "",
        "email": "info@bezaled.com",
        "phone_whatsapp": "+1 786 826 7016",
        "website": "bezaled.com",
        "business": "Verified LED target: US-based LED video wall company selling commercial LED video walls, fine-pitch indoor panels and outdoor stadium displays for churches, concerts and corporate spaces.",
        "facebook": "Bezaleddisplays",
        "instagram": "bezaleddisplays",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 835,
        "country": "USA",
        "region": "North America",
        "company_en": "Event Technology Rentals (Rentipads)",
        "company_local": "Event Technology Rentals",
        "city": "Nationwide USA",
        "contact_name": "",
        "title": "",
        "email": "info@rentipads.com",
        "phone_whatsapp": "+1 866 840 1472",
        "website": "rentipads.com/led-video-wall-rental",
        "business": "Verified LED target: nationwide event technology rental company offering LED video wall rentals, modular LED tile rentals, outdoor LED video walls and trade show LED display support.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 836,
        "country": "USA",
        "region": "North America",
        "company_en": "Access Audio",
        "company_local": "Access Audio",
        "city": "Cincinnati, OH",
        "contact_name": "",
        "title": "",
        "email": "info@accessaudio.com",
        "phone_whatsapp": "+1 513 771 1500",
        "website": "accessaudio.com",
        "business": "Verified LED target: Cincinnati event production company with Absen PL3.9 indoor/outdoor LED video wall rental inventory and LED wall services for events and drive-in worship.",
        "facebook": "AccessAudioInc",
        "instagram": "accessaudioinc",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 837,
        "country": "USA",
        "region": "North America",
        "company_en": "EventStarts",
        "company_local": "EventStarts",
        "city": "New York, NY / Nationwide USA",
        "contact_name": "",
        "title": "",
        "email": "mllegeorgesand@gmail.com",
        "phone_whatsapp": "+1 800 231 3132",
        "website": "eventstarts.com",
        "business": "Verified LED target: event production and rental company specializing in LED walls with 1.9mm, 2.6mm, 3.9mm and 4.8mm panels plus custom shaped LED screens.",
        "facebook": "eventstarts",
        "instagram": "eventstarts",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 838,
        "country": "USA",
        "region": "North America",
        "company_en": "Santiago Perez Productions",
        "company_local": "Santiago Perez Productions",
        "city": "Miami / Florida",
        "contact_name": "",
        "title": "",
        "email": "info@santiagoperezproductions.com",
        "phone_whatsapp": "+1 305 780 9409",
        "website": "santiagoperezproductions.com",
        "business": "Verified LED target: Florida event production company specializing in indoor/outdoor LED video wall rental and full audiovisual production across Miami, Fort Lauderdale, Naples, Orlando and Tampa.",
        "facebook": "santiagoperezproductions",
        "instagram": "santiagoperezproductions",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 839,
        "country": "USA",
        "region": "North America",
        "company_en": "Dionysus Creative",
        "company_local": "Dionysus Creative",
        "city": "Albuquerque, NM / Los Angeles, CA / North Bay, CA",
        "contact_name": "",
        "title": "",
        "email": "info@dionysuscreative.com",
        "phone_whatsapp": "+1 951 264 8339",
        "website": "dionysuscreative.com",
        "business": "Verified LED target: LED video wall integration and rental company offering Fabulux LED rentals, permanent installations, fine-pitch LED, virtual production and outdoor DOOH display solutions.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 840,
        "country": "USA",
        "region": "North America",
        "company_en": "Snell Vision",
        "company_local": "Snell Vision",
        "city": "Memphis, TN",
        "contact_name": "",
        "title": "",
        "email": "Info@snellvision.com",
        "phone_whatsapp": "+1 833 763 5563",
        "website": "snellvision.com",
        "business": "Verified LED target: Memphis company offering LED video wall rental and sales, LED screen wall panels and visual display solutions.",
        "facebook": "profile.php?id=61567277579790",
        "instagram": "snell_audio",
        "linkedin": "",
        "target_fit": "verified_led_display",
        "whatsapp_verified": False,
    },
    {
        "no": 841,
        "country": "USA",
        "region": "North America",
        "company_en": "Turning Point AV",
        "company_local": "Turning Point AV",
        "city": "Savannah, GA / Nationwide USA",
        "contact_name": "",
        "title": "",
        "email": "info@turningpointav.com",
        "phone_whatsapp": "+1 855 487 2811",
        "website": "turningpointav.com",
        "business": "Verified LED target: nationwide AV provider listing LED video wall rental, video equipment rental, conference AV and event production services.",
        "facebook": "TurningPointAV",
        "instagram": "turning_point_av",
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
