"""
LED Display Leads v23 — Colombia (Bogota, Medellin, Cartagena)
5 new Colombia entries, nos 537-541
"""
import ast, re, os, sys
sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(__file__)

def load_all_leads():
    _v4_src = open(os.path.join(BASE, "generate_led_leads_v4.py"), encoding="utf-8").read()
    leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", _v4_src, re.M | re.S).group(1))
    for _vname in [f"v{i}" for i in range(5, 23)]:
        _path = os.path.join(BASE, f"generate_led_leads_{_vname}.py")
        if not os.path.exists(_path): continue
        _src = open(_path, encoding="utf-8").read()
        _m = re.search(r"^new_entries = (\[.+?^\])", _src, re.M | re.S)
        if _m: leads.extend(ast.literal_eval(_m.group(1)))
    return leads

new_entries = [
    {
        "no": 537,
        "country": "Colombia",
        "region": "Americas",
        "company_en": "Innvector SAS",
        "company_local": "INNVECTOR SAS",
        "city": "Bogota",
        "contact_name": "",
        "title": "",
        "email": "comercial@innvector.com",
        "phone_whatsapp": "+57 321 2068925",
        "website": "https://innvector.com",
        "business": "LED screen + videowall + digital signage; interior/exterior pitches P2/P3/P6/P10; interactive touch displays; content management; high-impact advertising; Bogota Colombia; Instagram @innvector",
        "facebook": "",
        "instagram": "innvector",
        "linkedin": "innvector-sas",
    },
    {
        "no": 538,
        "country": "Colombia",
        "region": "Americas",
        "company_en": "LED Technology Medellin",
        "company_local": "Led Tecnology Medellin",
        "city": "Medellin",
        "contact_name": "",
        "title": "",
        "email": "gerencia@ledtecnologymedellin.com",
        "phone_whatsapp": "+57 302 3841183",
        "website": "https://ledtecnologymedellin.com",
        "business": "LED screen installation, maintenance and programming; bus route LED displays, pantallas LED, message boards; Medellin, Antioquia; Facebook profile.php?id=100091877637406",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 539,
        "country": "Colombia",
        "region": "Americas",
        "company_en": "Smartled Colombia",
        "company_local": "Smartled Colombia",
        "city": "Bogota",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+57 4557 9061",
        "website": "https://smartledcolombia.com",
        "business": "LED screen manufacturing and production; 10+ years; LED Wall, Outdoor LED, scoreboards, translucent LED, holograms; DOOH/retail/entertainment/corporate; authorized Techled concessionaire; 9 countries",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 540,
        "country": "Colombia",
        "region": "Americas",
        "company_en": "SISIC Colombia",
        "company_local": "SISIC",
        "city": "Bogota",
        "contact_name": "J. Cardenas",
        "title": "",
        "email": "j.cardenas@sisic.com.co",
        "phone_whatsapp": "+57 301 2249808",
        "website": "https://sisic.com.co",
        "business": "LED screen sales and installation; indoor + outdoor; preventive/corrective maintenance; design and installation consultation; Bogota Colombia",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 541,
        "country": "Colombia",
        "region": "Americas",
        "company_en": "Logistica y Montajes Cartagena",
        "company_local": "Logistica y Montajes Cartagena",
        "city": "Cartagena",
        "contact_name": "",
        "title": "",
        "email": "logisticaymontajes1@gmail.com",
        "phone_whatsapp": "+57 312 7590337",
        "website": "https://logisticaymontajescartagena.com",
        "business": "LED screen rental for events in Cartagena; also audio/staging; Caribbean coast Colombia; phone 316-0641",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
]

if __name__ == "__main__":
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from collections import Counter

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

    leads = load_all_leads()
    leads.extend(new_entries)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "LED Leads v23"

    headers = ["No","Country","Region","Company EN","Company Local","City",
               "Contact","Title","Email","Phone/WA","Website",
               "Business","Facebook","Instagram","LinkedIn"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="4472C4")
        cell.font = Font(bold=True, color="FFFFFF")

    for lead in leads:
        row = [
            lead.get("no",""), lead.get("country",""), lead.get("region",""),
            lead.get("company_en",""), lead.get("company_local",""), lead.get("city",""),
            lead.get("contact_name",""), lead.get("title",""), lead.get("email",""),
            lead.get("phone_whatsapp",""), lead.get("website",""),
            lead.get("business",""), lead.get("facebook",""),
            lead.get("instagram",""), lead.get("linkedin",""),
        ]
        ws.append(row)
        color = COUNTRY_COLORS.get(lead.get("country",""), "FFFFFF")
        for cell in ws[ws.max_row]:
            cell.fill = PatternFill("solid", fgColor=color)

    out = os.path.join(BASE, "LED_Display_Leads_v23.xlsx")
    wb.save(out)
    print(f"Saved: {out}")

    counter = Counter(l.get("country") for l in leads)
    print(f"Total: {len(leads)} leads")
    for c, n in sorted(counter.items(), key=lambda x: -x[1]):
        print(f"  {c}: {n}")
