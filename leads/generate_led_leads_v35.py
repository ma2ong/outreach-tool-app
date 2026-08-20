"""
LED Display Leads v35 — USA (8 new entries, nos 611-618)
PA Entertainment Group, Mitey AV, Refresh LED, Worship Productions,
CPR MultiMedia Solutions, MediaQuest, Vortex LED Wall, The One Up Group
"""
import ast, re, os, sys
sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(__file__)

def load_all_leads():
    _v4_src = open(os.path.join(BASE, "generate_led_leads_v4.py"), encoding="utf-8").read()
    leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", _v4_src, re.M | re.S).group(1))
    for _vname in [f"v{i}" for i in range(5, 35)]:
        _path = os.path.join(BASE, f"generate_led_leads_{_vname}.py")
        if not os.path.exists(_path): continue
        _src = open(_path, encoding="utf-8").read()
        _m = re.search(r"^new_entries = (\[.+?^\])", _src, re.M | re.S)
        if _m: leads.extend(ast.literal_eval(_m.group(1)))
    return leads

new_entries = [
    {
        "no": 611,
        "country": "USA",
        "region": "Americas",
        "company_en": "PA Entertainment Group",
        "company_local": "",
        "city": "Harrisburg, PA",
        "contact_name": "Chuck",
        "title": "",
        "email": "chuck@paentertainmentgroup.com",
        "phone_whatsapp": "",
        "website": "https://paentertainmentgroup.com",
        "business": "LED video wall rental and event production services; serves corporate, concerts, and festivals in Pennsylvania and surrounding states. Instagram @paentertainmentgroup.",
        "facebook": "paentertainmentgroup",
        "instagram": "paentertainmentgroup",
        "linkedin": "",
    },
    {
        "no": 612,
        "country": "USA",
        "region": "Americas",
        "company_en": "Mitey AV",
        "company_local": "",
        "city": "New Orleans, LA",
        "contact_name": "",
        "title": "",
        "email": "events@miteyav.com",
        "phone_whatsapp": "+15042665681",
        "website": "https://miteyav.com",
        "business": "LED video wall and AV rental for events in New Orleans and Gulf Coast; confirmed WhatsApp +1(504)266-5681 via Facebook page button. Instagram @miteyav.",
        "facebook": "miteyav",
        "instagram": "miteyav",
        "linkedin": "",
    },
    {
        "no": 613,
        "country": "USA",
        "region": "Americas",
        "company_en": "Refresh LED",
        "company_local": "",
        "city": "Mechanicsburg, PA",
        "contact_name": "Josh",
        "title": "",
        "email": "josh@refreshled.com",
        "phone_whatsapp": "",
        "website": "https://refreshled.com",
        "business": "LED video wall rental and sales; phone (619)850-5037 found but mobile status unconfirmed. Instagram @getrefreshled.",
        "facebook": "refreshled",
        "instagram": "getrefreshled",
        "linkedin": "",
    },
    {
        "no": 614,
        "country": "USA",
        "region": "Americas",
        "company_en": "Worship Productions",
        "company_local": "",
        "city": "Yorba Linda, CA",
        "contact_name": "",
        "title": "",
        "email": "customerservice@worshipproductions.org",
        "phone_whatsapp": "+1 714-477-0305",
        "website": "https://worshipproductions.org",
        "business": "LED video wall rental and production services for churches, concerts, and live events; Southern California. Instagram @worshipproductions.",
        "facebook": "worshipproductions",
        "instagram": "worshipproductions",
        "linkedin": "",
    },
    {
        "no": 615,
        "country": "USA",
        "region": "Americas",
        "company_en": "CPR MultiMedia Solutions",
        "company_local": "",
        "city": "Gaithersburg, MD",
        "contact_name": "J. Studley",
        "title": "",
        "email": "info@cprmms.com",
        "phone_whatsapp": "",
        "website": "https://cprmms.com",
        "business": "Full-service AV and LED video wall rental for corporate events and conferences in Maryland/DC area. Instagram @cprmms.",
        "facebook": "cprmms",
        "instagram": "cprmms",
        "linkedin": "",
    },
    {
        "no": 616,
        "country": "USA",
        "region": "Americas",
        "company_en": "MediaQuest",
        "company_local": "",
        "city": "Pittsburgh, PA",
        "contact_name": "T. Bender",
        "title": "",
        "email": "t.bender@mediaquest.biz",
        "phone_whatsapp": "",
        "website": "https://mediaquest.biz",
        "business": "LED video wall and AV production rental company serving Pittsburgh and Western Pennsylvania; corporate events and live productions. Instagram @mediaquestpgh.",
        "facebook": "mediaquestpgh",
        "instagram": "mediaquestpgh",
        "linkedin": "",
    },
    {
        "no": 617,
        "country": "USA",
        "region": "Americas",
        "company_en": "Vortex LED Wall",
        "company_local": "",
        "city": "San Diego, CA",
        "contact_name": "",
        "title": "",
        "email": "info@vortexledwall.com",
        "phone_whatsapp": "",
        "website": "https://vortexledwall.com",
        "business": "Specialist LED video wall rental company in San Diego; fine-pitch and outdoor LED panels for events, trade shows, and concerts. Instagram @vortexledwall.",
        "facebook": "vortexledwall",
        "instagram": "vortexledwall",
        "linkedin": "",
    },
    {
        "no": 618,
        "country": "USA",
        "region": "Americas",
        "company_en": "The One Up Group",
        "company_local": "",
        "city": "West Hollywood, CA",
        "contact_name": "",
        "title": "",
        "email": "Events@TheOneUpGroup.com",
        "phone_whatsapp": "+13106662250",
        "website": "https://theoneupgroup.com",
        "business": "LED video wall and full-service AV production for music, entertainment, and corporate events in Los Angeles; confirmed WhatsApp +1(310)666-2250 via Facebook page button. Instagram @theoneupgroup.",
        "facebook": "theoneupgroup",
        "instagram": "theoneupgroup",
        "linkedin": "",
    },
]

if __name__ == "__main__":
    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "LED Leads v35"
        if new_entries:
            headers = list(new_entries[0].keys())
            ws.append(headers)
            for e in new_entries:
                ws.append([e.get(h, "") for h in headers])
        out = os.path.join(BASE, "LED_Display_Leads_v35.xlsx")
        wb.save(out)
        print(f"Saved: {out}")
    except ImportError:
        pass

    leads = load_all_leads()
    leads.extend(new_entries)
    usa = [l for l in leads if l.get("country") == "USA"]
    print(f"Total leads: {len(leads)}")
    print(f"USA: {len(usa)}")
    print("\nNew entries (v35):")
    for e in new_entries:
        wa = e.get("phone_whatsapp", "")
        print(f"  no:{e['no']} {e['company_en']} | {e['city']} | IG:@{e['instagram']} | WA:{wa or 'N/A'} | email:{e['email']}")
