import json, os

base = r"C:\Users\Administrator\ai-topic-generator\output\leads\pipeline"

# --- Update Email Pipeline ---
ep_path = os.path.join(base, "email", "prospects.json")
ep = json.load(open(ep_path, encoding="utf-8"))
existing_nos = {p["no"] for p in ep}

new_email = [
    {"no": 651, "company_en": "GSE Audiovisual Inc",         "email": "sales@gseav.com",                  "city": "Orlando, FL"},
    {"no": 652, "company_en": "Ultimate Outdoor Entertainment","email": "events@uoe.com",                  "city": "Cerritos, CA"},
    {"no": 653, "company_en": "Mercury Sound & Lighting",    "email": "info@mercurysl.com",               "city": "Wixom, MI"},
    {"no": 654, "company_en": "C&H Audio Visual Services",   "email": "rentals@chavs.net",                "city": "Louisville, KY"},
    {"no": 655, "company_en": "Nova Productions LLC",        "email": "info@novaproductionsomaha.com",    "city": "Omaha, NE"},
    {"no": 656, "company_en": "PRI Productions",             "email": "info@priproductions.com",          "city": "Jacksonville, FL"},
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
    {"no": 652, "company_en": "Ultimate Outdoor Entertainment","username": "ultimateoutdoorentertainment", "city": "Cerritos, CA"},
    {"no": 653, "company_en": "Mercury Sound & Lighting",      "username": "mercurysl",                   "city": "Wixom, MI"},
    {"no": 654, "company_en": "C&H Audio Visual Services",     "username": "chaudiovisual",               "city": "Louisville, KY"},
    {"no": 655, "company_en": "Nova Productions LLC",          "username": "nova_productions_llc",        "city": "Omaha, NE"},
    {"no": 656, "company_en": "PRI Productions",               "username": "priproductions",              "city": "Jacksonville, FL"},
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
