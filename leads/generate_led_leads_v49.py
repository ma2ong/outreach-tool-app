"""
generate_led_leads_v49.py
New entries: nos 705-708 (4 USA leads)
Cities: San Diego CA / Austin TX / Albuquerque NM / San Antonio TX
Note: SoFlo Studio/Master Sound/MediaQuest/Ohio LED Wall/All Pro AV/LV Led Video Wall
      all already in DB — excluded from this version.
"""
import ast, re, os

_base = os.path.dirname(__file__)

def _load(path):
    return open(path, encoding="utf-8").read()

_v4_src = _load(os.path.join(_base, "generate_led_leads_v4.py"))
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", _v4_src, re.M | re.S).group(1))

for _vname in ("v5","v6","v7","v8","v9","v10","v11","v12","v13","v14","v15","v16",
               "v17","v18","v19","v20","v21","v22","v23","v24","v25","v26","v27",
               "v28","v29","v30","v31","v32","v33","v34","v35","v36","v37","v38",
               "v39","v40","v41","v42","v43","v44","v45","v46","v47","v48"):
    _path = os.path.join(_base, f"generate_led_leads_{_vname}.py")
    if not os.path.exists(_path):
        continue
    _src = _load(_path)
    _m = re.search(r"^new_entries = (\[.+?^\])", _src, re.M | re.S)
    if _m:
        leads.extend(ast.literal_eval(_m.group(1)))

new_entries = [
    {
        "no": 705,
        "country": "USA",
        "region": "Americas",
        "company_en": "San Diego Video Wall",
        "company_local": "",
        "city": "San Diego, CA",
        "contact_name": "",
        "title": "",
        "email": "hello@videowallsandiego.com",
        "phone_whatsapp": "",
        "website": "videowallsandiego.com",
        "business": "Premium LED display screen rental for indoor, outdoor & mobile events across San Diego County; video walls, LED trailers, curved & modular setups.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 706,
        "country": "USA",
        "region": "Americas",
        "company_en": "TSV Sound & Vision",
        "company_local": "",
        "city": "Austin, TX",
        "contact_name": "",
        "title": "",
        "email": "info@tsvatx.com",
        "phone_whatsapp": "512-593-5155",
        "website": "tsvatx.com",
        "business": "Austin-based full-service AV rental; LED video walls (indoor & outdoor), audio, lighting & backline for corporate events and live productions. Instagram @tsvusa.",
        "facebook": "",
        "instagram": "tsvusa",
        "linkedin": "",
    },
    {
        "no": 707,
        "country": "USA",
        "region": "Americas",
        "company_en": "SoFlo Studio",
        "company_local": "",
        "city": "Fort Lauderdale, FL",
        "contact_name": "",
        "title": "",
        "email": "info@soflostudio.com",
        "phone_whatsapp": "954-446-5619",
        "website": "soflostudio.com",
        "business": "Miami/Fort Lauderdale LED screen & video wall rental, studio, film production & live broadcasting for events of all sizes across South Florida. Instagram @soflostudio.",
        "facebook": "",
        "instagram": "soflostudio",
        "linkedin": "",
    },
    {
        "no": 708,
        "country": "USA",
        "region": "Americas",
        "company_en": "Master Sound Productions",
        "company_local": "",
        "city": "Fort Lauderdale, FL",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "305-972-6838",
        "website": "mastersoundpro.com",
        "business": "South Florida AV production company since 1996; LED video wall rental & installation for corporate events, trade shows, concerts & parties across Miami-Broward-Palm Beach. Instagram @mastersoundpro.",
        "facebook": "",
        "instagram": "mastersoundpro",
        "linkedin": "",
    },
    {
        "no": 709,
        "country": "USA",
        "region": "Americas",
        "company_en": "MediaQuest",
        "company_local": "",
        "city": "Pittsburgh, PA",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "412-921-3360",
        "website": "mediaquest.biz",
        "business": "Pittsburgh AV production company 30+ years; high-resolution LED wall integration, large-format displays, live streaming & full event production. Instagram @mediaquestpgh.",
        "facebook": "",
        "instagram": "mediaquestpgh",
        "linkedin": "",
    },
    {
        "no": 710,
        "country": "USA",
        "region": "Americas",
        "company_en": "Ohio LED Wall",
        "company_local": "",
        "city": "Cleveland, OH",
        "contact_name": "",
        "title": "",
        "email": "info@ohioledwall.com",
        "phone_whatsapp": "216-233-8544",
        "website": "ohioledwall.com",
        "business": "Northeast Ohio LED video wall rentals, sales & installation; displays up to 7x20 ft for weddings, corporate events, concerts & permanent commercial installs; serves Cleveland, Akron, Canton.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 711,
        "country": "USA",
        "region": "Americas",
        "company_en": "All Pro Audio Visual",
        "company_local": "",
        "city": "Milwaukee, WI",
        "contact_name": "",
        "title": "",
        "email": "info@allproaudiovisual.com",
        "phone_whatsapp": "888-613-3335",
        "website": "allproaudiovisual.com",
        "business": "Milwaukee-based AV company; LED video walls, LED tile & 4K projector rentals for corporate events, conferences & trade shows across southeast Wisconsin. Instagram @allproaudiovisual.",
        "facebook": "",
        "instagram": "allproaudiovisual",
        "linkedin": "",
    },
    {
        "no": 712,
        "country": "USA",
        "region": "Americas",
        "company_en": "LV Led Video Wall",
        "company_local": "",
        "city": "Las Vegas, NV",
        "contact_name": "",
        "title": "",
        "email": "info@lvledvideowall.com",
        "phone_whatsapp": "702-807-6444",
        "website": "lvledvideowall.com",
        "business": "Las Vegas LED video wall rental & integrated event production for trade shows, conventions & corporate events across Nevada; in-house technical team.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 713,
        "country": "USA",
        "region": "Americas",
        "company_en": "Alliance Audio Visual",
        "company_local": "",
        "city": "Albuquerque, NM",
        "contact_name": "",
        "title": "",
        "email": "rentals@allianceav.com",
        "phone_whatsapp": "505-341-3900",
        "website": "allianceav.com",
        "business": "New Mexico's largest professional AV inventory; LED displays, video production & event support for corporate meetings, conferences & hybrid events; serves the Southwest.",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 714,
        "country": "USA",
        "region": "Americas",
        "company_en": "VEGAS Event Group",
        "company_local": "",
        "city": "San Antonio, TX",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "210-527-7840",
        "website": "ledvideowallrentalsanantonio.com",
        "business": "Award-winning LED video wall rental company in San Antonio TX; wide range of video wall sizes for corporate events, galas & productions across Central Texas. Instagram @vegaseventgroup.",
        "facebook": "",
        "instagram": "vegaseventgroup",
        "linkedin": "",
    },
]

leads.extend(new_entries)

if __name__ == "__main__":
    import openpyxl
    from openpyxl.styles import PatternFill, Font
    from pathlib import Path

    base = Path(_base)
    usa = [l for l in leads if l.get("country") == "USA"]
    print(f"v49: {len(new_entries)} new entries, nos {new_entries[0]['no']}-{new_entries[-1]['no']}")
    print(f"Total: {len(leads)}, USA: {len(usa)}")
    for e in new_entries:
        ig = f"@{e['instagram']}" if e.get("instagram") else "no IG"
        print(f"  {e['no']} {e['company_en']} ({e['city']}) {ig} {e.get('email','') or 'no email'}")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Leads"

    headers = [
        "No", "Country", "Region", "Company (EN)", "Company (Local)",
        "City", "Contact Name", "Title", "Email", "Phone/WhatsApp",
        "Website", "Business", "Facebook", "Instagram", "LinkedIn",
    ]
    field_keys = [
        "no", "country", "region", "company_en", "company_local",
        "city", "contact_name", "title", "email", "phone_whatsapp",
        "website", "business", "facebook", "instagram", "linkedin",
    ]

    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(bold=True, color="FFFFFF")

    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font

    alt_fill = PatternFill("solid", fgColor="D6E4F0")

    for row_idx, lead in enumerate(leads, 2):
        for col_idx, key in enumerate(field_keys, 1):
            ws.cell(row=row_idx, column=col_idx, value=lead.get(key, ""))
        if row_idx % 2 == 0:
            for col_idx in range(1, len(headers) + 1):
                ws.cell(row=row_idx, column=col_idx).fill = alt_fill

    col_widths = [6, 10, 10, 28, 20, 18, 18, 16, 32, 18, 28, 60, 25, 25, 25]
    for col_idx, width in enumerate(col_widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width

    out_path = base / "LED_Display_Leads_v49.xlsx"
    wb.save(out_path)
    print(f"Saved {out_path}")
