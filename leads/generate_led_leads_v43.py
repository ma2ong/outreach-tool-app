"""
LED Display Leads Generator v43 — USA batch (6 companies, nos 657-662)
Raleigh NC, Knoxville TN, Charlottesville VA, New Orleans LA, Madison WI x2
"""
import json, ast, re, os
from pathlib import Path
import openpyxl
from openpyxl.styles import PatternFill, Font

base = Path(__file__).parent

# --- Load all previous leads (chain) ---
_v4_src = open(base / "generate_led_leads_v4.py", encoding="utf-8").read()
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", _v4_src, re.M | re.S).group(1))
for _vname in ("v5","v6","v7","v8","v9","v10","v11","v12","v13","v14","v15","v16",
               "v17","v18","v19","v20","v21","v22","v23","v24","v25","v26","v27",
               "v28","v29","v30","v31","v32","v33","v34","v35","v36","v37","v38",
               "v39","v40","v41","v42"):
    _path = base / f"generate_led_leads_{_vname}.py"
    if not _path.exists():
        continue
    _src = open(_path, encoding="utf-8").read()
    _m = re.search(r"^new_entries = (\[.+?^\])", _src, re.M | re.S)
    if _m:
        leads.extend(ast.literal_eval(_m.group(1)))

new_entries = [
    {
        "no": 657,
        "country": "USA",
        "region": "Americas",
        "company_en": "Triangle Media Solutions",
        "company_local": "",
        "city": "Raleigh, NC",
        "contact_name": "",
        "title": "",
        "email": "admin@trianglemediasolutions.com",
        "phone_whatsapp": "919-214-4351",
        "website": "trianglemediasolutions.com",
        "business": "LED video wall sales, installation, and rental for churches, businesses, events, and commercial spaces. Digital signage and AV integration. Serves Raleigh, Durham, Chapel Hill area (Triangle NC). Instagram @trianglemediasolutions. Website trianglemediasolutions.com",
        "facebook": "Triangle Media Solutions LLC",
        "instagram": "trianglemediasolutions",
        "linkedin": "trianglemediasolutions",
    },
    {
        "no": 658,
        "country": "USA",
        "region": "Americas",
        "company_en": "The Production Source",
        "company_local": "",
        "city": "Knoxville, TN",
        "contact_name": "",
        "title": "",
        "email": "info@theproductionsource.net",
        "phone_whatsapp": "865-210-8501",
        "website": "theproductionsource.net",
        "business": "Knoxville TN full-service AV: LED wall rentals, AV installations, conferences, concerts, corporate events, gear sales. Instagram @theproductionsource. Website theproductionsource.net",
        "facebook": "TheProductionSource",
        "instagram": "theproductionsource",
        "linkedin": "",
    },
    {
        "no": 659,
        "country": "USA",
        "region": "Americas",
        "company_en": "The AV Company",
        "company_local": "",
        "city": "Charlottesville, VA",
        "contact_name": "",
        "title": "",
        "email": "info@theavcompany.net",
        "phone_whatsapp": "434-977-8288",
        "website": "theavcompany.com",
        "business": "Virginia AV company: LED video walls, AV systems for live events, meetings, conferences. Serves Charlottesville, Harrisonburg, Richmond, Virginia Beach. FB: TheAVCompany. Website theavcompany.com",
        "facebook": "TheAVCompany",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 660,
        "country": "USA",
        "region": "Americas",
        "company_en": "Power On Productions",
        "company_local": "",
        "city": "New Orleans, LA",
        "contact_name": "",
        "title": "",
        "email": "info@poweronav.com",
        "phone_whatsapp": "985-400-3928",
        "website": "poweronav.com",
        "business": "New Orleans AV: LED video wall rentals for conferences, trade shows, galas, concerts and large event productions. Instagram @poweron4u, FB: poweronav. Website poweronav.com",
        "facebook": "poweronav",
        "instagram": "poweron4u",
        "linkedin": "",
    },
    {
        "no": 661,
        "country": "USA",
        "region": "Americas",
        "company_en": "Hinckley Productions",
        "company_local": "",
        "city": "Madison, WI",
        "contact_name": "",
        "title": "",
        "email": "info@hinckleyproductions.com",
        "phone_whatsapp": "608-819-6022",
        "website": "hinckleyproductions.com",
        "business": "Madison WI premium LED wall rentals: 18'x10' wall (2.8mm pixel pitch) for corporate events, concerts, sports venues, film production, experiential activations. Virtual production studio. Instagram @hinckleyproductions. Website hinckleyproductions.com",
        "facebook": "",
        "instagram": "hinckleyproductions",
        "linkedin": "Hinckley Design & Production LLC",
    },
    {
        "no": 662,
        "country": "USA",
        "region": "Americas",
        "company_en": "STAR Studios LLC",
        "company_local": "",
        "city": "DeForest, WI",
        "contact_name": "",
        "title": "",
        "email": "sales@starstudioswi.com",
        "phone_whatsapp": "",
        "website": "starstudioswi.com",
        "business": "Southern Wisconsin (Madison area) LED video wall rentals: weatherproof, outdoor-rated modular LED video walls for events of all sizes. Instagram @starstudioswi, FB: starstudioswi. Website starstudioswi.com",
        "facebook": "starstudioswi",
        "instagram": "starstudioswi",
        "linkedin": "",
    },
]

leads.extend(new_entries)

# --- Print summary ---
print(f"Total leads: {len(leads)}")
usa = [l for l in leads if l.get("country") == "USA"]
print(f"USA leads: {len(usa)}")
print(f"New entries: {len(new_entries)} (nos {new_entries[0]['no']}–{new_entries[-1]['no']})")

# --- Export to Excel ---
COUNTRY_COLORS = {
    "USA": "DDEEFF",
    "Korea": "FFE8CC",
    "Brazil": "E8F5E9",
    "Canada": "FFF9C4",
    "Colombia": "FCE4EC",
    "Mexico": "F3E5F5",
    "Chile": "E0F7FA",
    "Argentina": "FBE9E7",
    "Peru": "F1F8E9",
}

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "LED Leads v43"

headers = ["No", "Country", "Region", "Company EN", "Company Local", "City",
           "Contact Name", "Title", "Email", "Phone/WhatsApp",
           "Website", "Business", "Facebook", "Instagram", "LinkedIn"]
ws.append(headers)
for cell in ws[1]:
    cell.fill = PatternFill("solid", fgColor="334455")
    cell.font = Font(bold=True, color="FFFFFF")

for lead in leads:
    row = [
        lead.get("no"), lead.get("country"), lead.get("region"),
        lead.get("company_en"), lead.get("company_local"), lead.get("city"),
        lead.get("contact_name"), lead.get("title"), lead.get("email"),
        lead.get("phone_whatsapp"), lead.get("website"), lead.get("business"),
        lead.get("facebook"), lead.get("instagram"), lead.get("linkedin"),
    ]
    ws.append(row)
    color = COUNTRY_COLORS.get(lead.get("country", ""), "FFFFFF")
    for cell in ws[ws.max_row]:
        cell.fill = PatternFill("solid", fgColor=color)

ws.column_dimensions["A"].width = 6
ws.column_dimensions["D"].width = 30
ws.column_dimensions["F"].width = 25
ws.column_dimensions["I"].width = 32
ws.column_dimensions["J"].width = 20
ws.column_dimensions["K"].width = 28
ws.column_dimensions["L"].width = 60

out = base / "LED_Display_Leads_v43.xlsx"
wb.save(out)
print(f"Saved: {out}")
