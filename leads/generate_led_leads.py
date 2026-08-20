"""Generate LED Display Leads Excel for South America + North America markets."""
import openpyxl
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side
)
from openpyxl.utils import get_column_letter

leads = [
    # ==================== BRAZIL ====================
    {
        "no": 1, "country": "Brazil", "region": "South America",
        "company_en": "LedWave", "company_local": "LedWave",
        "city": "São Paulo / Goiânia / Rio de Janeiro / Brasília",
        "contact_name": "", "title": "",
        "email": "contato@ledwave.com.br",
        "phone_whatsapp": "+55 11 3044-4609 / +55 62 3921-7800",
        "website": "http://www.ledwave.com.br",
        "business": "LED display sales, rental & installation",
        "facebook": "", "instagram": "", "linkedin": "linkedin.com/company/ledwave",
    },
    {
        "no": 2, "country": "Brazil", "region": "South America",
        "company_en": "Crialed Visual Productions", "company_local": "Crialed Produções Visuais e Eventos",
        "city": "São Paulo, SP",
        "contact_name": "", "title": "",
        "email": "contato@crialed.com.br",
        "phone_whatsapp": "+55 11 2291-0031",
        "website": "https://www.crialed.com.br",
        "business": "LED panel sales, rental & event services",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 3, "country": "Brazil", "region": "South America",
        "company_en": "LED 10", "company_local": "LED 10",
        "city": "São Paulo, SP",
        "contact_name": "", "title": "",
        "email": "contato@led10.com.br",
        "phone_whatsapp": "+55 11 2115-3091",
        "website": "http://led10.com.br",
        "business": "LED panel sales & rental (since 2010)",
        "facebook": "facebook.com/paineisled10", "instagram": "", "linkedin": "",
    },
    {
        "no": 4, "country": "Brazil", "region": "South America",
        "company_en": "NA Equipment", "company_local": "N.A. Equipamentos",
        "city": "São Paulo, SP",
        "contact_name": "", "title": "",
        "email": "orcamentos1@naequipamentos.com.br",
        "phone_whatsapp": "+55 11 3606-7878",
        "website": "http://www.naequipamentos.com.br",
        "business": "Full-color LED panels, professional video equipment",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 5, "country": "Brazil", "region": "South America",
        "company_en": "P1LED / Prime LED", "company_local": "P1LED / Prime Led",
        "city": "São Paulo, SP",
        "contact_name": "", "title": "",
        "email": "contato@plled.com.br",
        "phone_whatsapp": "+55 11 95329-4173",
        "website": "https://www.primeled.com.br",
        "business": "LED panel sales & installation (DH Experience Group, 12+ years)",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 6, "country": "Brazil", "region": "South America",
        "company_en": "The LED", "company_local": "The LED",
        "city": "São Paulo, SP",
        "contact_name": "", "title": "",
        "email": "comercial@theled.com.br",
        "phone_whatsapp": "+55 11 98940-4332 / +55 11 96334-5500",
        "website": "http://www.theled.com.br",
        "business": "Largest digital visual communications company in Brazil, LED technology",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 7, "country": "Brazil", "region": "South America",
        "company_en": "Dshow", "company_local": "Dshow",
        "city": "São Paulo, SP",
        "contact_name": "", "title": "",
        "email": "dshow@dshow.com.br",
        "phone_whatsapp": "+55 11 99714-4969 / +55 11 3392-1514",
        "website": "http://www.dshow.com.br",
        "business": "Indoor/outdoor/flexible LED display solutions",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 8, "country": "Brazil", "region": "South America",
        "company_en": "Nationstar Brasil", "company_local": "Nationstar Brasil",
        "city": "São Paulo, SP",
        "contact_name": "", "title": "",
        "email": "vendas@nationstar.com.br",
        "phone_whatsapp": "+55 11 58974392",
        "website": "https://www.nationstarbrasil.com.br",
        "business": "Full-color LED panel supplier",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 9, "country": "Brazil", "region": "South America",
        "company_en": "Innovate Brazil", "company_local": "Innovate Brasil",
        "city": "Guarapari, ES",
        "contact_name": "", "title": "",
        "email": "contato@innovatebrazil.com.br",
        "phone_whatsapp": "+55 27 3362-1614",
        "website": "https://innovatebrazil.com.br",
        "business": "LED display solutions",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 10, "country": "Brazil", "region": "South America",
        "company_en": "Mundo de LED", "company_local": "Mundo de LED",
        "city": "São Paulo, SP",
        "contact_name": "", "title": "",
        "email": "sales@mundodeled.com.br",
        "phone_whatsapp": "(88) 99605-3355",
        "website": "https://www.mundodeled.com.br",
        "business": "LED displays (since 2013)",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 11, "country": "Brazil", "region": "South America",
        "company_en": "Optiart", "company_local": "Optiart",
        "city": "São Paulo, SP",
        "contact_name": "", "title": "",
        "email": "comercial@optiart.com.br",
        "phone_whatsapp": "+55 11 5060-4140",
        "website": "https://optiart.com.br",
        "business": "Retail digital signage & LED displays; official Samsung distributor in Brazil",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 12, "country": "Brazil", "region": "South America",
        "company_en": "Elite LED", "company_local": "Elite LED",
        "city": "Rio de Janeiro, RJ",
        "contact_name": "", "title": "",
        "email": "contato@eliteled.com.br",
        "phone_whatsapp": "+55 21 3344-0206",
        "website": "https://eliteled.com.br",
        "business": "Exclusive distributor for PROMARC LED screens in Brazil",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 13, "country": "Brazil", "region": "South America",
        "company_en": "Rangel Panels", "company_local": "Rangel Painéis",
        "city": "São Paulo, SP",
        "contact_name": "Flávio", "title": "Owner",
        "email": "flavio@rangelpaineis.com.br",
        "phone_whatsapp": "+55 11 99995-6612",
        "website": "https://rangelpaineis.com.br",
        "business": "LED display & advertising panels (since 1998)",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 14, "country": "Brazil", "region": "South America",
        "company_en": "Trend LED", "company_local": "Trend Led",
        "city": "Brasília, DF",
        "contact_name": "", "title": "",
        "email": "",
        "phone_whatsapp": "",
        "website": "",
        "business": "LED panel rental & sales",
        "facebook": "facebook.com/Trendbsb", "instagram": "", "linkedin": "",
    },
    # ==================== COLOMBIA ====================
    {
        "no": 15, "country": "Colombia", "region": "South America",
        "company_en": "PubliMaster Colombia", "company_local": "Publi Master SJ",
        "city": "Medellín",
        "contact_name": "", "title": "",
        "email": "ventas@publimastercolombia.com",
        "phone_whatsapp": "+57 311 2419363",
        "website": "https://publimastercolombia.com",
        "business": "LED screen importer & commercializer for events, indoor/outdoor advertising",
        "facebook": "facebook.com/publimasterSJ", "instagram": "instagram.com/publimastersj", "linkedin": "",
    },
    {
        "no": 16, "country": "Colombia", "region": "South America",
        "company_en": "Digital Signage Colombia", "company_local": "Digital Signage Colombia SAS",
        "city": "Bogotá",
        "contact_name": "", "title": "",
        "email": "negocios@dscolombia.co",
        "phone_whatsapp": "601 4321929 / WhatsApp: +57 317 521 1104",
        "website": "https://dscolombia.co",
        "business": "Official Samsung distributor (Colombia), LED video wall, touch screens, kiosks; 15+ years, 40,000+ installs",
        "facebook": "facebook.com/DigitalSignageColombia", "instagram": "instagram.com/digitalsignagecolombia",
        "linkedin": "linkedin.com/company/digital-signage-colombia-sas",
    },
    {
        "no": 17, "country": "Colombia", "region": "South America",
        "company_en": "MachineTronics", "company_local": "MachineTronics",
        "city": "Colombia (Bogotá, Medellín, Cali, etc.)",
        "contact_name": "Yulieth Cruz", "title": "",
        "email": "",
        "phone_whatsapp": "+57 318 3400796 / +57 316 4086143",
        "website": "https://www.machinetronics.com",
        "business": "LED screen manufacturer & distributor for advertising, events, real estate, corporate",
        "facebook": "facebook.com/MachineTronics", "instagram": "",
        "linkedin": "linkedin.com/in/yulieth-cruz-145a784a",
    },
    {
        "no": 18, "country": "Colombia", "region": "South America",
        "company_en": "Visual Led Colombia", "company_local": "Visual Led Colombia",
        "city": "Colombia",
        "contact_name": "", "title": "",
        "email": "ventas@visualled.com",
        "phone_whatsapp": "",
        "website": "https://visualled.com",
        "business": "LED screens for indoor/outdoor advertising in Colombia (since 2003)",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    # ==================== CHILE ====================
    {
        "no": 19, "country": "Chile", "region": "South America",
        "company_en": "PLED Chile", "company_local": "PLED.cl",
        "city": "Santiago",
        "contact_name": "", "title": "",
        "email": "info@pled.cl",
        "phone_whatsapp": "+56 9 3659-1068",
        "website": "https://www.pled.cl",
        "business": "LED display sales & rental",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 20, "country": "Chile", "region": "South America",
        "company_en": "Tecnogroup Chile", "company_local": "Tecnogroup",
        "city": "Las Condes, Santiago",
        "contact_name": "", "title": "",
        "email": "contacto@tecnogroup.cl",
        "phone_whatsapp": "+56 9 5449-1032",
        "website": "https://tecnogroup.cl",
        "business": "LED display & technology solutions",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 21, "country": "Chile", "region": "South America",
        "company_en": "Led Neon Chile", "company_local": "Led Neon Chile (LNC)",
        "city": "Renca, Santiago",
        "contact_name": "", "title": "",
        "email": "ventas@lnc.cl",
        "phone_whatsapp": "+56 2 2957-4444",
        "website": "https://www.lnc.cl",
        "business": "LED display & neon, 30 years expertise, electronic displays",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 22, "country": "Chile", "region": "South America",
        "company_en": "Remote Media", "company_local": "Remote Media",
        "city": "Ñuñoa, Santiago",
        "contact_name": "", "title": "",
        "email": "info@remotemedia.cl",
        "phone_whatsapp": "+56 2 2352-5532",
        "website": "https://remotemedia.cl",
        "business": "Digital signage & LED display solutions",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 23, "country": "Chile", "region": "South America",
        "company_en": "Fullvision", "company_local": "Fullvision",
        "city": "Ñuñoa, Santiago",
        "contact_name": "", "title": "",
        "email": "info@fullvision.cl",
        "phone_whatsapp": "+56 2 2455-6596",
        "website": "https://www.fullvision.cl",
        "business": "LED display system integrator",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 24, "country": "Chile", "region": "South America",
        "company_en": "Cleverox", "company_local": "Cleverox",
        "city": "Huechuraba, Santiago",
        "contact_name": "", "title": "",
        "email": "contacto@cleverox.com",
        "phone_whatsapp": "+56 2 2956-3200",
        "website": "https://www.cleverox.com",
        "business": "LED display and AV integration",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 25, "country": "Chile", "region": "South America",
        "company_en": "Demco Ltda", "company_local": "Demco Ltda",
        "city": "Quilicura, Santiago",
        "contact_name": "", "title": "",
        "email": "info@demco.cl",
        "phone_whatsapp": "+56 2 2782-1800",
        "website": "https://www.demco.cl",
        "business": "Wholesale distribution (since 1983), LED display & AV products",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 26, "country": "Chile", "region": "South America",
        "company_en": "4D LED Screens", "company_local": "4D Pantallas LEAD",
        "city": "Las Condes, Santiago",
        "contact_name": "", "title": "",
        "email": "info@cuatrod.net",
        "phone_whatsapp": "+56 2 434-1800",
        "website": "https://www.cuatrod.net",
        "business": "LED display solutions",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 27, "country": "Chile", "region": "South America",
        "company_en": "VideoWall Corporation", "company_local": "VideoWall Corporation SPA",
        "city": "La Reina, Santiago",
        "contact_name": "", "title": "",
        "email": "info@videowall.cl",
        "phone_whatsapp": "+56 9 8808-3220",
        "website": "https://www.videowall.cl",
        "business": "LED video wall systems integrator",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    # ==================== PERU ====================
    {
        "no": 28, "country": "Peru", "region": "South America",
        "company_en": "EXCTECLED Peru", "company_local": "Pantallas LED Peru - EXCTECLED",
        "city": "San Isidro, Lima",
        "contact_name": "", "title": "",
        "email": "ventas@exctecled.com",
        "phone_whatsapp": "+51 913059191",
        "website": "https://exctecled.com",
        "business": "Leading LED advertising screen distributor in Peru; fixed/rental/stadium/industrial",
        "facebook": "facebook.com/exctecled", "instagram": "instagram.com/pantallasledperu", "linkedin": "",
    },
    {
        "no": 29, "country": "Peru", "region": "South America",
        "company_en": "LED Laser Peru", "company_local": "LED y Laser Peru",
        "city": "Lima",
        "contact_name": "", "title": "",
        "email": "ventas@ledylaserperu.com",
        "phone_whatsapp": "+51 933 488 195",
        "website": "https://ledylaserperu.com",
        "business": "LED display sales & installation",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 30, "country": "Peru", "region": "South America",
        "company_en": "BiG LED Peru", "company_local": "BiG LED",
        "city": "Lima",
        "contact_name": "", "title": "",
        "email": "ventas@bigledperu.com",
        "phone_whatsapp": "+51 944 570 337",
        "website": "https://www.bigledperu.com",
        "business": "LED display wholesale & retail",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 31, "country": "Peru", "region": "South America",
        "company_en": "Layset Peru", "company_local": "Layset",
        "city": "Lima",
        "contact_name": "", "title": "",
        "email": "ventas@layset2.com",
        "phone_whatsapp": "+51 999 518 109",
        "website": "https://www.layset2.com",
        "business": "LED screen distributor, 15+ years experience",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 32, "country": "Peru", "region": "South America",
        "company_en": "Orion Enterprises Peru", "company_local": "ORION ENTERPRISES",
        "city": "Miraflores, Lima",
        "contact_name": "", "title": "",
        "email": "info@orion-peru.com",
        "phone_whatsapp": "+51 989 153 655",
        "website": "https://orion-peru.com",
        "business": "LED display solutions & integration",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 33, "country": "Peru", "region": "South America",
        "company_en": "NeoLED Peru", "company_local": "NEOLEDPERU",
        "city": "Los Olivos, Lima",
        "contact_name": "", "title": "",
        "email": "info@neoledperu.com",
        "phone_whatsapp": "+51 43 221 254",
        "website": "https://www.neoledperu.com",
        "business": "LED display sales & installation",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 34, "country": "Peru", "region": "South America",
        "company_en": "LED Maker Peru", "company_local": "LED MAKER",
        "city": "Lima",
        "contact_name": "", "title": "",
        "email": "ventas@ledmaker.com.pe",
        "phone_whatsapp": "+51 967 645 520",
        "website": "https://ledmaker.com.pe",
        "business": "LED display manufacturer & supplier",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 35, "country": "Peru", "region": "South America",
        "company_en": "INNOVALED Peru", "company_local": "INNOVALED",
        "city": "Surquillo, Lima",
        "contact_name": "", "title": "",
        "email": "ventas@innovaled.pe",
        "phone_whatsapp": "+51 986 534 469",
        "website": "https://www.innovaled.pe",
        "business": "LED display innovation & sales",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 36, "country": "Peru", "region": "South America",
        "company_en": "Goled Peru", "company_local": "Goled Peru",
        "city": "Lima",
        "contact_name": "", "title": "",
        "email": "ventas@goledperu.com",
        "phone_whatsapp": "+51 1 639-6589",
        "website": "http://goledperu.com",
        "business": "14 years in professional LED lighting & display",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    # ==================== ARGENTINA ====================
    {
        "no": 37, "country": "Argentina", "region": "South America",
        "company_en": "Dinalight", "company_local": "Dinalight",
        "city": "Buenos Aires",
        "contact_name": "", "title": "",
        "email": "info@dinalight.com",
        "phone_whatsapp": "+54 9 11 4064-9989 / WA: +54 9 11 3848-0840",
        "website": "https://www.dinalight.com",
        "business": "LED display manufacturer (20+ years), indoor/outdoor/rental/mesh/floor displays; expands across Latin America",
        "facebook": "facebook.com/p/Dinalightlatam-100072348303065",
        "instagram": "instagram.com/dinalight.led", "linkedin": "",
    },
    {
        "no": 38, "country": "Argentina", "region": "South America",
        "company_en": "Grupo UNO LED", "company_local": "Grupo UNO LED",
        "city": "Buenos Aires / Santiago del Estero",
        "contact_name": "", "title": "",
        "email": "info@grupounoled.com",
        "phone_whatsapp": "+54 9 11 5740-6998",
        "website": "https://grupounoled.com",
        "business": "Argentine LED screen factory, 3000+ clients, outdoor/indoor/mobile displays",
        "facebook": "facebook.com/grupounoled", "instagram": "instagram.com/grupounoled", "linkedin": "",
    },
    # ==================== USA ====================
    {
        "no": 39, "country": "USA", "region": "North America",
        "company_en": "American LED Display Solutions", "company_local": "American LED Display Solutions Corp.",
        "city": "Miami, FL",
        "contact_name": "", "title": "",
        "email": "Info@americanledisplays.com",
        "phone_whatsapp": "+1 305-420-5631 / +1 786-228-9212",
        "website": "https://americanledisplays.com",
        "business": "LED visual display manufacturer & supplier; indoor/outdoor/sports/transparent; global distribution network",
        "facebook": "facebook.com/AmericanLedDisplays", "instagram": "instagram.com/americanledisplays",
        "linkedin": "linkedin.com/in/american-led-display-solutions-0a116519",
    },
    {
        "no": 40, "country": "USA", "region": "North America",
        "company_en": "Fusion LED", "company_local": "Fusion LED Inc.",
        "city": "Houston, TX",
        "contact_name": "Richard James / Darick Endecott", "title": "Founders",
        "email": "sales@fusionled.us",
        "phone_whatsapp": "+1 800-854-6265",
        "website": "https://fusionled.us",
        "business": "LED display sign manufacturer; B2B wholesale to sign companies nationwide; 1000+ installs in 50+ states",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 41, "country": "USA", "region": "North America",
        "company_en": "American LED Technology", "company_local": "American LED Technology",
        "city": "North Little Rock, AR",
        "contact_name": "", "title": "",
        "email": "info@americanledtechnology.com",
        "phone_whatsapp": "+1 850-863-8777",
        "website": "https://www.americanledtechnology.com",
        "business": "LED display manufacturer",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 42, "country": "USA", "region": "North America",
        "company_en": "Advision LED Signs", "company_local": "Advision LED Signs",
        "city": "Oakdale, CA",
        "contact_name": "", "title": "",
        "email": "contact@advisionledsigns.com",
        "phone_whatsapp": "+1 877-532-5593",
        "website": "https://advisionledsigns.com",
        "business": "LED sign solutions",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 43, "country": "USA", "region": "North America",
        "company_en": "Vanguard LED Displays", "company_local": "Vanguard LED Displays",
        "city": "Lakeland, FL",
        "contact_name": "", "title": "",
        "email": "info@vanguardled.com",
        "phone_whatsapp": "+1 877-230-8787",
        "website": "https://vanguardled.com",
        "business": "LED display distributor & installer",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 44, "country": "USA", "region": "North America",
        "company_en": "Aurora LED Systems", "company_local": "Aurora LED, LLC",
        "city": "Henderson / Las Vegas, NV",
        "contact_name": "", "title": "",
        "email": "info@auroraled.com",
        "phone_whatsapp": "+1 702-386-1088",
        "website": "https://auroraledsystems.com",
        "business": "LED video display provider; sells to qualified Resellers & Integrators across US & Western Hemisphere",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 45, "country": "USA", "region": "North America",
        "company_en": "RP Visual Solutions", "company_local": "RP Visual Solutions",
        "city": "Anaheim, CA",
        "contact_name": "", "title": "",
        "email": "sales@rpvisuals.com",
        "phone_whatsapp": "+1 714-991-6400",
        "website": "https://rpvisuals.com",
        "business": "LED display & AV visual solutions",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 46, "country": "USA", "region": "North America",
        "company_en": "King Size LED", "company_local": "King Size LED",
        "city": "Chula Vista, CA",
        "contact_name": "", "title": "",
        "email": "info@kingsizeled.com",
        "phone_whatsapp": "+1 619-216-4770",
        "website": "https://www.kingsizeled.com",
        "business": "Large-format LED displays",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 47, "country": "USA", "region": "North America",
        "company_en": "LED Craft", "company_local": "LED Craft Inc.",
        "city": "St. Louis, MO",
        "contact_name": "", "title": "",
        "email": "info@ledcraftinc.com",
        "phone_whatsapp": "+1 314-776-2909",
        "website": "https://www.ledcraftinc.com",
        "business": "LED display manufacturer & distributor",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 48, "country": "USA", "region": "North America",
        "company_en": "SNA Displays", "company_local": "SNA Displays",
        "city": "New York, NY",
        "contact_name": "", "title": "",
        "email": "",
        "phone_whatsapp": "+1 866-848-9149",
        "website": "https://snadisplays.com",
        "business": "Large-scale LED display systems integrator",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 49, "country": "USA", "region": "North America",
        "company_en": "Cirrus LED", "company_local": "Cirrusled",
        "city": "Portsmouth, NH",
        "contact_name": "", "title": "",
        "email": "info@cirrusled.com",
        "phone_whatsapp": "+1 877-636-2331",
        "website": "https://www.cirrusled.com",
        "business": "LED display solutions",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    # ==================== CANADA ====================
    {
        "no": 50, "country": "Canada", "region": "North America",
        "company_en": "Christie Digital", "company_local": "Christie Digital Systems",
        "city": "Kitchener, ON",
        "contact_name": "", "title": "",
        "email": "info@christiedigital.com",
        "phone_whatsapp": "+1 714-527-7056",
        "website": "https://www.christiedigital.com",
        "business": "Large-format display & video wall manufacturer; wholesale to resellers and integrators",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    # ==================== MEXICO ====================
    {
        "no": 51, "country": "Mexico", "region": "North America",
        "company_en": "RGB Tronics", "company_local": "RGB Tronics",
        "city": "Monterrey",
        "contact_name": "", "title": "",
        "email": "info@rgbtronics.com.mx",
        "phone_whatsapp": "+52 81 1772-4695",
        "website": "https://rgbtronics.com.mx",
        "business": "LED giant screen wholesale & retail, advertising screens, 10+ years",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 52, "country": "Mexico", "region": "North America",
        "company_en": "DMX Technologies", "company_local": "DMX TEC",
        "city": "Mexico City",
        "contact_name": "", "title": "",
        "email": "info@dmxtec.com",
        "phone_whatsapp": "+52 55 5662-2600",
        "website": "https://pantallasled.mx",
        "business": "Large-scale LED electronic screen wholesaler, 10+ years",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 53, "country": "Mexico", "region": "North America",
        "company_en": "Kolo Digital", "company_local": "Kolo",
        "city": "Mexico City",
        "contact_name": "", "title": "",
        "email": "contacto@kolo.digital",
        "phone_whatsapp": "+52 1 55 1107-8686",
        "website": "https://kolo.digital",
        "business": "LED display & digital signage solutions",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 54, "country": "Mexico", "region": "North America",
        "company_en": "MMP Screen", "company_local": "MMP Screen",
        "city": "Mexico City",
        "contact_name": "", "title": "",
        "email": "info@mmp.com.mx",
        "phone_whatsapp": "+52 55 7982-5360",
        "website": "https://mmp.com.mx",
        "business": "LED screen solutions",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 55, "country": "Mexico", "region": "North America",
        "company_en": "LUMTEC Mexico", "company_local": "LUMTEC",
        "city": "Mexico City",
        "contact_name": "", "title": "",
        "email": "info@lumtec.com.mx",
        "phone_whatsapp": "+52 55 6775-5117",
        "website": "https://lumtec.com.mx",
        "business": "LED display solutions",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 56, "country": "Mexico", "region": "North America",
        "company_en": "Eyecatch Mexico", "company_local": "Eyecatch Mexico",
        "city": "Mexico City",
        "contact_name": "Eduardo Rosales", "title": "",
        "email": "eduardo.rosales@eyecatch.mx",
        "phone_whatsapp": "+52 56 1004-6498",
        "website": "https://eyecatch.mx",
        "business": "LED display & digital signage",
        "facebook": "", "instagram": "", "linkedin": "",
    },
    {
        "no": 57, "country": "Mexico", "region": "North America",
        "company_en": "SAP LED", "company_local": "SAP LED",
        "city": "San Luis Potosí",
        "contact_name": "", "title": "",
        "email": "contacto@sapled.mx",
        "phone_whatsapp": "+52 444 210-0824",
        "website": "https://sapled.mx",
        "business": "LED display distributor",
        "facebook": "", "instagram": "", "linkedin": "",
    },
]

# ─── Build workbook ───────────────────────────────────────────────────────────
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "LED Leads"

# Color palette
COLOR_HEADER_BG   = "1F4E79"   # dark blue header
COLOR_HEADER_FONT = "FFFFFF"
COLOR_BRAZIL      = "D9EAD3"   # green-ish
COLOR_COLOMBIA    = "FCE5CD"   # orange-ish
COLOR_CHILE       = "D0E4F5"   # light blue
COLOR_PERU        = "FFF2CC"   # yellow
COLOR_ARGENTINA   = "EAD1DC"   # pink
COLOR_USA         = "CFE2F3"   # blue
COLOR_CANADA      = "E6D0DE"   # mauve
COLOR_MEXICO      = "D9D2E9"   # purple

COUNTRY_COLORS = {
    "Brazil": COLOR_BRAZIL,
    "Colombia": COLOR_COLOMBIA,
    "Chile": COLOR_CHILE,
    "Peru": COLOR_PERU,
    "Argentina": COLOR_ARGENTINA,
    "USA": COLOR_USA,
    "Canada": COLOR_CANADA,
    "Mexico": COLOR_MEXICO,
}

headers = [
    "No.", "Region", "Country", "City",
    "Company (English)", "Company (Local)",
    "Contact Person", "Title",
    "Email", "Phone / WhatsApp",
    "Website", "Main Business",
    "Facebook", "Instagram", "LinkedIn",
]

# Write headers
header_fill = PatternFill("solid", fgColor=COLOR_HEADER_BG)
header_font = Font(bold=True, color=COLOR_HEADER_FONT, size=11)
header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

thin = Side(style="thin", color="BBBBBB")
border = Border(left=thin, right=thin, top=thin, bottom=thin)

for col_idx, h in enumerate(headers, 1):
    cell = ws.cell(row=1, column=col_idx, value=h)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = header_align
    cell.border = border

ws.row_dimensions[1].height = 32

# Write data
for row_idx, lead in enumerate(leads, 2):
    row_data = [
        lead["no"], lead["region"], lead["country"], lead["city"],
        lead["company_en"], lead["company_local"],
        lead["contact_name"], lead["title"],
        lead["email"], lead["phone_whatsapp"],
        lead["website"], lead["business"],
        lead["facebook"], lead["instagram"], lead["linkedin"],
    ]
    country = lead["country"]
    fill_color = COUNTRY_COLORS.get(country, "FFFFFF")
    row_fill = PatternFill("solid", fgColor=fill_color)

    for col_idx, value in enumerate(row_data, 1):
        cell = ws.cell(row=row_idx, column=col_idx, value=value)
        cell.fill = row_fill
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        cell.border = border

    ws.row_dimensions[row_idx].height = 28

# Column widths
col_widths = [5, 14, 12, 22, 28, 28, 16, 14, 30, 30, 32, 48, 30, 28, 38]
for col_idx, width in enumerate(col_widths, 1):
    ws.column_dimensions[get_column_letter(col_idx)].width = width

# Freeze top row
ws.freeze_panes = "A2"

# Add a summary sheet
ws_sum = wb.create_sheet("Summary")
ws_sum["A1"] = "LED Display Leads — South & North America"
ws_sum["A1"].font = Font(bold=True, size=14, color=COLOR_HEADER_BG)
ws_sum["A3"] = "Region"
ws_sum["B3"] = "Country"
ws_sum["C3"] = "# Companies"

for cell in ws_sum["A3:C3"][0]:
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = Alignment(horizontal="center")

summary_rows = [
    ("South America", "Brazil", 14),
    ("South America", "Colombia", 4),
    ("South America", "Chile", 9),
    ("South America", "Peru", 10),
    ("South America", "Argentina", 2),
    ("North America", "USA", 11),
    ("North America", "Canada", 1),
    ("North America", "Mexico", 7),
]
for i, (region, country, count) in enumerate(summary_rows, 4):
    ws_sum.cell(row=i, column=1, value=region)
    ws_sum.cell(row=i, column=2, value=country)
    ws_sum.cell(row=i, column=3, value=count)
    fill = PatternFill("solid", fgColor=COUNTRY_COLORS.get(country, "FFFFFF"))
    for c in range(1, 4):
        ws_sum.cell(row=i, column=c).fill = fill

total_row = len(summary_rows) + 4
ws_sum.cell(row=total_row, column=1, value="TOTAL")
ws_sum.cell(row=total_row, column=3, value=sum(r[2] for r in summary_rows))
for c in range(1, 4):
    ws_sum.cell(row=total_row, column=c).font = Font(bold=True)

for col in ["A", "B", "C"]:
    ws_sum.column_dimensions[col].width = 22

out_path = r"C:\Users\Administrator\ai-topic-generator\output\leads\LED_Display_Leads_Americas.xlsx"
wb.save(out_path)
print(f"Saved: {out_path}")
print(f"Total records: {len(leads)}")
