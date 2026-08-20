"""Update email and IG pipelines with v45 entries"""
import json, datetime
from pathlib import Path

TODAY = datetime.date.today().isoformat()
BASE = Path(__file__).parent

# --- Email pipeline ---
epath = BASE / "pipeline/email/prospects.json"
data = json.load(open(epath, encoding="utf-8"))
existing_nos = {p["no"] for p in data}

new_email = [
    {"no":676,"country":"USA","company_en":"Final Design Group","city":"Hurricane, UT","email":"SWLemmon@fdgtv.com","website":"fdgtv.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":677,"country":"USA","company_en":"The Penn Group","city":"Gahanna, OH","email":"sales@thepenn.group","website":"thepenn.group","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":678,"country":"USA","company_en":"Concept Pixels","city":"Nashville, TN","email":"info@conceptpixels.com","website":"conceptpixels.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":679,"country":"USA","company_en":"Supreme AV","city":"Charlton, MA","email":"Shane@supremeav.net","website":"supremeav.net","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":680,"country":"USA","company_en":"Moon Men DJs","city":"Birmingham, AL","email":"info@moonmenonline.com","website":"moonmendjs.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":681,"country":"USA","company_en":"A1 Visuals","city":"San Jose, CA","email":"A1visualevents@gmail.com","website":"sanjoseledscreen.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":682,"country":"USA","company_en":"Myx Productions","city":"Oklahoma City, OK","email":"info@myxproductions.com","website":"myxproductions.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":683,"country":"USA","company_en":"Dizplay Inc","city":"Detroit, MI","email":"","website":"dizplayrentals.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":684,"country":"USA","company_en":"Cory's AV Solutions","city":"Oklahoma City, OK","email":"","website":"corys.pro","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":685,"country":"USA","company_en":"Event Expert","city":"Providence, RI","email":"hello@eventexpert.io","website":"eventexpert.io","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
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
    {"no":677,"country":"USA","company_en":"The Penn Group","city":"Gahanna, OH","username":"thepenn.group","instagram":"thepenn.group","status":"prospect","warmup_done":False,"warmup_date":None,"touch_count":0,"message_sent_date":None,"added_date":TODAY},
    {"no":678,"country":"USA","company_en":"Concept Pixels","city":"Nashville, TN","username":"conceptpixels","instagram":"conceptpixels","status":"prospect","warmup_done":False,"warmup_date":None,"touch_count":0,"message_sent_date":None,"added_date":TODAY},
    {"no":679,"country":"USA","company_en":"Supreme AV","city":"Charlton, MA","username":"supreme_av","instagram":"supreme_av","status":"prospect","warmup_done":False,"warmup_date":None,"touch_count":0,"message_sent_date":None,"added_date":TODAY},
    {"no":680,"country":"USA","company_en":"Moon Men DJs","city":"Birmingham, AL","username":"moonmendjs","instagram":"moonmendjs","status":"prospect","warmup_done":False,"warmup_date":None,"touch_count":0,"message_sent_date":None,"added_date":TODAY},
    {"no":681,"country":"USA","company_en":"A1 Visuals","city":"San Jose, CA","username":"a1_visuals_","instagram":"a1_visuals_","status":"prospect","warmup_done":False,"warmup_date":None,"touch_count":0,"message_sent_date":None,"added_date":TODAY},
    {"no":682,"country":"USA","company_en":"Myx Productions","city":"Oklahoma City, OK","username":"myxproductions","instagram":"myxproductions","status":"prospect","warmup_done":False,"warmup_date":None,"touch_count":0,"message_sent_date":None,"added_date":TODAY},
    {"no":683,"country":"USA","company_en":"Dizplay Inc","city":"Detroit, MI","username":"dizplayinc","instagram":"dizplayinc","status":"prospect","warmup_done":False,"warmup_date":None,"touch_count":0,"message_sent_date":None,"added_date":TODAY},
    {"no":684,"country":"USA","company_en":"Cory's AV Solutions","city":"Oklahoma City, OK","username":"corysconnects","instagram":"corysconnects","status":"prospect","warmup_done":False,"warmup_date":None,"touch_count":0,"message_sent_date":None,"added_date":TODAY},
]
added_ig = sum(1 for e in new_ig if e["username"] not in existing_ig)
for e in new_ig:
    if e["username"] not in existing_ig:
        igdata.append(e)
with open(igpath, "w", encoding="utf-8") as f:
    json.dump(igdata, f, ensure_ascii=False, indent=2)
print(f"IG pipeline: +{added_ig} entries")
