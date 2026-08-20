"""
Email sender v70 - verified USA LED display / LED video wall batch.
Attaches the latest recent Korea projects poster.
"""
import email_sender_v58 as base

base.SUBJECT = "Recent LED Display Installations in Korea"
base.BODY_TEMPLATE = """\
Hi {name},

I'm Allen, from an LED display manufacturing factory in Shenzhen, China.

I found your LED video wall / LED screen work and wanted to share a recent reference from Korea. The attached project sheet includes indoor fine-pitch LED walls, outdoor LED screens, creative LED columns, and commercial LED installations.

If you ever need LED display panels for rental inventory, studio LED walls, outdoor LED screens, or fixed installations, I can help recommend panel options based on size, viewing distance, brightness, pixel pitch, and maintenance needs.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp/WeChat: +86 135-7087-1001
Email: allenma2ong@gmail.com
"""

base.TARGETS = [
    {"no": 867, "company_en": "Metat3ch", "email": "info@metat3ch.com", "name": "Metat3ch Team"},
    {"no": 868, "company_en": "Reventals", "email": "info@reventals.com", "name": "Reventals Team"},
    {"no": 869, "company_en": "GC Event Studio", "email": "hey@gceventstudio.com", "name": "GC Event Studio Team"},
    {"no": 870, "company_en": "Fox Audio Visual", "email": "joseph@foxaudiovisual.com", "name": "Joseph"},
]

if __name__ == "__main__":
    base.main()
