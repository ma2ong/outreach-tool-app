"""LED Display Leads — Americas + Korea — v19
Extends v18 (489 records) with 13 new entries = 502 total.
Sources: WebSearch + Jina reader (website contact pages)
New: USA +13 (event rental, dealers, AV integrators, digital signage — new cities)
Cities: Union City NJ, Langhorne PA (x2), Chicago IL, New York NY (x3),
        Bay Shore NY, Baltimore MD, Miami FL, Boston MA, Oklahoma City OK,
        National multi-city (x2)
"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from collections import Counter
import ast, re, os

# ── Load v4 leads ──────────────────────────────────────────────────────────────
_v4_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generate_led_leads_v4.py")
_v4_src  = open(_v4_path, encoding="utf-8").read()
leads = ast.literal_eval(re.search(r"^leads = (\[.+?^\])", _v4_src, re.M | re.S).group(1))

# ── Load v5 – v18 new_entries ─────────────────────────────────────────────────
for _vname in ("v5", "v6", "v7", "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15", "v16", "v17", "v18"):
    _path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"generate_led_leads_{_vname}.py")
    _src  = open(_path, encoding="utf-8").read()
    _m    = re.search(r"^new_entries = (\[.+?^\])", _src, re.M | re.S)
    if _m:
        leads.extend(ast.literal_eval(_m.group(1)))

# ── New entries (490 – 502) ────────────────────────────────────────────────────
new_entries = [
    # ==================== USA new (13) ====================
    {
        "no":490,"country":"USA","region":"Americas",
        "company_en":"LED Wall Systems","company_local":"",
        "city":"Union City, NJ",
        "contact_name":"","title":"",
        "email":"sales@ledwallsystems.com","phone_whatsapp":"(646) 229-2995",
        "website":"ledwallsystems.com",
        "business":"LED wall rental, sales, and permanent installation serving NYC metro and nationwide; services: events, trade shows, church, XR/virtual production, digital signage; clients include NY Marathon, Tony Awards, JVC Jazz Festival; email confirmed from website",
        "facebook":"","instagram":"","linkedin":"",
    },
    {
        "no":491,"country":"USA","region":"Americas",
        "company_en":"Nationwide Event Rentals","company_local":"",
        "city":"Langhorne, PA",
        "contact_name":"","title":"",
        "email":"Info@NationwideEventRentals.com","phone_whatsapp":"(800) 653-5940",
        "website":"nationwideeventrentals.com",
        "business":"Full-service event production company renting LED video walls nationwide; clients include Pfizer, NFL, DNC, Chainsmokers, Americas Got Talent; HQ Langhorne PA with nationwide reach; email confirmed from website",
        "facebook":"","instagram":"","linkedin":"",
    },
    {
        "no":492,"country":"USA","region":"Americas",
        "company_en":"Altitude LED","company_local":"",
        "city":"Chicago, IL",
        "contact_name":"","title":"",
        "email":"solutions@altitudeled.com","phone_whatsapp":"(872) 877-3480",
        "website":"altitudeled.com",
        "business":"LED screen dealer and installer specializing in church/worship market; sells and installs permanent LED walls for small-to-medium churches across USA; product lines: Air, Cloud, Apex series; Instagram @altitudeled; email confirmed from website",
        "facebook":"","instagram":"altitudeled","linkedin":"",
    },
    {
        "no":493,"country":"USA","region":"Americas",
        "company_en":"AVR Expos","company_local":"",
        "city":"New York, NY",
        "contact_name":"","title":"",
        "email":"info@avrexpos.com","phone_whatsapp":"(800) 693-6668",
        "website":"avrexpos.com",
        "business":"AV rental company offering LED video wall rentals in NYC, Philadelphia, Boston, Miami and nationwide for trade shows, conferences, and events; brands: Absen, AOTO, INFiLED; email confirmed from website",
        "facebook":"","instagram":"","linkedin":"",
    },
    {
        "no":494,"country":"USA","region":"Americas",
        "company_en":"New Image LED Video Walls","company_local":"",
        "city":"Bay Shore, NY",
        "contact_name":"","title":"",
        "email":"info@newimageeventproductions.com","phone_whatsapp":"(646) 287-5002",
        "website":"newimageledvideowalls.com",
        "business":"Dedicated LED video wall rental and sales company serving NYC, Philadelphia, Boston and nationwide; specializes in corporate events, concerts, trade shows, and permanent installations; Instagram @nie_nyc; email confirmed from website",
        "facebook":"","instagram":"nie_nyc","linkedin":"",
    },
    {
        "no":495,"country":"USA","region":"Americas",
        "company_en":"ATD Audio Visual","company_local":"",
        "city":"New York, NY",
        "contact_name":"","title":"",
        "email":"info@atd-av.com","phone_whatsapp":"(866) 738-3580",
        "website":"atd-av.com",
        "business":"Full-service event production company specializing in LED video wall rental in NYC and LA; 20+ years experience; handles concerts, corporate events, fashion shows, sports; Instagram @atd.av; email confirmed from website",
        "facebook":"","instagram":"atd.av","linkedin":"",
    },
    {
        "no":496,"country":"USA","region":"Americas",
        "company_en":"Mid Atlantic Event Group","company_local":"",
        "city":"Langhorne, PA",
        "contact_name":"","title":"",
        "email":"info@maegav.com","phone_whatsapp":"(215) 791-2776",
        "website":"midatlanticeventgroup.com",
        "business":"AV production company serving Philadelphia and PA region; LED video walls, audio, and event production for corporate clients; Instagram @midatlanticeventgroup; email confirmed from website",
        "facebook":"MidAtlanticEventGroup","instagram":"midatlanticeventgroup","linkedin":"",
    },
    {
        "no":497,"country":"USA","region":"Americas",
        "company_en":"Gable Company","company_local":"",
        "city":"Baltimore, MD",
        "contact_name":"","title":"",
        "email":"solutions@gablecompany.com","phone_whatsapp":"(800) 854-0568",
        "website":"gablecompany.com",
        "business":"Visual communications company offering digital signage and LED display integration in Baltimore MD and nationally; serves stadiums, convention centers, retail, churches, casinos, healthcare; email confirmed from website",
        "facebook":"","instagram":"","linkedin":"",
    },
    {
        "no":498,"country":"USA","region":"Americas",
        "company_en":"All Pro Audio Visual","company_local":"",
        "city":"National (multi-city, USA)",
        "contact_name":"","title":"",
        "email":"Info@allproaudiovisual.com","phone_whatsapp":"(888) 613-3335",
        "website":"allproaudiovisual.com",
        "business":"National AV rental company with LED video wall rentals across multiple US cities including Kansas City MO, Oklahoma City OK, Panama City FL, Salt Lake City UT; event production and installation; Instagram @allproaudiovisual; email confirmed from website",
        "facebook":"","instagram":"allproaudiovisual","linkedin":"",
    },
    {
        "no":499,"country":"USA","region":"Americas",
        "company_en":"Integrated AV Co","company_local":"",
        "city":"Oklahoma City, OK",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"(405) 594-7940",
        "website":"integratedavco.com",
        "business":"AV integrator serving Oklahoma and New Mexico; installs commercial video walls and AV systems for churches, commercial spaces, and corporate clients; phone confirmed from website",
        "facebook":"","instagram":"","linkedin":"",
    },
    {
        "no":500,"country":"USA","region":"Americas",
        "company_en":"Nationwide Video","company_local":"",
        "city":"National (multi-city, USA)",
        "contact_name":"","title":"",
        "email":"info@subrent.com","phone_whatsapp":"(800) 935-2323",
        "website":"nationwidevideo.com",
        "business":"National AV rental company with LED video wall crews in Detroit MI, Orlando FL, Las Vegas NV, Atlanta GA, New Jersey, Dallas TX, Nashville TN, San Diego CA; event production; email confirmed from website",
        "facebook":"","instagram":"","linkedin":"",
    },
    {
        "no":501,"country":"USA","region":"Americas",
        "company_en":"Boston Audio Rentals","company_local":"",
        "city":"Boston, MA",
        "contact_name":"","title":"",
        "email":"info@BostonAudioRentals.com","phone_whatsapp":"(617) 888-5360",
        "website":"bostonaudiorentals.com",
        "business":"Boston-based AV rental company offering high-resolution LED wall solutions for live events, corporate productions, and special occasions in Massachusetts; email confirmed from website",
        "facebook":"","instagram":"","linkedin":"",
    },
    {
        "no":502,"country":"USA","region":"Americas",
        "company_en":"Miami Sound Rental","company_local":"",
        "city":"Miami, FL",
        "contact_name":"","title":"",
        "email":"info@miamisoundrental.com","phone_whatsapp":"(305) 974-4411",
        "website":"miamisoundrental.com",
        "business":"Miami-based event rental company offering LED video wall rental packages for concerts, conferences, sporting events, fashion shows, and houses of worship in South Florida; email confirmed from website",
        "facebook":"","instagram":"","linkedin":"",
    },
]

leads.extend(new_entries)

# ── Sanity check ──────────────────────────────────────────────────────────────
assert len(leads) == 502, f"Expected 502 leads, got {len(leads)}"
nos = [l["no"] for l in leads]
assert len(nos) == len(set(nos)), "Duplicate no found!"

# ── Country color map ─────────────────────────────────────────────────────────
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

# ── Build workbook ────────────────────────────────────────────────────────────
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "LED Leads"

headers = [
    "No","Country","Region","Company (EN)","Company (Local)",
    "City","Contact","Title","Email","Phone/WhatsApp",
    "Website","Business Description","Facebook","Instagram","LinkedIn"
]

header_fill = PatternFill("solid", fgColor="2E75B6")
header_font = Font(bold=True, color="FFFFFF", size=11)
thin = Side(style="thin", color="CCCCCC")
border = Border(left=thin, right=thin, top=thin, bottom=thin)

for col, h in enumerate(headers, 1):
    cell = ws.cell(row=1, column=col, value=h)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = border

ws.row_dimensions[1].height = 30

field_keys = [
    "no","country","region","company_en","company_local",
    "city","contact_name","title","email","phone_whatsapp",
    "website","business","facebook","instagram","linkedin"
]

for row_idx, lead in enumerate(leads, 2):
    color = COUNTRY_COLORS.get(lead.get("country",""), "FFFFFF")
    row_fill = PatternFill("solid", fgColor=color)
    for col_idx, key in enumerate(field_keys, 1):
        val = lead.get(key, "")
        cell = ws.cell(row=row_idx, column=col_idx, value=val)
        cell.fill = row_fill
        cell.alignment = Alignment(vertical="center", wrap_text=(col_idx == 12))
        cell.border = border

col_widths = [6,12,10,28,20,18,16,14,30,20,28,55,20,20,20]
for i, w in enumerate(col_widths, 1):
    ws.column_dimensions[get_column_letter(i)].width = w

ws.freeze_panes = "A2"
ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}1"

# ── Summary sheet ─────────────────────────────────────────────────────────────
ws2 = wb.create_sheet("Summary")
country_counts = Counter(l["country"] for l in leads)
ws2.append(["Country", "Count"])
for country, count in sorted(country_counts.items(), key=lambda x: -x[1]):
    ws2.append([country, count])
ws2.append(["TOTAL", len(leads)])

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LED_Display_Leads_v19.xlsx")
wb.save(out_path)
print(f"Saved: {out_path}")
print(f"Total leads: {len(leads)}")
for country, count in sorted(country_counts.items(), key=lambda x: -x[1]):
    print(f"  {country}: {count}")
