"""
Update all pipelines with v36 entries (nos 619-625)
"""
import json, datetime
from pathlib import Path

BASE = Path(__file__).parent
TODAY = datetime.date.today().isoformat()

ig_entries = [
    {"no": 619, "username": "elitedisplays",            "company_en": "Elite Displays",             "city": "Las Vegas, NV",  "country": "USA"},
    # no 620 LED Show Vision has no IG found — skip IG pipeline
    {"no": 621, "username": "verumavsolutions",         "company_en": "Verum AV Solutions",         "city": "Houston, TX",    "country": "USA"},
    {"no": 622, "username": "powerfactoryproductions",  "company_en": "Power Factory Productions",  "city": "Houston, TX",    "country": "USA"},
    {"no": 623, "username": "arizonastage",             "company_en": "Arizona Stage",              "city": "Scottsdale, AZ", "country": "USA"},
    {"no": 624, "username": "palmproductionsandevents", "company_en": "Palm Productions and Events","city": "Tampa, FL",      "country": "USA"},
    {"no": 625, "username": "empire_djs",               "company_en": "Empire AV",                  "city": "Orlando, FL",    "country": "USA"},
]

ig_path = BASE / "pipeline/instagram/prospects.json"
ig_data = json.load(open(ig_path, encoding="utf-8"))
existing_ig = {p["username"] for p in ig_data}
added_ig = 0
for e in ig_entries:
    if e["username"] not in existing_ig:
        ig_data.append({
            "no": e["no"],
            "username": e["username"],
            "company_en": e["company_en"],
            "city": e["city"],
            "country": e["country"],
            "status": "prospect",
            "warmup_done": False,
            "touch_count": 0,
            "dm_sent_date": None,
            "dm_message_preview": None,
            "added_date": TODAY,
        })
        added_ig += 1
        print(f"  IG added: @{e['username']}")
    else:
        print(f"  IG skip (exists): @{e['username']}")
json.dump(ig_data, open(ig_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"IG pipeline: +{added_ig} → total {len(ig_data)}")

email_entries = [
    {"no": 619, "company_en": "Elite Displays",             "email_to": "info@elitedisplays.com",            "city": "Las Vegas, NV"},
    {"no": 620, "company_en": "LED Show Vision",             "email_to": "connect@vitaeventsgroup.com",       "city": "Las Vegas, NV"},
    {"no": 621, "company_en": "Verum AV Solutions",         "email_to": "info@verumav.com",                  "city": "Houston, TX"},
    {"no": 622, "company_en": "Power Factory Productions",  "email_to": "info@powerfactorypro.com",          "city": "Houston, TX"},
    {"no": 623, "company_en": "Arizona Stage",              "email_to": "Jake@arizonastage.com",             "city": "Scottsdale, AZ"},
    {"no": 624, "company_en": "Palm Productions and Events","email_to": "hello@palmproductionsandevents.com","city": "Tampa, FL"},
    {"no": 625, "company_en": "Empire AV",                  "email_to": "info@empireentertainment.us",       "city": "Orlando, FL"},
]

email_path = BASE / "pipeline/email/prospects.json"
email_data = json.load(open(email_path, encoding="utf-8"))
existing_email_nos = {p["no"] for p in email_data}
added_email = 0
for e in email_entries:
    if e["no"] not in existing_email_nos:
        email_data.append({
            "no": e["no"],
            "company_en": e["company_en"],
            "email_to": e["email_to"],
            "country": "USA",
            "city": e["city"],
            "status": "prospect",
            "touch_count": 0,
            "email_sent_date": None,
            "added_date": TODAY,
        })
        added_email += 1
        print(f"  Email added: no:{e['no']} → {e['email_to']}")
    else:
        print(f"  Email skip (exists): no:{e['no']}")
json.dump(email_data, open(email_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"Email pipeline: +{added_email} → total {len(email_data)}")

print("\nDone.")
