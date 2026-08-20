"""
LED Display Leads v40 — USA (8 new entries, nos 635-642)
Rocket Productions USA, Meyer Pro Inc, Limitless Lights and Sound, TX LED Rental,
Illuminated Mobile, C West Entertainment, Sifi Entertainment, Master Sound Pro
"""
import ast, re, os, sys
sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(__file__)

def load_all_leads():
    _v4_src = open(os.path.join(BASE, "generate_led_leads_v4.py"), encoding="utf-8").read()
    leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", _v4_src, re.M | re.S).group(1))
    for _vname in [f"v{i}" for i in range(5, 40)]:
        _path = os.path.join(BASE, f"generate_led_leads_{_vname}.py")
        if not os.path.exists(_path): continue
        _src = open(_path, encoding="utf-8").read()
        _m = re.search(r"^new_entries = (\[.+?^\])", _src, re.M | re.S)
        if _m: leads.extend(ast.literal_eval(_m.group(1)))
    return leads

new_entries = [
    {
        "no": 635,
        "country": "USA",
        "region": "Americas",
        "company_en": "Rocket Productions USA",
        "company_local": "",
        "city": "Atlanta, GA",
        "contact_name": "",
        "title": "",
        "email": "sales@rocketprousa.com",
        "phone_whatsapp": "",
        "website": "https://www.redrocketsouth.com",
        "business": "Full-service AV and LED video wall rental for concerts, corporate events, and live productions in Atlanta and Southeast USA; clients include Atlanta United FC; Instagram @rocketprousa. Phone: (770) 738-9554 (suburban Atlanta, WA unconfirmed).",
        "facebook": "Rocketproductionsusa",
        "instagram": "rocketprousa",
        "linkedin": "rocket-productions-usa",
    },
    {
        "no": 636,
        "country": "USA",
        "region": "Americas",
        "company_en": "Meyer Pro Inc",
        "company_local": "",
        "city": "Portland, OR",
        "contact_name": "",
        "title": "",
        "email": "info@meyerproinc.com",
        "phone_whatsapp": "",
        "website": "https://meyerproinc.com",
        "business": "AV production and LED video wall rental for corporate events, nonprofits, and live events in Portland and Seattle; also sells AV equipment; Instagram @meyerproinc. Phone: (503) 855-8585 (Portland, WA unconfirmed).",
        "facebook": "meyerproinc",
        "instagram": "meyerproinc",
        "linkedin": "",
    },
    {
        "no": 637,
        "country": "USA",
        "region": "Americas",
        "company_en": "Limitless Lights and Sound",
        "company_local": "",
        "city": "Houston, TX",
        "contact_name": "Dash",
        "title": "",
        "email": "dash@limitlesslightsandsound.com",
        "phone_whatsapp": "",
        "website": "https://limitlesslightsandsound.com",
        "business": "Full-service event production company in Houston and San Antonio; LED video walls/projections, lighting design, pro audio, concerts, AV system design for hospitality, worship, sports; Instagram @limitlesslightsandsound. Phone: (512) 201-6569 (Austin TX, possibly mobile; WA unconfirmed).",
        "facebook": "limitlesslightsandsound",
        "instagram": "limitlesslightsandsound",
        "linkedin": "",
    },
    {
        "no": 638,
        "country": "USA",
        "region": "Americas",
        "company_en": "TX LED Rental",
        "company_local": "",
        "city": "Dallas, TX",
        "contact_name": "",
        "title": "",
        "email": "info@txledrental.com",
        "phone_whatsapp": "",
        "website": "https://txledrental.com",
        "business": "Specialist indoor LED screen rental company serving Dallas, Houston, San Antonio, and Austin; 10+ years experience; turnkey setup/teardown with technicians; starting at $1,000/event. Phone: (469) 818-9841 (Dallas, WA unconfirmed). No Instagram found.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 639,
        "country": "USA",
        "region": "Americas",
        "company_en": "Illuminated Mobile",
        "company_local": "",
        "city": "Chicago, IL",
        "contact_name": "",
        "title": "",
        "email": "Info@IlluminatedMobile.com",
        "phone_whatsapp": "",
        "website": "https://illuminatedmobile.com",
        "business": "Chicago-based mobile LED billboard truck and LED trailer rental company; also provides digital scoreboards and outdoor LED event screens; serves Chicago, Detroit, and Midwest markets; Instagram @illuminatedmobile. Phone: (312) 924-7979 (Chicago landline, WA unconfirmed).",
        "facebook": "IlluminatedMobile",
        "instagram": "illuminatedmobile",
        "linkedin": "",
    },
    {
        "no": 640,
        "country": "USA",
        "region": "Americas",
        "company_en": "C West Entertainment",
        "company_local": "",
        "city": "Phoenix, AZ",
        "contact_name": "",
        "title": "",
        "email": "info@djcwest.com",
        "phone_whatsapp": "",
        "website": "https://www.djcwest.com",
        "business": "Phoenix AV production company offering LED video wall rental, corporate event production, audio, and DJ services; clients in Phoenix, Scottsdale, and Arizona; website offers SMS texting on (623) 256-7887 (likely mobile; WA unconfirmed). Instagram @cwestent.",
        "facebook": "djcwest",
        "instagram": "cwestent",
        "linkedin": "c-west-entertainment",
    },
    {
        "no": 641,
        "country": "USA",
        "region": "Americas",
        "company_en": "Sifi Entertainment",
        "company_local": "",
        "city": "Atlanta, GA",
        "contact_name": "",
        "title": "",
        "email": "events@sifient.com",
        "phone_whatsapp": "",
        "website": "https://sifient.com",
        "business": "Atlanta AV and event production company; LED screen rentals, AV rentals, mobile stage, uplighting, DJ services; WeddingWire award winner 2017-2023; serves Atlanta area and worldwide. Phone: (404) 376-4064. Instagram @sifientertainment.",
        "facebook": "Sifi-Entertainment-90402529907",
        "instagram": "sifientertainment",
        "linkedin": "",
    },
    {
        "no": 642,
        "country": "USA",
        "region": "Americas",
        "company_en": "Master Sound Pro",
        "company_local": "",
        "city": "Fort Lauderdale, FL",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "",
        "website": "https://mastersoundpro.com",
        "business": "South Florida AV and event production company in Fort Lauderdale; LED video wall rental for corporate events, concerts, and festivals in Miami-Dade and Broward County; also does sound, lighting, stage, generator rental. Phone: (305) 972-6838. Instagram @mastersoundpro.",
        "facebook": "",
        "instagram": "mastersoundpro",
        "linkedin": "",
    },
]

if __name__ == "__main__":
    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "LED Leads v40"
        if new_entries:
            headers = list(new_entries[0].keys())
            ws.append(headers)
            for e in new_entries:
                ws.append([e.get(h, "") for h in headers])
        out = os.path.join(BASE, "LED_Display_Leads_v40.xlsx")
        wb.save(out)
        print(f"Saved: {out}")
    except ImportError:
        pass

    leads = load_all_leads()
    leads.extend(new_entries)
    usa = [l for l in leads if l.get("country") == "USA"]
    print(f"Total leads: {len(leads)}")
    print(f"USA: {len(usa)}")
    print("\nNew entries (v40):")
    for e in new_entries:
        print(f"  no:{e['no']} {e['company_en']} | {e['city']} | IG:@{e['instagram'] or 'N/A'} | email:{e['email'] or 'N/A'}")
