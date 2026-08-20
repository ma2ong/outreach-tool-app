"""
Email sender v64 - verified USA LED display batch.
Attaches the latest recent Korea projects poster.
"""
import email_sender_v58 as base

base.SUBJECT = "Recent LED Display Installations in Korea"
base.BODY_TEMPLATE = """\
Hi {name},

I'm Allen, from an LED display manufacturing factory in Shenzhen, China.

I found your LED display / LED billboard truck work and wanted to share a recent reference from Korea. The attached project sheet includes indoor fine-pitch LED walls, outdoor LED screens, creative LED columns, and commercial LED installations.

If you have upcoming LED display projects, I can help recommend panel options based on screen size, viewing distance, installation method, and indoor/outdoor use.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp/WeChat: +86 135-7087-1001
Email: allenma2ong@gmail.com
"""

base.TARGETS = [
    {"no": 814, "company_en": "Trailex LED Event Solutions", "email": "trailex1@aol.com", "name": "Trailex LED Team"},
    {"no": 816, "company_en": "Big Screens On The Go", "email": "GoBig@BigScreensOnTheGo.com", "name": "Big Screens On The Go Team"},
    {"no": 817, "company_en": "Brands In Motion", "email": "info@BrandsInMotion.com", "name": "Brands In Motion Team"},
    {"no": 818, "company_en": "Rolling Outdoor Media", "email": "info@rollingoutdoormedia.com", "name": "Rolling Outdoor Media Team"},
    {"no": 819, "company_en": "Mobile Billboard Miami", "email": "info@mobilebillboardmiami.com", "name": "Mobile Billboard Miami Team"},
    {"no": 820, "company_en": "DAT Media FL", "email": "Info@bestadvertisingtruck.com", "name": "DAT Media Team"},
    {"no": 821, "company_en": "LED Truck Media", "email": "sales@ledtruckmedia.com", "name": "LED Truck Media Team"},
    {"no": 822, "company_en": "Lime Media", "email": "info@lime-media.com", "name": "Lime Media Team"},
]

if __name__ == "__main__":
    base.main()
