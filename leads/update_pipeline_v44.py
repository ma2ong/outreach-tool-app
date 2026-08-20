"""Update email and IG pipelines with v44 entries"""
import json, datetime
from pathlib import Path

TODAY = datetime.date.today().isoformat()
BASE = Path(__file__).parent

# --- Email pipeline ---
epath = BASE / "pipeline/email/prospects.json"
data = json.load(open(epath, encoding="utf-8"))
existing_nos = {p["no"] for p in data}

new_email = [
    {"no":663,"country":"USA","company_en":"Northwest Video Wall","city":"Seattle, WA","email":"","website":"nwvideowall.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":664,"country":"USA","company_en":"LightSmiths","city":"Seattle, WA","email":"","website":"lightsmiths.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":665,"country":"USA","company_en":"UltimateX Displays","city":"Minneapolis, MN","email":"info@ultimatexdisplays.com","website":"ultimatexdisplays.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":666,"country":"USA","company_en":"Jagen Events","city":"Minneapolis, MN","email":"","website":"jagenevents.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":667,"country":"USA","company_en":"ERG247 Event Resource Group","city":"Tampa, FL","email":"hello@erg247.com","website":"erg247.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":668,"country":"USA","company_en":"Control Entertainment","city":"San Diego, CA","email":"alisha@control-entertainment.com","website":"control-entertainment.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":669,"country":"USA","company_en":"Take One Audiovisual","city":"Salt Lake City, UT","email":"info@takeoneav.com","website":"takeoneav.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":670,"country":"USA","company_en":"Mountain AV Events","city":"Salt Lake City, UT","email":"","website":"mountainav-events.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":671,"country":"USA","company_en":"Ohio LED Wall","city":"Cleveland, OH","email":"info@ohioledwall.com","website":"ohioledwall.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":672,"country":"USA","company_en":"Great Lakes Audio Visual","city":"Milan, OH","email":"info@greatlakesaudiovisual.com","website":"greatlakesaudiovisual.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":673,"country":"USA","company_en":"NPi Audio Visual Solutions","city":"Cleveland, OH","email":"info@npiav.com","website":"npiav.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":674,"country":"USA","company_en":"AV Pro Sound and Video","city":"Monroe, NC","email":"info@avprosoundandvideo.com","website":"avprosoundandvideo.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":675,"country":"USA","company_en":"Buffalo Audio Visual","city":"Buffalo, NY","email":"info@buffaloaudiovisual.com","website":"buffaloaudiovisual.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"added_date":TODAY},
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
    {"no":664,"country":"USA","company_en":"LightSmiths","city":"Seattle, WA","username":"lightsmiths.seattle","instagram":"lightsmiths.seattle","status":"prospect","warmup_done":False,"warmup_date":None,"touch_count":0,"message_sent_date":None,"added_date":TODAY},
    {"no":667,"country":"USA","company_en":"ERG247 Event Resource Group","city":"Tampa, FL","username":"erg247","instagram":"erg247","status":"prospect","warmup_done":False,"warmup_date":None,"touch_count":0,"message_sent_date":None,"added_date":TODAY},
    {"no":668,"country":"USA","company_en":"Control Entertainment","city":"San Diego, CA","username":"control_entertainment","instagram":"control_entertainment","status":"prospect","warmup_done":False,"warmup_date":None,"touch_count":0,"message_sent_date":None,"added_date":TODAY},
    {"no":669,"country":"USA","company_en":"Take One Audiovisual","city":"Salt Lake City, UT","username":"takeoneav","instagram":"takeoneav","status":"prospect","warmup_done":False,"warmup_date":None,"touch_count":0,"message_sent_date":None,"added_date":TODAY},
    {"no":670,"country":"USA","company_en":"Mountain AV Events","city":"Salt Lake City, UT","username":"mountain_av","instagram":"mountain_av","status":"prospect","warmup_done":False,"warmup_date":None,"touch_count":0,"message_sent_date":None,"added_date":TODAY},
    {"no":672,"country":"USA","company_en":"Great Lakes Audio Visual","city":"Milan, OH","username":"greatlakesav","instagram":"greatlakesav","status":"prospect","warmup_done":False,"warmup_date":None,"touch_count":0,"message_sent_date":None,"added_date":TODAY},
    {"no":673,"country":"USA","company_en":"NPi Audio Visual Solutions","city":"Cleveland, OH","username":"npiaudiovisualsolutions","instagram":"npiaudiovisualsolutions","status":"prospect","warmup_done":False,"warmup_date":None,"touch_count":0,"message_sent_date":None,"added_date":TODAY},
    {"no":674,"country":"USA","company_en":"AV Pro Sound and Video","city":"Monroe, NC","username":"avproductionsnc","instagram":"avproductionsnc","status":"prospect","warmup_done":False,"warmup_date":None,"touch_count":0,"message_sent_date":None,"added_date":TODAY},
]
added_ig = sum(1 for e in new_ig if e["username"] not in existing_ig)
for e in new_ig:
    if e["username"] not in existing_ig:
        igdata.append(e)
with open(igpath, "w", encoding="utf-8") as f:
    json.dump(igdata, f, ensure_ascii=False, indent=2)
print(f"IG pipeline: +{added_ig} entries")
