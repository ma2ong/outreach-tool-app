"""
Email sender v71 - verified USA LED display / LED video wall batch.
Attaches the latest recent Korea projects poster.
"""
import email_sender_v58 as base

base.SUBJECT = "Recent LED Display Installations in Korea"
base.BODY_TEMPLATE = """\
Hi {name},

I'm Allen, from an LED display manufacturing factory in Shenzhen, China.

I found your LED video wall / LED screen work and wanted to share a recent reference from Korea. The attached project sheet includes indoor fine-pitch LED walls, outdoor LED screens, creative LED columns, and commercial LED installations.

If you ever need LED display panels for rental inventory, event video walls, outdoor LED screens, or fixed installations, I can help recommend panel options based on size, viewing distance, brightness, pixel pitch, and maintenance needs.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp/WeChat: +86 135-7087-1001
Email: allenma2ong@gmail.com
"""

base.TARGETS = [
    {"no": 872, "company_en": "Goodboy Multimedia", "email": "goodboymultimedia@gmail.com", "name": "Daniel"},
    {"no": 873, "company_en": "The ProMedia Group", "email": "sales@thepromediagroup.com", "name": "The ProMedia Group Team"},
    {"no": 874, "company_en": "EventFab", "email": "alex@eventfab.com", "name": "Alex"},
    {"no": 876, "company_en": "media mea", "email": "sales@mediamea.io", "name": "media mea Team"},
]

if __name__ == "__main__":
    base.main()
