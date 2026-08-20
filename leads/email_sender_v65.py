"""
Email sender v65 - verified USA LED display / mobile LED truck batch.
Attaches the latest recent Korea projects poster.
"""
import email_sender_v58 as base

base.SUBJECT = "Recent LED Display Installations in Korea"
base.BODY_TEMPLATE = """\
Hi {name},

I'm Allen, from an LED display manufacturing factory in Shenzhen, China.

I found your mobile LED truck / LED display work and wanted to share a recent reference from Korea. The attached project sheet includes indoor fine-pitch LED walls, outdoor LED screens, creative LED columns, and commercial LED installations.

If you ever need LED display panels for truck screen upgrades, modular LED video walls, outdoor rental screens, or fixed installations, I can help recommend panel options based on size, viewing distance, brightness, and maintenance needs.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp/WeChat: +86 135-7087-1001
Email: allenma2ong@gmail.com
"""

base.TARGETS = [
    {"no": 824, "company_en": "MVS Media Group", "email": "sales@mvsmediagroup.com", "name": "MVS Media Group Team"},
    {"no": 825, "company_en": "LEDTRUCK.COM", "email": "sales@ledtruck.com", "name": "LEDTRUCK.COM Team"},
    {"no": 826, "company_en": "Mobile LED Trucks", "email": "info@mobileledtrucks.com", "name": "Mobile LED Trucks Team"},
    {"no": 827, "company_en": "Advanced Mobile LED", "email": "allen@advancedmobileled.com", "name": "Allen"},
    {"no": 829, "company_en": "DMS LED Trucks", "email": "info@dmsledtruck.com", "name": "DMS LED Trucks Team"},
    {"no": 830, "company_en": "Lux Media", "email": "ads@theluxtruck.com", "name": "Lux Media Team"},
    {"no": 831, "company_en": "Nomadic Genius", "email": "regis@nomadicgenius.com", "name": "Regis"},
]

if __name__ == "__main__":
    base.main()
