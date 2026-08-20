"""
LED Display Leads v30 — USA (6 new entries, nos 568-573)
Airborne Visuals, ATH Productions, GeoEvent, TLL Top LED Lumination, Bounce Multimedia, TrueBlue Exhibits
All confirmed new (dedup passed). Trade show, event production, and AV rental companies.
"""
import ast, re, os, sys
sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(__file__)

def load_all_leads():
    _v4_src = open(os.path.join(BASE, "generate_led_leads_v4.py"), encoding="utf-8").read()
    leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", _v4_src, re.M | re.S).group(1))
    for _vname in [f"v{i}" for i in range(5, 30)]:
        _path = os.path.join(BASE, f"generate_led_leads_{_vname}.py")
        if not os.path.exists(_path): continue
        _src = open(_path, encoding="utf-8").read()
        _m = re.search(r"^new_entries = (\[.+?^\])", _src, re.M | re.S)
        if _m: leads.extend(ast.literal_eval(_m.group(1)))
    return leads

new_entries = [
    {
        "no": 568,
        "country": "USA",
        "region": "Americas",
        "company_en": "Airborne Visuals",
        "company_local": "Airborne Visuals",
        "city": "Las Vegas, NV (also Orlando, Chicago, NYC, international)",
        "contact_name": "",
        "title": "",
        "email": "info@airbornevisuals.com",
        "phone_whatsapp": "800-821-2241",
        "website": "airbornevisuals.com",
        "business": "Trade show LED video wall booth rental. Pre-configured LED booth kits (10x10 to 40x40+). Serves Las Vegas, Orlando, Chicago, NYC and international venues. Instagram @airbornevisuals (333 followers, 55 posts); email confirmed from website",
        "facebook": "",
        "instagram": "airbornevisuals",
        "linkedin": "",
    },
    {
        "no": 569,
        "country": "USA",
        "region": "Americas",
        "company_en": "ATH Productions",
        "company_local": "ATH Productions",
        "city": "Houston, TX (Humble)",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "409-860-5551",
        "website": "athproductions.com",
        "business": "Full-service event production company. LED wall rental, audio, lighting, staging for corporate events, weddings, concerts, trade shows. Serves Houston, Dallas, Austin, Atlanta, San Antonio. NovaStar-compatible LED systems. Instagram @audiotekhouston (1,412 followers, 238 posts)",
        "facebook": "audiotekhouston",
        "instagram": "audiotekhouston",
        "linkedin": "",
    },
    {
        "no": 570,
        "country": "USA",
        "region": "Americas",
        "company_en": "GeoEvent",
        "company_local": "GeoEvent",
        "city": "Los Angeles, CA",
        "contact_name": "",
        "title": "",
        "email": "info@geoevent.net",
        "phone_whatsapp": "818-478-2009",
        "website": "geoevent.net",
        "business": "West Coast AV rental company, 1000s of LED tiles in stock. LED video wall P1.9, P2.6, P3.9mm panels. Serves LA, Las Vegas, San Francisco, San Diego. Full production services for major tours, corporate shows, esports events. Instagram @geoeventla",
        "facebook": "",
        "instagram": "geoeventla",
        "linkedin": "",
    },
    {
        "no": 571,
        "country": "USA",
        "region": "Americas",
        "company_en": "TLL Top LED Lumination",
        "company_local": "TLL Top LED Lumination",
        "city": "Orlando, FL / Las Vegas, NV",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "407-286-5244",
        "website": "topledlumination.com",
        "business": "LED video wall rentals and sales for all events. Two locations: Orlando (407.286.5244) and Las Vegas (702.909.4214). Turn-key packages with on-site technician service. Sells P1.9, P2.5, P2.8mm LED panels. Instagram @led_video_walls",
        "facebook": "",
        "instagram": "led_video_walls",
        "linkedin": "",
    },
    {
        "no": 572,
        "country": "USA",
        "region": "Americas",
        "company_en": "Bounce Multimedia",
        "company_local": "Bounce Multimedia",
        "city": "Houston (Humble), TX",
        "contact_name": "",
        "title": "",
        "email": "sales@bouncemultimedia.com",
        "phone_whatsapp": "409-860-5551",
        "website": "bouncemultimedia.com",
        "business": "LED wall rental for concerts, conferences, trade shows in Houston TX area. NovaStar processors + DVS LED wall systems. 1500 sq ft studio + maintenance facility. Since 2003. Email confirmed from website.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 573,
        "country": "USA",
        "region": "Americas",
        "company_en": "TrueBlue Exhibits",
        "company_local": "TrueBlue Exhibits",
        "city": "Las Vegas, NV",
        "contact_name": "",
        "title": "",
        "email": "info@trueblue-exhibits.com",
        "phone_whatsapp": "",
        "website": "trueblue-exhibits.com",
        "business": "Custom trade show booth + LED video wall rental/sales, nationwide. Factory direct LED walls for trade shows. Serves Las Vegas, NYC, SF, Orlando, Chicago. LED panel configurations from 10x10 to large format. Email confirmed from website.",
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

    out = os.path.join(BASE, "LED_Display_Leads_v19.xlsx")
    wb.save(out)
    print(f"Saved: {out}")
