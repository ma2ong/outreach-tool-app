"""LED Display Leads — Americas + Korea — v6
Extends v5 (300 records) with 31 new entries = 331 total.
Sources: Instagram/Facebook opencli search + WebSearch + Naver
New: Korea +11, USA +3, Mexico +3, Brazil +1, Colombia +2,
     Argentina +1, Chile +5, Peru +3, Canada +2
Validation notes added for WhatsApp/KakaoTalk confirmed contacts.
"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from collections import Counter
import ast, re, os

# ── Load v4 leads ──────────────────────────────────────────────────────────────
_v4_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generate_led_leads_v4.py")
_v4_src  = open(_v4_path, encoding="utf-8").read()
_leads_src = re.search(r"^leads = (\[.+?^\])", _v4_src, re.M | re.S).group(1)
leads = ast.literal_eval(_leads_src)

# ── Load v5 new_entries ────────────────────────────────────────────────────────
_v5_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generate_led_leads_v5.py")
_v5_src  = open(_v5_path, encoding="utf-8").read()
_v5_new_src = re.search(r"^new_entries = (\[.+?^\])", _v5_src, re.M | re.S).group(1)
leads.extend(ast.literal_eval(_v5_new_src))

# ── New entries (301 – 331) ────────────────────────────────────────────────────
new_entries = [
    # ==================== KOREA new (11) ====================
    {
        "no":301,"country":"Korea","region":"Asia",
        "company_en":"Vision Korea","company_local":"(주)비젼코리아",
        "city":"Gimpo, Gyeonggi-do",
        "contact_name":"","title":"",
        "email":"vk3131@naver.com","phone_whatsapp":"+82 31-991-3131",
        "website":"http://vk3131.co.kr",
        "business":"LED display manufacturer; full-color panels, outdoor advertising, custom signage",
        "facebook":"","instagram":"led_vk3133","linkedin":"",
    },
    {
        "no":302,"country":"Korea","region":"Asia",
        "company_en":"Lostech","company_local":"(주)로스텍",
        "city":"Cheongju, North Chungcheong",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"+82 43-232-5770",
        "website":"https://lostech.kr",
        "business":"LED display manufacturer since 2009; LED 전광판, electronic scoreboards, outdoor advertising panels",
        "facebook":"","instagram":"led.lostech","linkedin":"",
    },
    {
        "no":303,"country":"Korea","region":"Asia",
        "company_en":"Dglow (D.Glow Official)","company_local":"디글로우",
        "city":"Seoul",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"",
        "website":"",
        "business":"Premium LED solutions; signature 3-sided cube LED, building exterior LED, large outdoor installations",
        "facebook":"","instagram":"dglow_led","linkedin":"",
    },
    {
        "no":304,"country":"Korea","region":"Asia",
        "company_en":"Calla Media","company_local":"칼라미디어",
        "city":"Seoul",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"+82 2-540-1737",
        "website":"https://callamedia.kr",
        "business":"LED display rental & sales, AV equipment distribution; KakaoTalk: pf.kakao.com/_VGJqM",
        "facebook":"callamedia","instagram":"","linkedin":"",
    },
    {
        "no":305,"country":"Korea","region":"Asia",
        "company_en":"Sound Korea","company_local":"사운드코리아",
        "city":"Seoul",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"",
        "website":"",
        "business":"음향/영상/LED전광판/CCTV 전문 시공 (Sound, video, LED signage, CCTV installation)",
        "facebook":"soundkorea1","instagram":"","linkedin":"",
    },
    {
        "no":306,"country":"Korea","region":"Asia",
        "company_en":"Hanmaek IT","company_local":"한맥아이티",
        "city":"Seoul, Seongdong-gu",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"+82 507-1315-8411",
        "website":"",
        "business":"LED signage installation & construction",
        "facebook":"","instagram":"","linkedin":"",
    },
    {
        "no":307,"country":"Korea","region":"Asia",
        "company_en":"CMG Korea","company_local":"씨엠지",
        "city":"Seoul, Geumcheon-gu",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"+82 2-3281-2080",
        "website":"",
        "business":"LED signage & telecommunications construction",
        "facebook":"","instagram":"","linkedin":"",
    },
    {
        "no":308,"country":"Korea","region":"Asia",
        "company_en":"Uri ISL","company_local":"우리아이에스엘",
        "city":"Goyang, Ilsandong-gu",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"+82 507-1438-5909",
        "website":"",
        "business":"LED 전광판 전문 (LED display specialist)",
        "facebook":"","instagram":"","linkedin":"",
    },
    {
        "no":309,"country":"Korea","region":"Asia",
        "company_en":"Geumgang S&G","company_local":"금강에스앤지",
        "city":"Seoul, Geumcheon-gu",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"+82 507-1494-3458",
        "website":"",
        "business":"LED signage company",
        "facebook":"","instagram":"","linkedin":"",
    },
    {
        "no":310,"country":"Korea","region":"Asia",
        "company_en":"Bitna Electronics","company_local":"빛나전자",
        "city":"Seongnam, Jungwon-gu",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"+82 31-735-1990",
        "website":"",
        "business":"LED electronic display company",
        "facebook":"","instagram":"","linkedin":"",
    },
    {
        "no":311,"country":"Korea","region":"Asia",
        "company_en":"JuBit LED","company_local":"주빛LED",
        "city":"Korea",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"",
        "website":"https://juvitled.co.kr",
        "business":"LED display manufacturing and delivery",
        "facebook":"","instagram":"","linkedin":"",
    },
    # ==================== USA new (3) ====================
    {
        "no":312,"country":"USA","region":"North America",
        "company_en":"SV Solutions","company_local":"SV Solutions USA",
        "city":"Houston, TX",
        "contact_name":"","title":"",
        "email":"info@svsolutionsusa.com","phone_whatsapp":"+1 866-389-8595",
        "website":"https://svsolutionsusa.com",
        "business":"LED video walls & screens; churches, events, outdoor advertising; nationwide",
        "facebook":"","instagram":"svsolutions.usa","linkedin":"",
    },
    {
        "no":313,"country":"USA","region":"North America",
        "company_en":"XcolorLED USA","company_local":"XColorLed USA",
        "city":"Lynnwood, WA (Seattle area)",
        "contact_name":"","title":"",
        "email":"info@xcolorledusa.com","phone_whatsapp":"+1 425-550-6976",
        "website":"https://xcolorledusa.com",
        "business":"Premium LED video walls & displays; 3-year warranty; fast US shipping; financing available",
        "facebook":"","instagram":"xcolorledusa","linkedin":"",
    },
    {
        "no":314,"country":"USA","region":"North America",
        "company_en":"Long Run LED USA","company_local":"Long Run LED",
        "city":"USA",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"",
        "website":"",
        "business":"LED video wall solutions",
        "facebook":"","instagram":"longrunled_usa","linkedin":"",
    },
    # ==================== MEXICO new (3) ====================
    {
        "no":315,"country":"Mexico","region":"North America",
        "company_en":"Fénix-Evolution LED","company_local":"Producciones Fénix-Evolution",
        "city":"León, Guanajuato",
        "contact_name":"","title":"",
        "email":"ventas@fenix-evolution.com.mx","phone_whatsapp":"(477) 125-5013 WA León / (462) 269-9223 WA Irapuato",
        "website":"https://fenix-evolution.com.mx",
        "business":"LED screen rental & sale for events; coverage León, Irapuato, CDMX, Guadalajara, Monterrey, Cancún",
        "facebook":"produccionesfenixevolution","instagram":"fenixevolution_led","linkedin":"",
    },
    {
        "no":316,"country":"Mexico","region":"North America",
        "company_en":"Abk Lighting México","company_local":"Abk Lighting México",
        "city":"Mexico",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"",
        "website":"",
        "business":"LED screen rental & sale; #1 en México claim; Mon-Fri 8-6pm",
        "facebook":"","instagram":"abklightingoficial","linkedin":"",
    },
    {
        "no":317,"country":"Mexico","region":"North America",
        "company_en":"Light Tech México","company_local":"Light Tech México",
        "city":"Mexico",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"",
        "website":"",
        "business":"LED display solutions",
        "facebook":"","instagram":"lighttechmexico","linkedin":"",
    },
    # ==================== BRAZIL new (1) ====================
    {
        "no":318,"country":"Brazil","region":"South America",
        "company_en":"Chronos LED","company_local":"Chronos LED",
        "city":"Brazil",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"",
        "website":"https://chronosled.com.br",
        "business":"LED panels outdoor & indoor; direct importer, prices up to 40% lower; 1,516 Instagram followers",
        "facebook":"","instagram":"chronosledbr","linkedin":"",
    },
    # ==================== COLOMBIA new (2) ====================
    {
        "no":319,"country":"Colombia","region":"South America",
        "company_en":"CIBER CORP Colombia","company_local":"Ciber Light Col",
        "city":"Bogotá",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"+57 314 4130393",
        "website":"https://ciberlightcol.com",
        "business":"LED screens 20+ years; indoor/outdoor, lighting; WhatsApp confirmed on website",
        "facebook":"","instagram":"ciber_colombia_","linkedin":"",
    },
    {
        "no":320,"country":"Colombia","region":"South America",
        "company_en":"Pantallas Colombia (LED)","company_local":"Pantallas Colombia",
        "city":"Colombia",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"",
        "website":"",
        "business":"LED display company Colombia",
        "facebook":"","instagram":"pantallasledencolombia","linkedin":"",
    },
    # ==================== ARGENTINA new (1) ====================
    {
        "no":321,"country":"Argentina","region":"South America",
        "company_en":"Exodo LED","company_local":"EXODO LED",
        "city":"Buenos Aires (CABA)",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"",
        "website":"https://exodo-led.com.ar",
        "business":"LED screens indoor/outdoor; installment financing up to 24 months; Buenos Aires",
        "facebook":"exodoled","instagram":"exodoled","linkedin":"",
    },
    # ==================== CHILE new (5) ====================
    {
        "no":322,"country":"Chile","region":"South America",
        "company_en":"CGS Chile","company_local":"CGS Chile Ltda.",
        "city":"Providencia, Santiago",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"+56 2 2418-1225",
        "website":"https://cgschile.cl",
        "business":"Audiovisual solutions; LED screen sale & rental for concerts, seminars, congresses",
        "facebook":"CGSincChile","instagram":"cgschile.pantallasled.hd","linkedin":"",
    },
    {
        "no":323,"country":"Chile","region":"South America",
        "company_en":"FixLed Chile","company_local":"FixLed Chile",
        "city":"Chile",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"",
        "website":"",
        "business":"LED screen repair & technical service (verified Instagram)",
        "facebook":"","instagram":"fixledchile","linkedin":"",
    },
    {
        "no":324,"country":"Chile","region":"South America",
        "company_en":"Proyecto LED Chile","company_local":"Proyecto Led",
        "city":"Chile",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"",
        "website":"",
        "business":"LED screen rental for events",
        "facebook":"","instagram":"arriendopantallasledchile","linkedin":"",
    },
    {
        "no":325,"country":"Chile","region":"South America",
        "company_en":"Pantallas LED y Maquinas Chile","company_local":"Pantallas Led y Maquinas Chile",
        "city":"Chile",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"",
        "website":"",
        "business":"Giant LED screens & industrial machinery",
        "facebook":"","instagram":"pantallasledymaquinas","linkedin":"",
    },
    {
        "no":326,"country":"Chile","region":"South America",
        "company_en":"Marcatek Chile","company_local":"Marcatek Chile",
        "city":"Chile",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"",
        "website":"",
        "business":"LED screen and banner display sales",
        "facebook":"","instagram":"marcatek_chile","linkedin":"",
    },
    # ==================== PERU new (3) ====================
    {
        "no":327,"country":"Peru","region":"South America",
        "company_en":"LED Perú","company_local":"LED Perú",
        "city":"Peru",
        "contact_name":"","title":"",
        "email":"ventas@ledperu.com.pe","phone_whatsapp":"+51 964 550 548",
        "website":"https://ledperu.com.pe",
        "business":"LED screens, innovative visual solutions; WhatsApp confirmed: wa.me/51964550548",
        "facebook":"","instagram":"","linkedin":"",
    },
    {
        "no":328,"country":"Peru","region":"South America",
        "company_en":"Alquiler Pantallas LED Peru","company_local":"Alquiler Pantallas Led Peru",
        "city":"Lima",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"",
        "website":"",
        "business":"LED screen rental for events; technical team Lima",
        "facebook":"","instagram":"alquiler_de_pantallas_led_peru","linkedin":"",
    },
    {
        "no":329,"country":"Peru","region":"South America",
        "company_en":"LED Móvil Peru","company_local":"LED Móvil Perú",
        "city":"Peru",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"",
        "website":"",
        "business":"Ecological mobile LED advertising screens; easy programming, energy saving",
        "facebook":"","instagram":"pantallasledmovilperu","linkedin":"",
    },
    # ==================== CANADA new (2) ====================
    {
        "no":330,"country":"Canada","region":"North America",
        "company_en":"National Neon Signs","company_local":"National Neon Displays Ltd.",
        "city":"Calgary, AB",
        "contact_name":"","title":"",
        "email":"info@nationalneon.com","phone_whatsapp":"+1 403-814-0999",
        "website":"https://nationalneonsigns.ca",
        "business":"Premier Canadian sign company; custom LED displays, nationwide installation; Toronto & Vancouver",
        "facebook":"","instagram":"","linkedin":"",
    },
    {
        "no":331,"country":"Canada","region":"North America",
        "company_en":"VIEWitMEDIA","company_local":"VIEWitMEDIA",
        "city":"Richmond Hill, ON",
        "contact_name":"","title":"",
        "email":"","phone_whatsapp":"+1 833-934-1724",
        "website":"https://viewitmedia.ca",
        "business":"Digital signage solutions company; Toronto & Canada wide",
        "facebook":"","instagram":"","linkedin":"",
    },
]

leads.extend(new_entries)

# Renumber sequentially
for i, lead in enumerate(leads, 1):
    lead["no"] = i

# ─── Workbook ─────────────────────────────────────────────────────────────────
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "LED Leads - All Markets"

COLOR_HEADER_BG   = "1F4E79"
COLOR_HEADER_FONT = "FFFFFF"

COUNTRY_COLORS = {
    "Brazil":    "D9EAD3",
    "Colombia":  "FCE5CD",
    "Chile":     "D0E4F5",
    "Peru":      "FFF2CC",
    "Argentina": "EAD1DC",
    "USA":       "CFE2F3",
    "Canada":    "E6D0DE",
    "Mexico":    "D9D2E9",
    "Korea":     "F4CCCC",
}

headers = [
    "No.", "Region", "Country", "City",
    "Company (English)", "Company (Local Language)",
    "Contact Person", "Title",
    "Email", "Phone / WhatsApp / Kakao",
    "Website", "Main Business",
    "Facebook", "Instagram", "LinkedIn",
    "Notes / Action",
]

thin   = Side(style="thin", color="CCCCCC")
border = Border(left=thin, right=thin, top=thin, bottom=thin)
hfill  = PatternFill("solid", fgColor=COLOR_HEADER_BG)
hfont  = Font(bold=True, color=COLOR_HEADER_FONT, size=11)
halign = Alignment(horizontal="center", vertical="center", wrap_text=True)

for ci, h in enumerate(headers, 1):
    cell = ws.cell(row=1, column=ci, value=h)
    cell.fill = hfill; cell.font = hfont
    cell.alignment = halign; cell.border = border
ws.row_dimensions[1].height = 36

for ri, lead in enumerate(leads, 2):
    row_data = [
        lead["no"], lead["region"], lead["country"], lead["city"],
        lead["company_en"], lead["company_local"],
        lead["contact_name"], lead["title"],
        lead["email"], lead["phone_whatsapp"],
        lead["website"], lead["business"],
        lead["facebook"], lead["instagram"], lead["linkedin"],
        "",
    ]
    rfill = PatternFill("solid", fgColor=COUNTRY_COLORS.get(lead["country"], "FFFFFF"))
    for ci, val in enumerate(row_data, 1):
        cell = ws.cell(row=ri, column=ci, value=val)
        cell.fill = rfill
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        cell.border = border
    ws.row_dimensions[ri].height = 26

col_widths = [5, 14, 12, 25, 28, 28, 18, 14, 32, 32, 34, 50, 32, 30, 42, 20]
for ci, w in enumerate(col_widths, 1):
    ws.column_dimensions[get_column_letter(ci)].width = w
ws.freeze_panes = "A2"

# ─── Summary sheet ────────────────────────────────────────────────────────────
ws2 = wb.create_sheet("Summary")
ws2["A1"] = "LED Display Leads — Americas + Korea  (v6)"
ws2["A1"].font = Font(bold=True, size=14, color=COLOR_HEADER_BG)

ws2["A3"] = "Region"; ws2["B3"] = "Country"; ws2["C3"] = "# Companies"
for cell in ws2["A3:C3"][0]:
    cell.fill = hfill; cell.font = hfont
    cell.alignment = Alignment(horizontal="center")

country_count = Counter(lead["country"] for lead in leads)

summary = [
    ("South America", "Brazil",    country_count["Brazil"]),
    ("South America", "Colombia",  country_count["Colombia"]),
    ("South America", "Chile",     country_count["Chile"]),
    ("South America", "Peru",      country_count["Peru"]),
    ("South America", "Argentina", country_count["Argentina"]),
    ("North America", "USA",       country_count["USA"]),
    ("North America", "Canada",    country_count["Canada"]),
    ("North America", "Mexico",    country_count["Mexico"]),
    ("Asia",          "Korea",     country_count["Korea"]),
]
for i, (region, country, cnt) in enumerate(summary, 4):
    ws2.cell(row=i, column=1, value=region)
    ws2.cell(row=i, column=2, value=country)
    ws2.cell(row=i, column=3, value=cnt)
    f = PatternFill("solid", fgColor=COUNTRY_COLORS.get(country, "FFFFFF"))
    for c in range(1, 4):
        ws2.cell(row=i, column=c).fill = f

total_row = len(summary) + 4
ws2.cell(row=total_row, column=1, value="TOTAL")
ws2.cell(row=total_row, column=3, value=len(leads))
for c in range(1, 4):
    ws2.cell(row=total_row, column=c).font = Font(bold=True)
for col in ["A","B","C"]:
    ws2.column_dimensions[col].width = 20

# ─── 开发建议 sheet ────────────────────────────────────────────────────────────
ws3 = wb.create_sheet("开发建议")
ws3["A1"] = "B2B开发建议 — LED显示屏海外客户"
ws3["A1"].font = Font(bold=True, size=13, color=COLOR_HEADER_BG)

tips = [
    ("巴西 (Brazil)",
     "首选WhatsApp联系；提及Absen/Leyard已在巴西有分支，证明市场成熟度。"
     "针对Crialed/LedWave等租赁公司，主推P3.9/P4.8租赁屏。"),
    ("哥伦比亚 (Colombia)",
     "MachineTronics/CIBER CORP等WhatsApp已验证可直接发消息。"
     "Machinetronics WhatsApp: +57 318 340 0796；CIBER WhatsApp: +57 314 4130393。"),
    ("智利 (Chile)",
     "Santiago集中大量系统集成商；CGS Chile体量较大，可优先联系。"
     "提供西班牙语技术支持文档有助于建立信任。"),
    ("美国 (USA)",
     "SV Solutions(Houston)和XcolorLED USA(Seattle)均有官网和邮件，可冷邮件开发。"
     "SNA Displays/PixelFLEX做高端项目；LED Nation USA是LatAm中转站。"),
    ("加拿大 (Canada)",
     "National Neon Signs(Calgary)有邮件info@nationalneon.com，直接联系。"
     "BC省(温哥华)华人商圈活跃，ClearLED/Adtronics响应快。"),
    ("韩国 (Korea)",
     "비젼코리아/로스텍/칼라미디어均有直接电话，可电话+邮件双渠道。"
     "칼라미디어有KakaoTalk: pf.kakao.com/_VGJqM（已验证）。"
     "韩国客户重视技术规格与认证(KC/CE)，首封邮件附产品规格书。"),
    ("墨西哥 (Mexico)",
     "Fénix-Evolution LEDWhatsApp已验证：(477) 125-5013。"
     "Monterrey(iLED)和León(Fénix-Evolution)是主要市场。"
     "活动/租赁市场大，Showco/Luft Screen是重点目标。"),
    ("秘鲁 (Peru)",
     "LED Perú WhatsApp已验证: wa.me/51964550548。"
     "Lima集中绝大部分需求；EXCTECLED是当地最知名分销商。"
     "价格竞争激烈，强调性价比和售后响应速度。"),
    ("阿根廷 (Argentina)",
     "Prina Argentina(prina.net)是当地标杆品牌，35年历史。"
     "Exodo LED提供24期分期，专注中小客户。"
     "WhatsApp是主要联系渠道，附产品图片和价格表效果好。"),
]

for r, (country, tip) in enumerate(tips, 3):
    ws3.cell(row=r, column=1, value=country).font = Font(bold=True, size=11)
    ws3.cell(row=r, column=2, value=tip)
    ws3.row_dimensions[r].height = 48

ws3.column_dimensions["A"].width = 20
ws3.column_dimensions["B"].width = 80

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LED_Display_Leads_v6.xlsx")
wb.save(out)
print(f"Saved: {out}  ({len(leads)} records)")
