"""
LED Display Leads v36 — USA (7 new entries, nos 619-625)
Elite Displays, LED Show Vision, Verum AV Solutions, Power Factory Productions,
Arizona Stage, Palm Productions and Events, Empire AV
"""
import ast, re, os, sys
sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(__file__)

def load_all_leads():
    _v4_src = open(os.path.join(BASE, "generate_led_leads_v4.py"), encoding="utf-8").read()
    leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", _v4_src, re.M | re.S).group(1))
    for _vname in [f"v{i}" for i in range(5, 36)]:
        _path = os.path.join(BASE, f"generate_led_leads_{_vname}.py")
        if not os.path.exists(_path): continue
        _src = open(_path, encoding="utf-8").read()
        _m = re.search(r"^new_entries = (\[.+?^\])", _src, re.M | re.S)
        if _m: leads.extend(ast.literal_eval(_m.group(1)))
    return leads

new_entries = [
    {
        "no": 619,
        "country": "USA",
        "region": "Americas",
        "company_en": "Elite Displays",
        "company_local": "",
        "city": "Las Vegas, NV",
        "contact_name": "",
        "title": "",
        "email": "info@elitedisplays.com",
        "phone_whatsapp": "",
        "website": "https://elitedisplays.com",
        "business": "High-value LED display integrator for sports, casinos, and hospitality venues; completed projects for Cleveland Cavaliers, UCONN, Lamar University, Resorts World Las Vegas, Wynn Casino, The Venetian, Rogers Arena (Vancouver Canucks); also offers rental/staging LED. Instagram @elitedisplays (Las Vegas, NV). Phone: (702) 410-2232 (WA unconfirmed).",
        "facebook": "61564864314371",
        "instagram": "elitedisplays",
        "linkedin": "e-lite-displays",
    },
    {
        "no": 620,
        "country": "USA",
        "region": "Americas",
        "company_en": "LED Show Vision",
        "company_local": "",
        "city": "Las Vegas, NV",
        "contact_name": "",
        "title": "",
        "email": "connect@vitaeventsgroup.com",
        "phone_whatsapp": "",
        "website": "https://ledshowvision.com",
        "business": "Las Vegas LED video wall rental specialist for trade shows, corporate events, and weddings; P1.8 HD walls, champagne walls, LED display bars; parent company Vita Events Group. Phone: (702) 745-8143 (WA unconfirmed). Instagram not found.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 621,
        "country": "USA",
        "region": "Americas",
        "company_en": "Verum AV Solutions",
        "company_local": "",
        "city": "Houston, TX",
        "contact_name": "",
        "title": "",
        "email": "info@verumav.com",
        "phone_whatsapp": "",
        "website": "https://verumav.com",
        "business": "Houston AV and LED screen rental company for corporate events and trade shows; Phone: (346) 837-8628 (346 area code, likely mobile; WA unconfirmed). Instagram @verumavsolutions, Facebook profile.php?id=61559437112925.",
        "facebook": "61559437112925",
        "instagram": "verumavsolutions",
        "linkedin": "",
    },
    {
        "no": 622,
        "country": "USA",
        "region": "Americas",
        "company_en": "Power Factory Productions",
        "company_local": "",
        "city": "Houston, TX",
        "contact_name": "",
        "title": "",
        "email": "info@powerfactorypro.com",
        "phone_whatsapp": "",
        "website": "https://powerfactoryproductions.com",
        "business": "Full-service AV production company in Houston; LED video walls, video wall rental, and systems integration; also does audio/sound/stage. Phone: (281) 630-6900 (suburban Houston, likely landline). Instagram @powerfactoryproductions, Facebook powerfactoryproductions.",
        "facebook": "powerfactoryproductions",
        "instagram": "powerfactoryproductions",
        "linkedin": "",
    },
    {
        "no": 623,
        "country": "USA",
        "region": "Americas",
        "company_en": "Arizona Stage",
        "company_local": "",
        "city": "Scottsdale, AZ",
        "contact_name": "Jake",
        "title": "",
        "email": "Jake@arizonastage.com",
        "phone_whatsapp": "",
        "website": "https://arizonastage.com",
        "business": "LED video wall rental and stage production serving Phoenix, Scottsdale, and statewide Arizona; delivers to multiple AZ cities. Instagram @arizonastage, Facebook @arizonastagellc, TikTok @arizona_stage.",
        "facebook": "arizonastagellc",
        "instagram": "arizonastage",
        "linkedin": "",
    },
    {
        "no": 624,
        "country": "USA",
        "region": "Americas",
        "company_en": "Palm Productions and Events",
        "company_local": "",
        "city": "Tampa, FL",
        "contact_name": "",
        "title": "",
        "email": "hello@palmproductionsandevents.com",
        "phone_whatsapp": "+1 855-565-0900",
        "website": "https://palmproductionsandevents.com",
        "business": "LED video wall, lighting, sound, and event production services in Tampa and South Florida; serves galas, corporate events, and concerts. Instagram @palmproductionsandevents. Phone confirmed via IG DM reply 2026-05-23.",
        "facebook": "palmproductionsandevents",
        "instagram": "palmproductionsandevents",
        "linkedin": "",
    },
    {
        "no": 625,
        "country": "USA",
        "region": "Americas",
        "company_en": "Empire AV",
        "company_local": "",
        "city": "Orlando, FL",
        "contact_name": "",
        "title": "",
        "email": "info@empireentertainment.us",
        "phone_whatsapp": "",
        "website": "https://empireav.com/us",
        "business": "Orlando LED video wall and AV equipment rental for corporate events, weddings, and trade shows; indoor/outdoor/mobile LED walls; serving Central Florida. Phone: (407) 440-8060 (WA unconfirmed). Instagram @empire_djs, Facebook empirepage.",
        "facebook": "empirepage",
        "instagram": "empire_djs",
        "linkedin": "",
    },
]

if __name__ == "__main__":
    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "LED Leads v36"
        if new_entries:
            headers = list(new_entries[0].keys())
            ws.append(headers)
            for e in new_entries:
                ws.append([e.get(h, "") for h in headers])
        out = os.path.join(BASE, "LED_Display_Leads_v36.xlsx")
        wb.save(out)
        print(f"Saved: {out}")
    except ImportError:
        pass

    leads = load_all_leads()
    leads.extend(new_entries)
    usa = [l for l in leads if l.get("country") == "USA"]
    print(f"Total leads: {len(leads)}")
    print(f"USA: {len(usa)}")
    print("\nNew entries (v36):")
    for e in new_entries:
        print(f"  no:{e['no']} {e['company_en']} | {e['city']} | IG:@{e['instagram'] or 'N/A'} | email:{e['email']}")
