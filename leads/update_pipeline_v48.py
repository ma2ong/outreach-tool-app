"""Add v48 entries (nos 699-704) to email and IG pipelines."""
import json, os

BASE = os.path.dirname(__file__)
EMAIL_PIPELINE = os.path.join(BASE, "pipeline/email/prospects.json")
IG_PIPELINE = os.path.join(BASE, "pipeline/instagram/prospects.json")

new_email = [
    {"no": 699, "country": "USA", "company_en": "Rocky Mountain Roll", "city": "Meridian, ID",
     "email": "Sales@rockymountainroll.com", "website": "https://rockymountainroll.com",
     "instagram": "rockymountainroll", "status": "prospect", "touch_count": 0,
     "message_sent_date": None, "notes": ""},
    {"no": 700, "country": "USA", "company_en": "Rocky Mountain Audio Visual", "city": "Boise, ID",
     "email": "rentals@rmav.com", "website": "https://rmav.com",
     "instagram": "", "status": "prospect", "touch_count": 0,
     "message_sent_date": None, "notes": ""},
    {"no": 701, "country": "USA", "company_en": "Arizona Mobile Media", "city": "Tucson, AZ",
     "email": "info@azmobilemedia.net", "website": "https://azmobilemedia.net",
     "instagram": "", "status": "prospect", "touch_count": 0,
     "message_sent_date": None, "notes": ""},
    {"no": 702, "country": "USA", "company_en": "Seals Productions", "city": "Chattanooga, TN",
     "email": "sealsproductions7@gmail.com", "website": "https://sealsproductions.com",
     "instagram": "sealsproductions", "status": "prospect", "touch_count": 0,
     "message_sent_date": None, "notes": ""},
    {"no": 703, "country": "USA", "company_en": "AMPD Lighting and Audio Visual", "city": "Spokane, WA",
     "email": "Sales@ampdspokane.com", "website": "https://ampdspokane.com",
     "instagram": "ampdlightingaudiovisual", "status": "prospect", "touch_count": 0,
     "message_sent_date": None, "notes": ""},
    {"no": 704, "country": "USA", "company_en": "AVL Solutions", "city": "Greenville, SC",
     "email": "info@avlsusa.com", "website": "https://avlsusa.com",
     "instagram": "avl_solutions", "status": "prospect", "touch_count": 0,
     "message_sent_date": None, "notes": ""},
]

new_ig = [
    {"no": 699, "username": "rockymountainroll", "company_en": "Rocky Mountain Roll",
     "city": "Meridian, ID", "status": "prospect", "warmup_done": False,
     "touch_count": 0, "dm_sent_date": None},
    {"no": 702, "username": "sealsproductions", "company_en": "Seals Productions",
     "city": "Chattanooga, TN", "status": "prospect", "warmup_done": False,
     "touch_count": 0, "dm_sent_date": None},
    {"no": 703, "username": "ampdlightingaudiovisual", "company_en": "AMPD Lighting and Audio Visual",
     "city": "Spokane, WA", "status": "prospect", "warmup_done": False,
     "touch_count": 0, "dm_sent_date": None},
    {"no": 704, "username": "avl_solutions", "company_en": "AVL Solutions",
     "city": "Greenville, SC", "status": "prospect", "warmup_done": False,
     "touch_count": 0, "dm_sent_date": None},
]

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
