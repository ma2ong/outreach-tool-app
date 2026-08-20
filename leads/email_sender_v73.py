"""
Email sender v73 - verified USA LED display / LED video wall batch.
Attaches the latest recent Korea projects poster.
"""
import email_sender_v58 as base

base.SUBJECT = "Recent LED Display Installations in Korea"
base.BODY_TEMPLATE = """\
Hi {name},

I'm Allen, from an LED display manufacturing factory in Shenzhen, China.

I found your LED display / LED video wall work and wanted to share a recent project reference from Korea. The attached project sheet includes indoor fine-pitch LED walls, outdoor LED screens, creative LED columns, and commercial LED installations.

If you ever need LED panels for rental inventory, event video walls, XR stages, outdoor displays, or fixed installations, I can help recommend options based on screen size, viewing distance, brightness, pixel pitch, and maintenance access.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp/WeChat: +86 135-7087-1001
Email: allenma2ong@gmail.com
"""

base.TARGETS = [
    {"no": 884, "company_en": "American Movie Company", "email": "info@americanmovieco.com", "name": "American Movie Company Team"},
    {"no": 885, "company_en": "SOFLO Main Events", "email": "info@soflomainevents.com", "name": "SOFLO Main Events Team"},
    {"no": 886, "company_en": "Pure AV", "email": "info@pureav.co", "name": "Pure AV Team"},
    {"no": 887, "company_en": "Digital Sign Distributors", "email": "info@digitalsigndistributors.com", "name": "Digital Sign Distributors Team"},
    {"no": 888, "company_en": "DVS LED Systems", "email": "sales@dvsledsystems.com", "name": "DVS LED Systems Team"},
]

if __name__ == "__main__":
    base.main()
