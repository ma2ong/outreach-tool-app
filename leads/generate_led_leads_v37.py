"""
LED Display Leads v37 — USA (9 new entries, nos 626-634)
New cities: Chicago (x3), Dallas, Denver, Seattle, Boston, NYC, Philadelphia
Channels: Email (7), IG DM (5), FB (4)
"""
import ast, re, os, sys
sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(__file__)

def load_all_leads():
    _v4_src = open(os.path.join(BASE, "generate_led_leads_v4.py"), encoding="utf-8").read()
    leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", _v4_src, re.M | re.S).group(1))
    for _vname in [f"v{i}" for i in range(5, 37)]:
        _path = os.path.join(BASE, f"generate_led_leads_{_vname}.py")
        if not os.path.exists(_path): continue
        _src = open(_path, encoding="utf-8").read()
        _m = re.search(r"^new_entries = (\[.+?^\])", _src, re.M | re.S)
        if _m: leads.extend(ast.literal_eval(_m.group(1)))
    return leads

new_entries = [
    {
        "no": 626,
        "country": "USA",
        "region": "Americas",
        "company_en": "Vantage Production Group",
        "company_local": "",
        "city": "Chicago, IL",
        "contact_name": "",
        "title": "",
        "email": "info@vantagepg.com",
        "phone_whatsapp": "+1 815-469-0000",
        "website": "https://vantagepg.com",
        "business": "Full-service AV, LED video wall, audio, lighting, and staging; 20+ years in Chicago/Midwest; formerly Sound Works Productions; concerts, corporate events, LED rentals. Facebook: vantageproductiongroup. Email confirmed from website.",
        "facebook": "vantageproductiongroup",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 627,
        "country": "USA",
        "region": "Americas",
        "company_en": "Chicago Audio & Lighting",
        "company_local": "",
        "city": "Schaumburg, IL",
        "contact_name": "",
        "title": "",
        "email": "chicagoavrentals@gmail.com",
        "phone_whatsapp": "+1 630-688-2886",
        "website": "https://achicagoavrentals.com",
        "business": "AV rental company serving Chicago metro; LED walls, projectors, audio, lighting; 24hr technical support; Schaumburg, IL base (1803 W Wise Rd). Email confirmed from contact page.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 628,
        "country": "USA",
        "region": "Americas",
        "company_en": "Insane Impact",
        "company_local": "",
        "city": "Chicago, IL",
        "contact_name": "D. Steffen",
        "title": "",
        "email": "Dsteffen@insaneimpact.com",
        "phone_whatsapp": "+1 515-349-7708",
        "website": "https://www.insaneimpact.com",
        "business": "Premier LED screen rental provider; serving Chicago since 2015; indoor and outdoor LED for events, concerts, corporate. Instagram @insaneimpact; Facebook: insaneimpact. Email confirmed from contact page.",
        "facebook": "insaneimpact",
        "instagram": "insaneimpact",
        "linkedin": "",
    },
    {
        "no": 629,
        "country": "USA",
        "region": "Americas",
        "company_en": "CMG Visuals",
        "company_local": "",
        "city": "Dallas, TX",
        "contact_name": "",
        "title": "",
        "email": "sales@cmgvisuals.com",
        "phone_whatsapp": "+1 214-714-2153",
        "website": "https://www.cmgvisuals.com",
        "business": "LED video wall rental & production services; Dallas-based; corporate events, trade shows, concerts; completed installs at Gilley's Dallas and major DFW venues. Instagram @cmgvisualsled. Email confirmed from website.",
        "facebook": "",
        "instagram": "cmgvisualsled",
        "linkedin": "",
    },
    {
        "no": 630,
        "country": "USA",
        "region": "Americas",
        "company_en": "Denver Display",
        "company_local": "",
        "city": "Denver, CO",
        "contact_name": "",
        "title": "",
        "email": "support@denverdisplay.com",
        "phone_whatsapp": "+1 720-314-8035",
        "website": "https://www.denverdisplay.com",
        "business": "HD video wall rentals, staging, and AV event management; Denver HQ with Chicago and Las Vegas production facilities; serves corporate, conferences, trade shows. Facebook: DenverDisplay. Email confirmed from contact page.",
        "facebook": "DenverDisplay",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 631,
        "country": "USA",
        "region": "Americas",
        "company_en": "Seattle Video Wall",
        "company_local": "",
        "city": "Seattle, WA",
        "contact_name": "",
        "title": "",
        "email": "hello@seattlevideowall.com",
        "phone_whatsapp": "",
        "website": "https://seattlevideowall.com",
        "business": "Professional LED screen rental across Seattle; serves Washington State Convention Center, Climate Pledge Arena, and major venues; indoor and outdoor LED video wall. Email confirmed from website.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 632,
        "country": "USA",
        "region": "Americas",
        "company_en": "Boston Audio Rentals",
        "company_local": "",
        "city": "Norwood, MA",
        "contact_name": "",
        "title": "",
        "email": "info@BostonAudioRentals.com",
        "phone_whatsapp": "+1 617-888-5360",
        "website": "https://bostonaudiorentals.com",
        "business": "LED wall rental + full AV for Boston-area events; conferences, corporate, concerts; Norwood, MA base. Instagram @bostonaudiorentals (Facebook: bostonaudiorentalsma). Email confirmed from contact page.",
        "facebook": "bostonaudiorentalsma",
        "instagram": "bostonaudiorentals",
        "linkedin": "",
    },
    {
        "no": 633,
        "country": "USA",
        "region": "Americas",
        "company_en": "New Image Event Productions",
        "company_local": "",
        "city": "Jamaica, NY",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+1 646-287-5002",
        "website": "https://www.newimageeventproductions.com",
        "business": "LED video wall rental & sales; Jamaica, Queens, NYC; serves Boston, Philadelphia, NYC metro; Instagram @nie_nyc. Phone confirmed from website.",
        "facebook": "",
        "instagram": "nie_nyc",
        "linkedin": "",
    },
    {
        "no": 634,
        "country": "USA",
        "region": "Americas",
        "company_en": "A.V. Rental Services Inc",
        "company_local": "",
        "city": "Philadelphia, PA",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+1 800-695-5943",
        "website": "https://www.audiovisualrenting.com",
        "business": "20-year LED video wall rental company; Philadelphia-based; indoor/outdoor LED for corporate events, trade shows. Instagram @philly_audio_visual; Facebook: AVRentals.",
        "facebook": "AVRentals",
        "instagram": "philly_audio_visual",
        "linkedin": "",
    },
]


if __name__ == "__main__":
    import openpyxl
    from openpyxl.styles import PatternFill

    COUNTRY_COLORS = {
        "Korea":     "FFF2CC",
        "USA":       "DDEEFF",
        "Brazil":    "E2EFDA",
        "Canada":    "FCE4D6",
        "Chile":     "EAD1DC",
        "Argentina": "D9E1F2",
        "Colombia":  "F4CCCC",
        "Peru":      "FFE5B4",
        "Mexico":    "D5E8D4",
    }

    all_leads = load_all_leads()
    all_leads.extend(new_entries)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "LED Leads"
    headers = ["no","country","region","company_en","company_local","city","contact_name","title",
               "email","phone_whatsapp","website","business","facebook","instagram","linkedin"]
    ws.append(headers)

    for lead in all_leads:
        row = [lead.get(h, "") for h in headers]
        ws.append(row)
        color = COUNTRY_COLORS.get(lead.get("country", ""), "FFFFFF")
        fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
        for cell in ws[ws.max_row]:
            cell.fill = fill

    out = os.path.join(BASE, "LED_Display_Leads_v37.xlsx")
    wb.save(out)
    print(f"Saved {out} with {len(all_leads)} leads")
    usa = [l for l in all_leads if l.get("country") == "USA"]
    print(f"USA total: {len(usa)}")
