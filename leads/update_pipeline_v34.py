import json
from datetime import date

BASE = r"C:\Users\Administrator\ai-topic-generator\output\leads"
TODAY = date.today().isoformat()

ig_path = BASE + r"\pipeline\instagram\prospects.json"
data = json.load(open(ig_path, encoding="utf-8"))
new_ig = [
    {"no":597,"country":"USA","company_en":"AV For You","city":"Crystal, MN","username":"av.for.you","status":"prospect","warmup_done":False,"warmup_date":None,"dm_sent_date":None,"dm_message_preview":None,"touch_count":0},
    {"no":598,"country":"USA","company_en":"Fire Up Creative","city":"Andover, MN","username":"fireupcreative","status":"prospect","warmup_done":False,"warmup_date":None,"dm_sent_date":None,"dm_message_preview":None,"touch_count":0},
    {"no":599,"country":"USA","company_en":"Showtime LED","city":"Kansas City, MO","username":"showtime.led","status":"prospect","warmup_done":False,"warmup_date":None,"dm_sent_date":None,"dm_message_preview":None,"touch_count":0},
    {"no":600,"country":"USA","company_en":"KC Event Company","city":"Overland Park, KS","username":"kceventcompany","status":"prospect","warmup_done":False,"warmup_date":None,"dm_sent_date":None,"dm_message_preview":None,"touch_count":0},
    {"no":601,"country":"USA","company_en":"TSV Sound & Vision","city":"St. Louis, MO","username":"tsvusa","status":"prospect","warmup_done":False,"warmup_date":None,"dm_sent_date":None,"dm_message_preview":None,"touch_count":0},
    {"no":602,"country":"USA","company_en":"JAWS AVL","city":"San Antonio, TX","username":"jawsaudio","status":"prospect","warmup_done":False,"warmup_date":None,"dm_sent_date":None,"dm_message_preview":None,"touch_count":0},
    {"no":603,"country":"USA","company_en":"DPC Event Services","city":"San Antonio, TX","username":"dpcevents","status":"prospect","warmup_done":False,"warmup_date":None,"dm_sent_date":None,"dm_message_preview":None,"touch_count":0},
    {"no":604,"country":"USA","company_en":"Outdoor LED Rentals","city":"Nashville, TN","username":"outdoorledrentals","status":"prospect","warmup_done":False,"warmup_date":None,"dm_sent_date":None,"dm_message_preview":None,"touch_count":0},
    {"no":605,"country":"USA","company_en":"Elite Multimedia","city":"Mount Juliet, TN","username":"elitemultimedia","status":"prospect","warmup_done":False,"warmup_date":None,"dm_sent_date":None,"dm_message_preview":None,"touch_count":0},
    {"no":606,"country":"USA","company_en":"Fairfield Pro AV","city":"Charlotte, NC","username":"fairfieldproav","status":"prospect","warmup_done":False,"warmup_date":None,"dm_sent_date":None,"dm_message_preview":None,"touch_count":0},
    {"no":607,"country":"USA","company_en":"FireFly AV Design","city":"Charlotte, NC","username":"fireflyclt","status":"prospect","warmup_done":False,"warmup_date":None,"dm_sent_date":None,"dm_message_preview":None,"touch_count":0},
    {"no":608,"country":"USA","company_en":"Mathes Event Productions","city":"Chamblee, GA","username":"eventsmathes","status":"prospect","warmup_done":False,"warmup_date":None,"dm_sent_date":None,"dm_message_preview":None,"touch_count":0},
    {"no":609,"country":"USA","company_en":"Picture This Production Services","city":"Portland, OR","username":"picturethisportland","status":"prospect","warmup_done":False,"warmup_date":None,"dm_sent_date":None,"dm_message_preview":None,"touch_count":0},
    {"no":610,"country":"USA","company_en":"North State Audio Visual","city":"Chico, CA","username":"northstateaudiovisual","status":"prospect","warmup_done":False,"warmup_date":None,"dm_sent_date":None,"dm_message_preview":None,"touch_count":0},
]
data.extend(new_ig)
with open(ig_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"IG: {len(data)} total, +{len(new_ig)}")

email_path = BASE + r"\pipeline\email\prospects.json"
edata = json.load(open(email_path, encoding="utf-8"))
new_email = [
    {"no":597,"country":"USA","company_en":"AV For You","city":"Crystal, MN","email":"rentals@avforyou.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"exclude_reason":None},
    {"no":598,"country":"USA","company_en":"Fire Up Creative","city":"Andover, MN","email":"dave@fireupvideo.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"exclude_reason":None},
    {"no":599,"country":"USA","company_en":"Showtime LED","city":"Kansas City, MO","email":"info@showtimeled.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"exclude_reason":None},
    {"no":600,"country":"USA","company_en":"KC Event Company","city":"Overland Park, KS","email":"info@kceventcompany.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"exclude_reason":None},
    {"no":601,"country":"USA","company_en":"TSV Sound & Vision","city":"St. Louis, MO","email":"info@tsvstl.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"exclude_reason":None},
    {"no":602,"country":"USA","company_en":"JAWS AVL","city":"San Antonio, TX","email":"info@jawsaudio.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"exclude_reason":None},
    {"no":604,"country":"USA","company_en":"Outdoor LED Rentals","city":"Nashville, TN","email":"info@outdoorledrentals.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"exclude_reason":None},
    {"no":605,"country":"USA","company_en":"Elite Multimedia","city":"Mount Juliet, TN","email":"rentals@elitemultimedia.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"exclude_reason":None},
    {"no":606,"country":"USA","company_en":"Fairfield Pro AV","city":"Charlotte, NC","email":"samjr@fairfieldpro.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"exclude_reason":None},
    {"no":607,"country":"USA","company_en":"FireFly AV Design","city":"Charlotte, NC","email":"noah@fireflyavdesign.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"exclude_reason":None},
    {"no":608,"country":"USA","company_en":"Mathes Event Productions","city":"Chamblee, GA","email":"info@mathesevents.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"exclude_reason":None},
    {"no":609,"country":"USA","company_en":"Picture This Production Services","city":"Portland, OR","email":"info@pixthis.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"exclude_reason":None},
    {"no":610,"country":"USA","company_en":"North State Audio Visual","city":"Chico, CA","email":"info@northstateav.com","status":"prospect","touch_count":0,"message_sent_date":None,"message_channel":None,"exclude_reason":None},
]
edata.extend(new_email)
with open(email_path, "w", encoding="utf-8") as f:
    json.dump(edata, f, ensure_ascii=False, indent=2)
print(f"Email: {len(edata)} total, +{len(new_email)}")
