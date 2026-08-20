"""
Email sender v69 - verified USA LED display / LED video wall batch.
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
    {"no": 861, "company_en": "Beantown Audio Rentals", "email": "info@beantownaudiorentals.com", "name": "Beantown Audio Rentals Team"},
    {"no": 862, "company_en": "A. A. Rental", "email": "info@aarental.com", "name": "A. A. Rental Team"},
    {"no": 864, "company_en": "AValive", "email": "customerservice@avalive.com", "name": "AValive Team"},
    {"no": 865, "company_en": "Electric Events DC", "email": "hithere@electriceventsdc.com", "name": "Electric Events DC Team"},
    {"no": 866, "company_en": "Screenworks NEP", "email": "info@screenworksnep.com", "name": "Screenworks NEP Team"},
]

if __name__ == "__main__":
    base.main()
