"""
LED Display Leads v31 — USA (7 new entries, nos 574-580)
Event Smart Technology, LED Rentals Houston, Pacific Coast Entertainment,
Audio Video LA, LV Led Video Wall, Atlanta Special FX, All Pro Audio Visual
All confirmed new (dedup passed). LED wall rental, AV production, event companies.
"""
import ast, re, os, sys
sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(__file__)

def load_all_leads():
    _v4_src = open(os.path.join(BASE, "generate_led_leads_v4.py"), encoding="utf-8").read()
    leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", _v4_src, re.M | re.S).group(1))
    for _vname in [f"v{i}" for i in range(5, 31)]:
        _path = os.path.join(BASE, f"generate_led_leads_{_vname}.py")
        if not os.path.exists(_path): continue
        _src = open(_path, encoding="utf-8").read()
        _m = re.search(r"^new_entries = (\[.+?^\])", _src, re.M | re.S)
        if _m: leads.extend(ast.literal_eval(_m.group(1)))
    return leads

new_entries = [
    {
        "no": 574,
        "country": "USA",
        "region": "Americas",
        "company_en": "Event Smart Technology",
        "company_local": "Event Smart Technology",
        "city": "Las Vegas, NV",
        "contact_name": "",
        "title": "",
        "email": "info@eventstecnology.com",
        "phone_whatsapp": "702-702-9792",
        "website": "eventstecnology.com",
        "business": "LED Spheres and LED Screen rentals, event production and immersive event design. Serves Las Vegas, Nashville, Denver, Atlanta, Phoenix and nationwide. Instagram @event_technology_services (668 followers); email and phone confirmed from website",
        "facebook": "",
        "instagram": "event_technology_services",
        "linkedin": "",
    },
    {
        "no": 575,
        "country": "USA",
        "region": "Americas",
        "company_en": "LED Rentals Houston",
        "company_local": "LED Rentals Houston",
        "city": "Houston, TX",
        "contact_name": "",
        "title": "",
        "email": "ledrentalshouston@yahoo.com",
        "phone_whatsapp": "832-754-5644",
        "website": "ledrentalshouston.com",
        "business": "LED screens, stages, and full production rental in Houston and surrounding areas. Instagram @ledrentalshouston (705 followers, 120 posts); email and phone confirmed from Instagram bio",
        "facebook": "ledrentalshouston",
        "instagram": "ledrentalshouston",
        "linkedin": "",
    },
    {
        "no": 576,
        "country": "USA",
        "region": "Americas",
        "company_en": "Pacific Coast Entertainment",
        "company_local": "Pacific Coast Entertainment",
        "city": "Huntington Beach, CA",
        "contact_name": "",
        "title": "",
        "email": "info@gopce.com",
        "phone_whatsapp": "866-335-4723",
        "website": "gopce.com",
        "business": "Full-service live event production company. LED video walls, touring, lighting, audio, staging. Serves OC + LA area and beyond. Built LED installations at Great Park Live. Instagram @pacificcoastentertainment (1,432 followers, 359 posts); email confirmed from website",
        "facebook": "PacificCoastEntertainment",
        "instagram": "pacificcoastentertainment",
        "linkedin": "",
    },
    {
        "no": 577,
        "country": "USA",
        "region": "Americas",
        "company_en": "Audio Video LA",
        "company_local": "Audio Video LA",
        "city": "Los Angeles, CA",
        "contact_name": "",
        "title": "",
        "email": "info@audiovideola.com",
        "phone_whatsapp": "818-679-8104",
        "website": "audiovideola.com",
        "business": "Full-service AV rental company in Los Angeles. LED walls, projectors, screens, staging, lighting, broadcasting, webcasting for corporate and private events. 600 S Spring St, LA. Instagram @audiovideola (1,451 followers, 2,848 posts); email confirmed from website",
        "facebook": "AudioVideoLA",
        "instagram": "audiovideola",
        "linkedin": "",
    },
    {
        "no": 578,
        "country": "USA",
        "region": "Americas",
        "company_en": "LV Led Video Wall",
        "company_local": "LV Led Video Wall",
        "city": "Las Vegas, NV",
        "contact_name": "",
        "title": "",
        "email": "info@lvledvideowall.com",
        "phone_whatsapp": "702-807-6444",
        "website": "lvledvideowall.com",
        "business": "LED video wall rental and sales for Las Vegas and Nevada. Exhibitions, shows, conferences, trade show booths. Over 10 years in business. 6180 N Hollywood Blvd, Las Vegas. Email confirmed from website",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 579,
        "country": "USA",
        "region": "Americas",
        "company_en": "Atlanta Special FX",
        "company_local": "Atlanta Special FX",
        "city": "Atlanta, GA",
        "contact_name": "Mike W",
        "title": "",
        "email": "mikew@atlantaspecialfx.com",
        "phone_whatsapp": "888-664-0097",
        "website": "atlspecialfx.com",
        "business": "Special effects + LED video wall rental company serving nationwide. High-brightness LED video walls (up to 5000 nit) for indoor/outdoor events, concerts, corporate shows. Since 2008. Instagram @atlspecialfx (3,098 followers); email confirmed from website",
        "facebook": "AtlantaSpecialFX",
        "instagram": "atlspecialfx",
        "linkedin": "",
    },
    {
        "no": 580,
        "country": "USA",
        "region": "Americas",
        "company_en": "All Pro Audio Visual",
        "company_local": "All Pro Audio Visual",
        "city": "USA (nationwide)",
        "contact_name": "",
        "title": "",
        "email": "Info@allproaudiovisual.com",
        "phone_whatsapp": "",
        "website": "allproaudiovisual.com",
        "business": "Nationwide AV rental company since 2010. LED tile rentals (3mm-7mm) and seamless video wall rentals in multiple US cities including LA, Fort Lauderdale, Mobile AL, San Jose, Pensacola. Conferences, trade shows, corporate events. Email confirmed from website",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
]


if __name__ == "__main__":
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

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

    all_leads = load_all_leads() + new_entries
    print(f"Total leads: {len(all_leads)}")
    country_counts = {}
    for l in all_leads:
        c = l.get("country", "?")
        country_counts[c] = country_counts.get(c, 0) + 1
    for c, n in sorted(country_counts.items()):
        print(f"  {c}: {n}")

    headers = ["no","country","region","company_en","company_local","city","contact_name","title",
               "email","phone_whatsapp","website","business","facebook","instagram","linkedin"]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "LED Leads"

    header_fill = PatternFill("solid", fgColor="2C3E50")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    thin = Side(style="thin", color="CCCCCC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border

    for row_idx, lead in enumerate(all_leads, 2):
        color = COUNTRY_COLORS.get(lead.get("country", ""), "FFFFFF")
        fill = PatternFill("solid", fgColor=color)
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=row_idx, column=col, value=lead.get(h, ""))
            cell.fill = fill
            cell.border = border
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    col_widths = [6,10,10,28,20,30,16,16,32,18,28,60,24,24,24]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.row_dimensions[1].height = 22
    ws.freeze_panes = "A2"

    out = os.path.join(BASE, "LED_Display_Leads_v20.xlsx")
    wb.save(out)
    print(f"Saved: {out}")
