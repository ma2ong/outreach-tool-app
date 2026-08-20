"""Add v47 entries (nos 692-698) to email and IG pipelines."""
import json, os

BASE = os.path.dirname(__file__)
EMAIL_PIPELINE = os.path.join(BASE, "pipeline/email/prospects.json")
IG_PIPELINE = os.path.join(BASE, "pipeline/instagram/prospects.json")

new_email = [
    {"no": 692, "country": "USA", "company_en": "GSF Productions", "city": "Raleigh, NC",
     "email": "info@gsfaudio.com", "website": "https://gsfaudio.com",
     "instagram": "gsf_productions", "status": "prospect", "touch_count": 0,
     "message_sent_date": None, "notes": ""},
    {"no": 693, "country": "USA", "company_en": "ProductionOne", "city": "Memphis, TN",
     "email": "info@productionone.com", "website": "https://productionone.com",
     "instagram": "productiononeav", "status": "prospect", "touch_count": 0,
     "message_sent_date": None, "notes": ""},
    {"no": 694, "country": "USA", "company_en": "TechPro Audio & Video", "city": "El Paso, TX",
     "email": "service@techpro-av.com", "website": "https://techpro-av.com",
     "instagram": "techproavtx", "status": "prospect", "touch_count": 0,
     "message_sent_date": None, "notes": ""},
    {"no": 695, "country": "USA", "company_en": "Excel Presentation Services", "city": "Orlando, FL",
     "email": "info@excelpresentations.com", "website": "https://ledvideowallrentalorlando.com",
     "instagram": "", "status": "prospect", "touch_count": 0,
     "message_sent_date": None, "notes": ""},
    {"no": 696, "country": "USA", "company_en": "AV Rental Orlando", "city": "Orlando, FL",
     "email": "info@avrentalorlando.com", "website": "https://avrentalorlando.com",
     "instagram": "", "status": "prospect", "touch_count": 0,
     "message_sent_date": None, "notes": ""},
    {"no": 697, "country": "USA", "company_en": "Orlando Video Walls", "city": "Orlando, FL",
     "email": "hello@orlandovideowallrental.com", "website": "https://orlandovideowallrental.com",
     "instagram": "", "status": "prospect", "touch_count": 0,
     "message_sent_date": None, "notes": ""},
    {"no": 698, "country": "USA", "company_en": "VOX Audio Visual", "city": "Tulsa, OK",
     "email": "", "website": "https://voxaudiovisual.com",
     "instagram": "voxaudiovisual", "status": "prospect", "touch_count": 0,
     "message_sent_date": None, "notes": "IG only, no public email"},
]

new_ig = [
    {"no": 692, "username": "gsf_productions", "company_en": "GSF Productions",
     "city": "Raleigh, NC", "status": "prospect", "warmup_done": False,
     "touch_count": 0, "dm_sent_date": None},
    {"no": 693, "username": "productiononeav", "company_en": "ProductionOne",
     "city": "Memphis, TN", "status": "prospect", "warmup_done": False,
     "touch_count": 0, "dm_sent_date": None},
    {"no": 694, "username": "techproavtx", "company_en": "TechPro Audio & Video",
     "city": "El Paso, TX", "status": "prospect", "warmup_done": False,
     "touch_count": 0, "dm_sent_date": None},
    {"no": 698, "username": "voxaudiovisual", "company_en": "VOX Audio Visual",
     "city": "Tulsa, OK", "status": "prospect", "warmup_done": False,
     "touch_count": 0, "dm_sent_date": None},
]

# Email pipeline
ep = json.load(open(EMAIL_PIPELINE, encoding="utf-8"))
existing_nos = {p["no"] for p in ep}
added_email = 0
for e in new_email:
    if e["no"] not in existing_nos:
        ep.append(e)
        added_email += 1
with open(EMAIL_PIPELINE, "w", encoding="utf-8") as f:
    json.dump(ep, f, ensure_ascii=False, indent=2)
print(f"Email pipeline: +{added_email} (total {len(ep)})")

# IG pipeline
ig = json.load(open(IG_PIPELINE, encoding="utf-8"))
existing_users = {p.get("username") for p in ig}
added_ig = 0
for e in new_ig:
    if e["username"] not in existing_users:
        ig.append(e)
        added_ig += 1
with open(IG_PIPELINE, "w", encoding="utf-8") as f:
    json.dump(ig, f, ensure_ascii=False, indent=2)
print(f"IG pipeline: +{added_ig} (total {len(ig)})")
