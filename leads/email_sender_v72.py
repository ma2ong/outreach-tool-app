"""
Email sender v72 - verified USA LED display / LED video wall batch.
Attaches the latest recent Korea projects poster.
"""
import email_sender_v58 as base

base.SUBJECT = "Recent LED Display Installations in Korea"
base.BODY_TEMPLATE = """\
Hi {name},

I'm Allen, from an LED display manufacturing factory in Shenzhen, China.

I found your LED video wall / LED screen work and wanted to share a recent reference from Korea. The attached project sheet includes indoor fine-pitch LED walls, outdoor LED screens, creative LED columns, and commercial LED installations.

If you ever need LED display panels for rental inventory, event video walls, XR stages, outdoor LED screens, or fixed installations, I can help recommend panel options based on size, viewing distance, brightness, pixel pitch, and maintenance needs.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp/WeChat: +86 135-7087-1001
Email: allenma2ong@gmail.com
"""

base.TARGETS = [
    {"no": 877, "company_en": "Masato Events", "email": "info@masatoevents.com", "name": "Masato Events Team"},
    {"no": 878, "company_en": "Radium Pictures", "email": "info@radiumpix.com", "name": "Radium Pictures Team"},
    {"no": 879, "company_en": "AV Rentals NYC", "email": "info@avrentalsnyc.com", "name": "AV Rentals NYC Team"},
    {"no": 880, "company_en": "Affordable Sound Stages", "email": "affordablesoundstages@yahoo.com", "name": "Vic"},
    {"no": 881, "company_en": "Interactive Vision Solutions", "email": "info@avequipmentrental.nyc", "name": "Interactive Vision Solutions Team"},
]

if __name__ == "__main__":
    base.main()
