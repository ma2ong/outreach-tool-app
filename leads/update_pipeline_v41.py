import json, os

base = r"C:\Users\Administrator\ai-topic-generator\output\leads\pipeline"

# --- Update Email Pipeline ---
ep_path = os.path.join(base, "email", "prospects.json")
ep = json.load(open(ep_path, encoding="utf-8"))
existing_nos = {p["no"] for p in ep}

new_email = [
    {"no": 643, "company_en": "Rent LED Video Walls",        "email": "info@rentledvideowall.com",    "city": "Annapolis, MD"},
    {"no": 644, "company_en": "Media Support Services Inc",  "email": "info@mssav.com",               "city": "Baltimore, MD"},
    {"no": 645, "company_en": "AV Actions Inc",              "email": "info@avactions.com",           "city": "Alexandria, VA"},
    {"no": 646, "company_en": "Stage Lights and Sound",      "email": "Sales@StageLightsandSound.com","city": "Richmond, CA"},
    {"no": 647, "company_en": "Amos Productions",            "email": "info@amospro.com",             "city": "Livermore, CA"},
    {"no": 648, "company_en": "Megahertz AV",                "email": "info@mhzav.com",               "city": "Santa Clara, CA"},
    {"no": 649, "company_en": "Corporate Lighting and Audio","email": "sales@corplighting.com",       "city": "New Orleans, LA"},
]

added_email = 0
for entry in new_email:
    if entry["no"] not in existing_nos:
        ep.append({
            "no": entry["no"],
            "country": "USA",
            "company_en": entry["company_en"],
            "email": entry["email"],
            "city": entry["city"],
            "status": "prospect",
            "touch_count": 0,
            "email_sent_date": None,
            "message_sent_date": None,
            "message_channel": None,
            "exclude_reason": None,
        })
        added_email += 1
        print(f"  Added email: {entry['company_en']}")

with open(ep_path, "w", encoding="utf-8") as f:
    json.dump(ep, f, ensure_ascii=False, indent=2)
print(f"Email pipeline: +{added_email} entries, total {len(ep)}")

# --- Update IG Pipeline ---
ig_path = os.path.join(base, "instagram", "prospects.json")
ig = json.load(open(ig_path, encoding="utf-8"))
ig_usernames = {p.get("username") or p.get("instagram", "") for p in ig}

new_ig = [
    {"no": 645, "company_en": "AV Actions Inc",              "username": "avactions_dc", "city": "Alexandria, VA"},
    {"no": 647, "company_en": "Amos Productions",            "username": "amospro_av",   "city": "Livermore, CA"},
    {"no": 649, "company_en": "Corporate Lighting and Audio","username": "corplighting", "city": "New Orleans, LA"},
]

ig_added = 0
for entry in new_ig:
    if entry["username"] not in ig_usernames:
        ig.append({
            "no": entry["no"],
            "country": "USA",
            "company_en": entry["company_en"],
            "username": entry["username"],
            "instagram": entry["username"],
            "city": entry["city"],
            "status": "prospect",
            "warmup_done": False,
            "warmup_date": None,
            "touch_count": 0,
            "dm_sent_date": None,
            "message_sent_date": None,
            "dm_message_preview": None,
            "exclude_reason": None,
        })
        ig_added += 1
        print(f"  Added IG: @{entry['username']}")

with open(ig_path, "w", encoding="utf-8") as f:
    json.dump(ig, f, ensure_ascii=False, indent=2)
print(f"IG pipeline: +{ig_added} entries, total {len(ig)}")
