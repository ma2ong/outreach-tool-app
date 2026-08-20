import json, os

base = r"C:\Users\Administrator\ai-topic-generator\output\leads\pipeline"

# --- Update Email Pipeline ---
ep_path = os.path.join(base, "email", "prospects.json")
ep = json.load(open(ep_path, encoding="utf-8"))
existing_nos = {p["no"] for p in ep}

new_email = [
    {"no": 657, "company_en": "Triangle Media Solutions", "email": "admin@trianglemediasolutions.com", "city": "Raleigh, NC"},
    {"no": 658, "company_en": "The Production Source",    "email": "info@theproductionsource.net",    "city": "Knoxville, TN"},
    {"no": 659, "company_en": "The AV Company",           "email": "info@theavcompany.net",           "city": "Charlottesville, VA"},
    {"no": 660, "company_en": "Power On Productions",     "email": "info@poweronav.com",              "city": "New Orleans, LA"},
    {"no": 661, "company_en": "Hinckley Productions",     "email": "info@hinckleyproductions.com",    "city": "Madison, WI"},
    {"no": 662, "company_en": "STAR Studios LLC",          "email": "sales@starstudioswi.com",        "city": "DeForest, WI"},
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
    {"no": 657, "company_en": "Triangle Media Solutions", "username": "trianglemediasolutions", "city": "Raleigh, NC"},
    {"no": 658, "company_en": "The Production Source",    "username": "theproductionsource",    "city": "Knoxville, TN"},
    {"no": 660, "company_en": "Power On Productions",     "username": "poweron4u",              "city": "New Orleans, LA"},
    {"no": 661, "company_en": "Hinckley Productions",     "username": "hinckleyproductions",    "city": "Madison, WI"},
    {"no": 662, "company_en": "STAR Studios LLC",          "username": "starstudioswi",          "city": "DeForest, WI"},
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
