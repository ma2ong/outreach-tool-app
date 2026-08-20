"""LED Display Leads — Americas + Korea — v11
Extends v10 (389 records) with 7 new entries = 396 total.
Sources: Instagram opencli + Jina website fetch
New: Korea +5, USA +1, (미디어파사드/디지털사이니지/부산/서울 방향)
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

# ── Load v5 / v6 / v7 / v8 / v9 / v10 new_entries ────────────────────────────
for _vname in ("v5", "v6", "v7", "v8", "v9", "v10"):
    _path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"generate_led_leads_{_vname}.py")
    _src  = open(_path, encoding="utf-8").read()
    _m    = re.search(r"^new_entries = (\[.+?^\])", _src, re.M | re.S)
    if _m:
        leads.extend(ast.literal_eval(_m.group(1)))

# ── New entries (390 – 396) ────────────────────────────────────────────────────
new_entries = [
    # ==================== Korea new (5) ====================
    {
        "no":390,"country":"Korea","region":"Asia",
        "company_en":"JD-ART Seoul","company_local":"제이디아트",
        "city":"Seoul",
        "contact_name":"","title":"",
        "email":"jd-art@naver.com","phone_whatsapp":"",
        "website":"",
        "business":"Immersive experience studio; 3D video, media art, media facade, interactive, projection mapping; brand space design; Instagram @jd.artseoul (2,625 followers, Verified)",
        "facebook":"","instagram":"jd.artseoul","linkedin":"",
    },
    {
        "no":391,"country":"Korea","region":"Asia",
        "company_en":"Monde DID","company_local":"몽드DID",
        "city":"Korea",
        "contact_name":"","title":"",
        "email":"synmww@naver.com","phone_whatsapp":"+82 10-2725-8201",
        "website":"",
        "business":"DID multi-vision + digital signage + cafe electronic menu boards; ceiling/wall-mounted menu boards; Instagram @monde_did (131 followers)",
        "facebook":"","instagram":"monde_did","linkedin":"",
    },
    {
        "no":392,"country":"Korea","region":"Asia",
        "company_en":"RF DID","company_local":"알에프",
        "city":"Korea",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"",
        "website":"",
        "business":"Digital signage + LED signboard; digital solutions for cafes, restaurants, medical offices; free consultation; 630 posts, Instagram @rf__did (288 followers)",
        "facebook":"","instagram":"rf__did","linkedin":"",
    },
    {
        "no":393,"country":"Korea","region":"Asia",
        "company_en":"AdMirror","company_local":"애드미러",
        "city":"Seoul",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"02-847-2123",
        "website":"",
        "business":"Space infrastructure specialist; digital signage, interior, signage design-to-install one-stop service; nationwide installation; Instagram @admirror_official (19 followers); phone confirmed from bio",
        "facebook":"","instagram":"admirror_official","linkedin":"",
    },
    {
        "no":394,"country":"Korea","region":"Asia",
        "company_en":"White Elephant LED","company_local":"화이트엘리펀트LED",
        "city":"Busan",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"1833-7989",
        "website":"https://www.bs-led.co.kr",
        "business":"LED signboard specialist; Busan-region LED signs (brand name KLED); 부산전광판; website bs-led.co.kr; Instagram @whiteelephant_led (752 followers)",
        "facebook":"","instagram":"whiteelephant_led","linkedin":"",
    },
    {
        "no":395,"country":"Korea","region":"Asia",
        "company_en":"Hanmac IT","company_local":"한맥아이티",
        "city":"Seoul (Seongdong-gu, SK Techno Building)",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"02-467-7447",
        "website":"",
        "business":"LED signboard + multimedia specialist; technology meets art concept; custom estimates; Seoul Seongdong-gu; Instagram @hanmacit (310 followers); phone confirmed from bio",
        "facebook":"","instagram":"hanmacit","linkedin":"",
    },
    # ==================== USA new (1) ====================
    {
        "no":396,"country":"USA","region":"Americas",
        "company_en":"FastInstall","company_local":"",
        "city":"Seattle, WA (Greater Seattle Area)",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"+1 425-766-3232",
        "website":"https://fastinstall.us",
        "business":"LED video wall installation + TV mounting; same-day installation; serves Seattle, Bellevue, Redmond, Kirkland, Issaquah, Lynnwood; Instagram @fastinstall.us (490 followers)",
        "facebook":"","instagram":"fastinstall.us","linkedin":"",
    },
]

leads.extend(new_entries)

# ── Country colour map ─────────────────────────────────────────────────────────
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

# ── Build Excel ────────────────────────────────────────────────────────────────
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "LED Leads - All Markets"

headers = [
    "No.", "Region", "Country", "City",
    "Company (English)", "Company (Local Language)",
    "Contact Person", "Title",
    "Email", "Phone / WhatsApp", "WhatsApp", "Kakao",
    "Website", "Main Business",
    "Facebook", "Instagram", "LinkedIn", "Notes/Action",
]

header_font  = Font(bold=True, color="FFFFFF", size=10)
header_fill  = PatternFill("solid", fgColor="2F5496")
header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
thin_border  = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"),  bottom=Side(style="thin"),
)

for col_idx, h in enumerate(headers, start=1):
    cell = ws.cell(row=1, column=col_idx, value=h)
    cell.font = header_font; cell.fill = header_fill
    cell.alignment = header_align; cell.border = thin_border

ws.row_dimensions[1].height = 30
ws.freeze_panes = "A2"
col_widths = [5, 10, 12, 18, 28, 24, 16, 14, 28, 18, 14, 14, 28, 36, 18, 18, 20, 22]
for i, w in enumerate(col_widths, start=1):
    ws.column_dimensions[get_column_letter(i)].width = w

for row_idx, lead in enumerate(leads, start=2):
    wa_flag = "✅" if "wa.me" in lead.get("business","").lower() or "whatsapp" in lead.get("business","").lower() else ""
    kk_flag = "✅" if "kakao" in lead.get("business","").lower() or "pf.kakao" in lead.get("business","").lower() else ""
    row = [
        lead.get("no",""), lead.get("region",""), lead.get("country",""), lead.get("city",""),
        lead.get("company_en",""), lead.get("company_local",""),
        lead.get("contact_name",""), lead.get("title",""),
        lead.get("email",""), lead.get("phone_whatsapp",""), wa_flag, kk_flag,
        lead.get("website",""), lead.get("business",""),
        lead.get("facebook",""), lead.get("instagram",""), lead.get("linkedin",""), "",
    ]
    fill_color = COUNTRY_COLORS.get(lead.get("country",""), "FFFFFF")
    row_fill   = PatternFill("solid", fgColor=fill_color)
    for col_idx, val in enumerate(row, start=1):
        cell = ws.cell(row=row_idx, column=col_idx, value=val)
        cell.fill = row_fill; cell.border = thin_border
        cell.alignment = Alignment(vertical="top", wrap_text=True)
        cell.font = Font(size=9)

ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}1"

# ── Sheet 2: Summary ───────────────────────────────────────────────────────────
ws2 = wb.create_sheet("Summary")
ws2.column_dimensions["A"].width = 16
ws2.column_dimensions["B"].width = 14
ws2["A1"] = "LED Display Leads — v11 Summary"
ws2["A1"].font = Font(bold=True, size=12, color="2F5496")
ws2.merge_cells("A1:B1")
ws2["A3"] = "Country"; ws2["B3"] = "Company Count"
for cell in ws2["3:3"]:
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="2F5496")
    cell.alignment = Alignment(horizontal="center")
    cell.border = thin_border

counts = Counter(lead["country"] for lead in leads)
countries_order = ["Korea","USA","Brazil","Canada","Chile","Argentina","Colombia","Peru","Mexico"]
r = 4
for country in countries_order:
    ws2.cell(row=r, column=1, value=country).border = thin_border
    c = ws2.cell(row=r, column=2, value=counts.get(country, 0))
    c.border = thin_border; c.alignment = Alignment(horizontal="center")
    r += 1
ws2.cell(row=r, column=1, value="TOTAL").font = Font(bold=True)
ws2.cell(row=r, column=1).border = thin_border
c2 = ws2.cell(row=r, column=2, value=len(leads))
c2.font = Font(bold=True); c2.border = thin_border
c2.alignment = Alignment(horizontal="center")
ws2["A"+str(r+2)] = f"Last updated: 2026-05-07  |  Total: {len(leads)} records"
ws2["A"+str(r+2)].font = Font(italic=True, color="666666")

# ── Sheet 3: 开发建议 ───────────────────────────────────────────────────────────
ws3 = wb.create_sheet("开发建议")
ws3.column_dimensions["A"].width = 14
ws3.column_dimensions["B"].width = 60
ws3["A1"] = "市场开发建议 — v11"
ws3["A1"].font = Font(bold=True, size=12, color="2F5496")
ws3.merge_cells("A1:B1")
advice = [
    ("Korea","白象LED(1833-7989, bs-led.co.kr)专注釜山市场。汉邦IT(02-467-7447)、애드미러(02-847-2123)都在首尔，可电话直联。Monde DID邮件synmww@naver.com。JD-ART jd-art@naver.com做媒体艺术，高端市场。"),
    ("USA","FastInstall(425-766-3232, fastinstall.us)做视频墙安装，Seattle覆盖。Eagle LED USA(info@eagleled.us)是分销商。重点推视频墙和数字标牌产品。"),
    ("Brazil","Azul Light(+55 44 3031-5492)是最大目标，4家分店+22K粉丝。BSL Light+GT Painel已有渠道。"),
    ("Canada","Inno-Leader有深圳背景，沟通顺畅。AVT/Illusion Universe体量较大，适合做经销商。"),
    ("Chile","CGS Chile(+56 2 2418-1225 / WA +56 9 9532-2717)、arriendopantallasledchile(+56 974753938)是本轮新增优质联系人。"),
    ("Argentina","Tucumán(+54 386-551-0502)、Si-Led Buenos Aires等3条新增。经济不稳，优先推性价比型号。"),
    ("Colombia","Visionled(Fredy Ruiz +57 310-492-3133, Medellín)、Alquiler Pantallas LED Colombia(Bogotá)是重点。用WhatsApp+西班牙语。"),
    ("Peru","Lima核心，LED Maker Peru(ledmaker.com.pe)已在库。alquiler_de_pantallas_led_peru(20年经验)需跟进联系方式。"),
    ("Mexico","Pantallas LED Monterrey新增。CDMX+Guadalajara+Monterrey三大市场。Fénix Evolution专注活动租赁。"),
]
ws3["A3"] = "国家"; ws3["B3"] = "开发策略"
for cell in ws3["3:3"]:
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="2F5496")
    cell.border = thin_border
for i, (country, tip) in enumerate(advice, start=4):
    ws3.cell(row=i, column=1, value=country).border = thin_border
    ws3.cell(row=i, column=2, value=tip).border = thin_border
    ws3.cell(row=i, column=2).alignment = Alignment(wrap_text=True)

# ── Save ───────────────────────────────────────────────────────────────────────
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LED_Display_Leads_v11.xlsx")
wb.save(out_path)
print(f"Saved: {out_path} ({len(leads)} records)")
