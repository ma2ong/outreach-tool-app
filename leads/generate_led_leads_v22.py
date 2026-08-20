"""
LED Display Leads v22 — Colombia cities + Peru
5 new Colombia entries (Barranquilla, Santa Marta, Bucaramanga, Bogota x2)
1 new Peru entry (Lima)
nos 531-536
"""
import ast, re, os, sys
sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(__file__)

def load_all_leads():
    _v4_src = open(os.path.join(BASE, "generate_led_leads_v4.py"), encoding="utf-8").read()
    leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", _v4_src, re.M | re.S).group(1))
    for _vname in [f"v{i}" for i in range(5, 22)]:
        _path = os.path.join(BASE, f"generate_led_leads_{_vname}.py")
        if not os.path.exists(_path): continue
        _src = open(_path, encoding="utf-8").read()
        _m = re.search(r"^new_entries = (\[.+?^\])", _src, re.M | re.S)
        if _m: leads.extend(ast.literal_eval(_m.group(1)))
    return leads

new_entries = [
    {
        "no": 531,
        "country": "Colombia",
        "region": "Americas",
        "company_en": "DesignLab LED Barranquilla",
        "company_local": "DesignLab",
        "city": "Barranquilla",
        "contact_name": "",
        "title": "",
        "email": "info@schallerdesignlab.com",
        "phone_whatsapp": "+57 318 3627856",
        "website": "https://pantallaled.co",
        "business": "LED screen design and installation; indoor/outdoor, scoreboards, video walls, retail, events, sports, corporate; technical consulting + content management; Barranquilla, Colombia",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 532,
        "country": "Colombia",
        "region": "Americas",
        "company_en": "Rental Eventos Colombia",
        "company_local": "Rental Eventos",
        "city": "Santa Marta",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+57 300 8374285",
        "website": "https://rentapantallas.com.co",
        "business": "LED screen and AV equipment rental for corporate events; covers Santa Marta, Barranquilla, Cartagena (Caribbean coast); clients include BBVA, SUNEDU; Instagram @rentaleventoscol",
        "facebook": "",
        "instagram": "rentaleventoscol",
        "linkedin": "",
    },
    {
        "no": 533,
        "country": "Colombia",
        "region": "Americas",
        "company_en": "Visual Pantallas LED Bucaramanga",
        "company_local": "Visual Pantallas Led S.A.S.",
        "city": "Bucaramanga",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+57 315 7989884",
        "website": "",
        "business": "LED screen sales and AV equipment; Carrera 22 33-38 Centro, Bucaramanga, Santander; NIT 9013552213; SAS registered",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 534,
        "country": "Colombia",
        "region": "Americas",
        "company_en": "Altema LED Rental Bogota",
        "company_local": "Altema Alquiler Pantallas LED",
        "city": "Bogota",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "",
        "website": "",
        "business": "Large-format LED screen rental for terraces, patios, plazas, event rooms; venue partner of Macrodiscoteca Escarlata, Bogota; Instagram @altema_alquiler_pantallas (189 followers, 350 posts)",
        "facebook": "",
        "instagram": "altema_alquiler_pantallas",
        "linkedin": "",
    },
    {
        "no": 535,
        "country": "Colombia",
        "region": "Americas",
        "company_en": "Vision Prime Colombia",
        "company_local": "Vision Prime",
        "city": "Bogota",
        "contact_name": "",
        "title": "",
        "email": "",
        "phone_whatsapp": "+57 310 2595817",
        "website": "https://visionprimecolombia.com",
        "business": "Audiovisual equipment rental and sales; LED screens (indoor/outdoor), video walls, projectors, audio; Bogota D.C.; phone +57 9323545; website visionprimecolombia.com",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
    },
    {
        "no": 536,
        "country": "Peru",
        "region": "Americas",
        "company_en": "RedMediaLive Peru",
        "company_local": "REDMEDIALIVE",
        "city": "Lima",
        "contact_name": "",
        "title": "",
        "email": "servicios@redmedialive.com",
        "phone_whatsapp": "+51 992 429776",
        "website": "https://redmedialive.com",
        "business": "LED screen rental + live streaming for corporate events; indoor/outdoor high-format LED; clients: BBVA, SUNEDU, EsSalud, MinEdu; Lima, Peru; Instagram @redmedialive (180 followers)",
        "facebook": "",
        "instagram": "redmedialive",
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
    ws.title = "LED Leads v22"

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

    out = os.path.join(BASE, "LED_Display_Leads_v22.xlsx")
    wb.save(out)
    print(f"Saved: {out}")

    counter = Counter(l.get("country") for l in leads)
    print(f"Total: {len(leads)} leads")
    for c, n in sorted(counter.items(), key=lambda x: -x[1]):
        print(f"  {c}: {n}")
