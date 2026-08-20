"""
Email sender v75 - verified USA LED display / LED video wall batch.
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
    {"no": 894, "company_en": "SOHO LED Rentals", "email": "Contact@SOHOLedRentals.com", "name": "SOHO LED Rentals Team"},
    {"no": 896, "company_en": "Ultimate Occasions", "email": "info@ultoccasions.com", "name": "Ultimate Occasions Team"},
    {"no": 897, "company_en": "1st Way Pro Rental", "email": "info@1stwayprorental.com", "name": "1st Way Pro Rental Team"},
    {"no": 898, "company_en": "NYC LED Wall Rental", "email": "wlab@wlab.tech", "name": "NYC LED Wall Rental Team"},
    {"no": 900, "company_en": "PhotoTek NYC", "email": "info@phototeknyc.com", "name": "PhotoTek NYC Team"},
]

if __name__ == "__main__":
    base.main()
