"""
Email sender v63 - verified USA LED display batch.
Attaches the latest recent Korea projects poster.
"""
import email_sender_v58 as base

base.SUBJECT = "Recent LED Display Installations in Korea"
base.BODY_TEMPLATE = """\
Hi {name},

I'm Allen, from an LED display manufacturing factory in Shenzhen, China.

I found your LED display / LED video wall work and wanted to share a recent reference from Korea. The attached project sheet includes indoor fine-pitch LED walls, outdoor LED screens, creative LED columns, and commercial LED installations.

If you have upcoming LED display projects, I can help recommend panel options based on screen size, viewing distance, installation method, and indoor/outdoor use.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp/WeChat: +86 135-7087-1001
Email: allenma2ong@gmail.com
"""

base.TARGETS = [
    {"no": 805, "company_en": "SRXTeK", "email": "info@srxtek.com", "name": "SRXTeK Team"},
    {"no": 806, "company_en": "LED Exhibits", "email": "info@ledexhibits.com", "name": "LED Exhibits Team"},
    {"no": 807, "company_en": "Grant's Tech", "email": "info@grantstech.net", "name": "Grant's Tech Team"},
    {"no": 808, "company_en": "Summit Prestige", "email": "support@summitprestige.com", "name": "Summit Prestige Team"},
    {"no": 809, "company_en": "The Tekk Group Corporation", "email": "hire@thetekkgroup.com", "name": "The Tekk Group Team"},
    {"no": 810, "company_en": "Profigroup", "email": "info@profigroup.us", "name": "Profigroup Team"},
    {"no": 811, "company_en": "Big Wheel Digital Media", "email": "info@bigwheeldigitalmedia.com", "name": "Big Wheel Digital Media Team"},
    {"no": 812, "company_en": "Mobile Technology Graphics", "email": "info@mtgsigns.com", "name": "MTG Team"},
    {"no": 813, "company_en": "HB Live", "email": "info@hblive.com", "name": "HB Live Team"},
]

if __name__ == "__main__":
    base.main()
