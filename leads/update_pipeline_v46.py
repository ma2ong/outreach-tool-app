"""Update email and IG pipelines with v46 entries"""
import json, datetime
from pathlib import Path

TODAY = datetime.date.today().isoformat()
BASE = Path(__file__).parent

# --- Email pipeline ---
epath = BASE / "pipeline/email/prospects.json"
data = json.load(open(epath, encoding="utf-8"))
existing_nos = {p["no"] for p in data}

new_email = [
    {"no":686,"country":"USA","company_en":"Xperience Entertainment","city":"Peoria, AZ","email":"info@readytoxperience.com","website":"readytoxperience.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":687,"country":"USA","company_en":"Denver Video Wall","city":"Denver, CO","email":"hello@denvervideowall.com","website":"denvervideowall.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":688,"country":"USA","company_en":"Midwest Audio Visual","city":"Cincinnati, OH","email":"info@midwestaudiovisual.com","website":"midwestaudiovisual.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":689,"country":"USA","company_en":"Phoenix LED Screens","city":"Phoenix, AZ","email":"","website":"phoenixledscreens.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":690,"country":"USA","company_en":"Lime Lights Entertainment","city":"Ridgeville, OH","email":"contactus@limelightsent.com","website":"limelightsent.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":691,"country":"USA","company_en":"MTI Sound","city":"Altamonte Springs, FL","email":"contact@mtisound.com","website":"mtisound.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
]
added = sum(1 for e in new_email if e["no"] not in existing_nos)
for e in new_email:
    if e["no"] not in existing_nos:
        data.append(e)
with open(epath, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"Email pipeline: +{added} entries")

# --- IG pipeline ---
igpath = BASE / "pipeline/instagram/prospects.json"
igdata = json.load(open(igpath, encoding="utf-8"))
existing_ig = {p["username"] for p in igdata}

new_ig = [
    {"no":686,"country":"USA","company_en":"Xperience Entertainment","city":"Peoria, AZ","username":"xperienceent","instagram":"xperienceent","status":"prospect","warmup_done":False,"warmup_date":None,"touch_count":0,"message_sent_date":None,"added_date":TODAY},
    {"no":689,"country":"USA","company_en":"Phoenix LED Screens","city":"Phoenix, AZ","username":"phoenixledscreens","instagram":"phoenixledscreens","status":"prospect","warmup_done":False,"warmup_date":None,"touch_count":0,"message_sent_date":None,"added_date":TODAY},
    {"no":690,"country":"USA","company_en":"Lime Lights Entertainment","city":"Ridgeville, OH","username":"limelightsentertain","instagram":"limelightsentertain","status":"prospect","warmup_done":False,"warmup_date":None,"touch_count":0,"message_sent_date":None,"added_date":TODAY},
    {"no":691,"country":"USA","company_en":"MTI Sound","city":"Altamonte Springs, FL","username":"mtisoundlighting","instagram":"mtisoundlighting","status":"prospect","warmup_done":False,"warmup_date":None,"touch_count":0,"message_sent_date":None,"added_date":TODAY},
]
added_ig = sum(1 for e in new_ig if e["username"] not in existing_ig)
for e in new_ig:
    if e["username"] not in existing_ig:
        igdata.append(e)
with open(igpath, "w", encoding="utf-8") as f:
    json.dump(igdata, f, ensure_ascii=False, indent=2)
print(f"IG pipeline: +{added_ig} entries")
