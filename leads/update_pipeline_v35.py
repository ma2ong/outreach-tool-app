"""
Update all three pipelines with v35 entries (nos 611-618)
"""
import json, datetime
from pathlib import Path

BASE = Path(__file__).parent
TODAY = datetime.date.today().isoformat()

# ── IG pipeline ──────────────────────────────────────────────────────────────
ig_entries = [
    {"no": 611, "username": "paentertainmentgroup", "company_en": "PA Entertainment Group", "city": "Harrisburg, PA", "country": "USA"},
    {"no": 612, "username": "miteyav",              "company_en": "Mitey AV",               "city": "New Orleans, LA","country": "USA"},
    {"no": 613, "username": "getrefreshled",        "company_en": "Refresh LED",            "city": "Mechanicsburg, PA","country": "USA"},
    {"no": 614, "username": "worshipproductions",   "company_en": "Worship Productions",    "city": "Yorba Linda, CA", "country": "USA"},
    {"no": 615, "username": "cprmms",               "company_en": "CPR MultiMedia Solutions","city": "Gaithersburg, MD","country": "USA"},
    {"no": 616, "username": "mediaquestpgh",        "company_en": "MediaQuest",             "city": "Pittsburgh, PA",  "country": "USA"},
    {"no": 617, "username": "vortexledwall",        "company_en": "Vortex LED Wall",        "city": "San Diego, CA",   "country": "USA"},
    {"no": 618, "username": "theoneupgroup",        "company_en": "The One Up Group",       "city": "West Hollywood, CA","country": "USA"},
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
print(f"IG pipeline: +{added_ig} entries → total {len(ig_data)}")

# ── WA pipeline ──────────────────────────────────────────────────────────────
wa_entries = [
    {
        "no": 612,
        "country": "USA",
        "company_en": "Mitey AV",
        "city": "New Orleans, LA",
        "phone": "+15042665681",
        "email": "events@miteyav.com",
        "instagram": "miteyav",
        "facebook": "miteyav",
        "website": "https://miteyav.com",
        "platform": "whatsapp",
        "username": "+15042665681",
        "status": "prospect",
        "touch_count": 0,
        "message_sent_date": None,
        "message_channel": None,
        "added_date": TODAY,
        "exclude_reason": None,
        "mobile_confirmed": True,
        "email_to": "events@miteyav.com",
    },
    {
        "no": 618,
        "country": "USA",
        "company_en": "The One Up Group",
        "city": "West Hollywood, CA",
        "phone": "+13106662250",
        "email": "Events@TheOneUpGroup.com",
        "instagram": "theoneupgroup",
        "facebook": "theoneupgroup",
        "website": "https://theoneupgroup.com",
        "platform": "whatsapp",
        "username": "+13106662250",
        "status": "prospect",
        "touch_count": 0,
        "message_sent_date": None,
        "message_channel": None,
        "added_date": TODAY,
        "exclude_reason": None,
        "mobile_confirmed": True,
        "email_to": "Events@TheOneUpGroup.com",
    },
]

wa_path = BASE / "pipeline/whatsapp/prospects.json"
wa_data = json.load(open(wa_path, encoding="utf-8"))
existing_wa_nos = {p["no"] for p in wa_data}
added_wa = 0
for e in wa_entries:
    if e["no"] not in existing_wa_nos:
        wa_data.append(e)
        added_wa += 1
        print(f"  WA added: no:{e['no']} {e['company_en']} {e['phone']}")
    else:
        print(f"  WA skip (exists): no:{e['no']}")
json.dump(wa_data, open(wa_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"WA pipeline: +{added_wa} entries → total {len(wa_data)}")

# ── Email pipeline ────────────────────────────────────────────────────────────
email_entries = [
    {"no": 611, "company_en": "PA Entertainment Group", "email_to": "chuck@paentertainmentgroup.com",          "country": "USA", "city": "Harrisburg, PA"},
    {"no": 612, "company_en": "Mitey AV",               "email_to": "events@miteyav.com",                     "country": "USA", "city": "New Orleans, LA"},
    {"no": 613, "company_en": "Refresh LED",             "email_to": "josh@refreshled.com",                    "country": "USA", "city": "Mechanicsburg, PA"},
    {"no": 614, "company_en": "Worship Productions",     "email_to": "customerservice@worshipproductions.org", "country": "USA", "city": "Yorba Linda, CA"},
    {"no": 615, "company_en": "CPR MultiMedia Solutions","email_to": "info@cprmms.com",                        "country": "USA", "city": "Gaithersburg, MD"},
    {"no": 616, "company_en": "MediaQuest",              "email_to": "t.bender@mediaquest.biz",                "country": "USA", "city": "Pittsburgh, PA"},
    {"no": 617, "company_en": "Vortex LED Wall",         "email_to": "info@vortexledwall.com",                 "country": "USA", "city": "San Diego, CA"},
    {"no": 618, "company_en": "The One Up Group",        "email_to": "Events@TheOneUpGroup.com",               "country": "USA", "city": "West Hollywood, CA"},
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
            "country": e["country"],
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
print(f"Email pipeline: +{added_email} entries → total {len(email_data)}")

print("\nDone.")
