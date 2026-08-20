"""
Email sender v62 - verified USA LED display batch.
Attaches the latest recent Korea projects poster.
"""
import email_sender_v58 as base

base.SUBJECT = "Recent LED Display Installations in Korea"
base.BODY_TEMPLATE = """\
Hi {name},

I'm Allen, from an LED display manufacturing factory in Shenzhen, China.

I found your LED screen / LED video wall work and wanted to share a recent reference from Korea. The attached project sheet includes indoor fine-pitch LED walls, outdoor LED screens, creative LED columns, and commercial LED installations.

If you have upcoming LED display projects, I can help recommend panel options based on screen size, viewing distance, installation method, and indoor/outdoor use.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp/WeChat: +86 135-7087-1001
Email: allenma2ong@gmail.com
"""

base.TARGETS = [
    {"no": 798, "company_en": "LED Screen Rentals", "email": "sales@ledscreenrentals.net", "name": "LED Screen Rentals Team"},
    {"no": 800, "company_en": "FunFlicks Kentucky", "email": "funflickskentunky@gmail.com", "name": "FunFlicks Kentucky Team"},
    {"no": 801, "company_en": "Royal AV Solutions", "email": "info@royalavsolutions.com", "name": "Royal AV Solutions Team"},
    {"no": 802, "company_en": "Game Craze Party Rentals", "email": "office@gamecrazeparty.com", "name": "Game Craze Party Rentals Team"},
    {"no": 803, "company_en": "Freedom Fun USA Dayton", "email": "dayton@freedomfunusa.com", "name": "Freedom Fun Dayton Team"},
]

if __name__ == "__main__":
    base.main()
