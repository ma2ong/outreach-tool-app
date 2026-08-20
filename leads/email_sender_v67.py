"""
Email sender v67 - verified USA LED display / LED video wall batch.
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
    {"no": 842, "company_en": "Crispy Audio", "email": "info@crispyaudio.com", "name": "Crispy Audio Team"},
    {"no": 843, "company_en": "PEAK Technologies", "email": "info@peakt.com", "name": "PEAK Technologies Team"},
    {"no": 845, "company_en": "Murray Scott Production Services", "email": "info@mspsglobal.com", "name": "MSPS Team"},
    {"no": 846, "company_en": "Brightlight Film", "email": "info@Brightlightfilm.us", "name": "Brightlight Film Team"},
    {"no": 847, "company_en": "Riverside LED Video Walls", "email": "info@riversideledvideowalls.com", "name": "Riverside LED Video Walls Team"},
    {"no": 848, "company_en": "Audio Design Rentals", "email": "info@audiodesignrentals.com", "name": "Audio Design Rentals Team"},
    {"no": 849, "company_en": "RCC Events", "email": "info@rccevent.com", "name": "RCC Events Team"},
    {"no": 850, "company_en": "Angels Music Productions", "email": "info@angelsmusic.net", "name": "Angels Music Productions Team"},
]

if __name__ == "__main__":
    base.main()
