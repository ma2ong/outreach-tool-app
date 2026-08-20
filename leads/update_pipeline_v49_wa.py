"""Add v49 USA phone entries to WA pipeline"""
import json, datetime
from pathlib import Path

TODAY = datetime.date.today().isoformat()
BASE = Path(__file__).parent
WAPATH = BASE / "pipeline/whatsapp/prospects.json"

data = json.load(open(WAPATH, encoding="utf-8"))
existing_nos = {p["no"] for p in data}

new_wa = [
    {"no":706,"country":"USA","company_en":"TSV Sound & Vision","city":"Austin, TX",
     "phone_whatsapp":"512-593-5155","phone":"15125935155","website":"tsvatx.com",
     "instagram":"tsvusa","status":"prospect","touch_count":0,
     "message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":707,"country":"USA","company_en":"SoFlo Studio","city":"Fort Lauderdale, FL",
     "phone_whatsapp":"954-446-5619","phone":"19544465619","website":"soflostudio.com",
     "instagram":"soflostudio","status":"prospect","touch_count":0,
     "message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":708,"country":"USA","company_en":"Master Sound Productions","city":"Fort Lauderdale, FL",
     "phone_whatsapp":"305-972-6838","phone":"13059726838","website":"mastersoundpro.com",
     "instagram":"mastersoundpro","status":"prospect","touch_count":0,
     "message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":709,"country":"USA","company_en":"MediaQuest","city":"Pittsburgh, PA",
     "phone_whatsapp":"412-921-3360","phone":"14129213360","website":"mediaquest.biz",
     "instagram":"mediaquestpgh","status":"prospect","touch_count":0,
     "message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":710,"country":"USA","company_en":"Ohio LED Wall","city":"Cleveland, OH",
     "phone_whatsapp":"216-233-8544","phone":"12162338544","website":"ohioledwall.com",
     "instagram":"","status":"prospect","touch_count":0,
     "message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":712,"country":"USA","company_en":"LV Led Video Wall","city":"Las Vegas, NV",
     "phone_whatsapp":"702-807-6444","phone":"17028076444","website":"lvledvideowall.com",
     "instagram":"","status":"prospect","touch_count":0,
     "message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":713,"country":"USA","company_en":"Alliance Audio Visual","city":"Albuquerque, NM",
     "phone_whatsapp":"505-341-3900","phone":"15053413900","website":"allianceav.com",
     "instagram":"","status":"prospect","touch_count":0,
     "message_sent_date":None,"message_channel":None,"added_date":TODAY},
    {"no":714,"country":"USA","company_en":"VEGAS Event Group","city":"San Antonio, TX",
     "phone_whatsapp":"210-527-7840","phone":"12105277840","website":"ledvideowallrentalsanantonio.com",
     "instagram":"vegaseventgroup","status":"prospect","touch_count":0,
     "message_sent_date":None,"message_channel":None,"added_date":TODAY},
]

added = 0
for e in new_wa:
    if e["no"] not in existing_nos:
        data.append(e)
        added += 1
        print(f"  +{e['no']} {e['company_en']} ({e['city']}) {e['phone_whatsapp']}")

with open(WAPATH, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"\nWA pipeline: +{added} new USA entries")
