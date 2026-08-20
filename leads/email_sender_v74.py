"""
Email sender v74 - verified USA LED display / LED video wall batch.
Attaches the latest recent Korea projects poster.
"""
import email_sender_v58 as base

base.SUBJECT = "Recent LED Display Installations in Korea"
base.BODY_TEMPLATE = """\
Hi {name},

I'm Allen, from an LED display manufacturing factory in Shenzhen, China.

I found your LED video wall / LED screen work and wanted to share a recent project reference from Korea. The attached project sheet includes indoor fine-pitch LED walls, outdoor LED screens, creative LED columns, and commercial LED installations.

If you ever need LED panels for rental inventory, event video walls, outdoor screens, or fixed installations, I can help recommend options based on screen size, viewing distance, brightness, pixel pitch, and service access.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp/WeChat: +86 135-7087-1001
Email: allenma2ong@gmail.com
"""

base.TARGETS = [
    {"no": 889, "company_en": "Iowa Media", "email": "matt@iowa-media.com", "name": "Matt"},
    {"no": 890, "company_en": "Assorted Studios", "email": "Assortedstudios@gmail.com", "name": "Jesse"},
    {"no": 891, "company_en": "Blue Sky Productions", "email": "info@blueskypd.com", "name": "Blue Sky Productions Team"},
    {"no": 892, "company_en": "Crescent Event Productions", "email": "hello@crescentevents.com", "name": "Crescent Event Productions Team"},
    {"no": 893, "company_en": "L/A Music Productions", "email": "lamusicproductions@yahoo.com", "name": "L/A Music Productions Team"},
]

if __name__ == "__main__":
    base.main()
