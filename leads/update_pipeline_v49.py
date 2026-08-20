"""Update email and IG pipelines with v49 entries (nos 705-714)"""
import json, datetime
from pathlib import Path

TODAY = datetime.date.today().isoformat()
BASE = Path(__file__).parent

# --- Email pipeline ---
epath = BASE / "pipeline/email/prospects.json"
data = json.load(open(epath, encoding="utf-8"))
existing_nos = {p["no"] for p in data}

new_email = [
    {"no":705,"country":"USA","company_en":"San Diego Video Wall","city":"San Diego, CA","email":"hello@videowallsandiego.com","website":"videowallsandiego.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":706,"country":"USA","company_en":"TSV Sound & Vision","city":"Austin, TX","email":"info@tsvatx.com","website":"tsvatx.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":707,"country":"USA","company_en":"SoFlo Studio","city":"Fort Lauderdale, FL","email":"info@soflostudio.com","website":"soflostudio.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":708,"country":"USA","company_en":"Master Sound Productions","city":"Fort Lauderdale, FL","email":"","website":"mastersoundpro.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":709,"country":"USA","company_en":"MediaQuest","city":"Pittsburgh, PA","email":"","website":"mediaquest.biz","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":710,"country":"USA","company_en":"Ohio LED Wall","city":"Cleveland, OH","email":"info@ohioledwall.com","website":"ohioledwall.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":711,"country":"USA","company_en":"All Pro Audio Visual","city":"Milwaukee, WI","email":"info@allproaudiovisual.com","website":"allproaudiovisual.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":712,"country":"USA","company_en":"LV Led Video Wall","city":"Las Vegas, NV","email":"info@lvledvideowall.com","website":"lvledvideowall.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":713,"country":"USA","company_en":"Alliance Audio Visual","city":"Albuquerque, NM","email":"rentals@allianceav.com","website":"allianceav.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":714,"country":"USA","company_en":"VEGAS Event Group","city":"San Antonio, TX","email":"","website":"ledvideowallrentalsanantonio.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
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
    {"no":706,"country":"USA","company_en":"TSV Sound & Vision","city":"Austin, TX","username":"tsvusa","instagram":"tsvusa","status":"prospect","warmup_done":False,"warmup_date":None,"touch_count":0,"message_sent_date":None,"added_date":TODAY},
    {"no":707,"country":"USA","company_en":"SoFlo Studio","city":"Fort Lauderdale, FL","username":"soflostudio","instagram":"soflostudio","status":"prospect","warmup_done":False,"warmup_date":None,"touch_count":0,"message_sent_date":None,"added_date":TODAY},
    {"no":708,"country":"USA","company_en":"Master Sound Productions","city":"Fort Lauderdale, FL","username":"mastersoundpro","instagram":"mastersoundpro","status":"prospect","warmup_done":False,"warmup_date":None,"touch_count":0,"message_sent_date":None,"added_date":TODAY},
    {"no":709,"country":"USA","company_en":"MediaQuest","city":"Pittsburgh, PA","username":"mediaquestpgh","instagram":"mediaquestpgh","status":"prospect","warmup_done":False,"warmup_date":None,"touch_count":0,"message_sent_date":None,"added_date":TODAY},
    {"no":711,"country":"USA","company_en":"All Pro Audio Visual","city":"Milwaukee, WI","username":"allproaudiovisual","instagram":"allproaudiovisual","status":"prospect","warmup_done":False,"warmup_date":None,"touch_count":0,"message_sent_date":None,"added_date":TODAY},
    {"no":714,"country":"USA","company_en":"VEGAS Event Group","city":"San Antonio, TX","username":"vegaseventgroup","instagram":"vegaseventgroup","status":"prospect","warmup_done":False,"warmup_date":None,"touch_count":0,"message_sent_date":None,"added_date":TODAY},
]
added_ig = sum(1 for e in new_ig if e["username"] not in existing_ig)
for e in new_ig:
    if e["username"] not in existing_ig:
        igdata.append(e)
with open(igpath, "w", encoding="utf-8") as f:
    json.dump(igdata, f, ensure_ascii=False, indent=2)
print(f"IG pipeline: +{added_ig} entries")
