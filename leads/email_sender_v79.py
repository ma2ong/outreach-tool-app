"""
Email sender v79 - verified USA LED display integrator / installer batch.
Attaches the latest recent Korea projects poster.
"""
import email_sender_v58 as base

base.SUBJECT = "Recent LED Display Installations in Korea"
base.BODY_TEMPLATE = """\
Hi {name},

I'm Allen, from an LED display manufacturing factory in Shenzhen, China.

I came across your LED video wall and display integration work and wanted to share a recent project reference from Korea. The attached project sheet includes indoor fine-pitch LED walls, outdoor LED screens, creative LED columns, and commercial LED installations.

If you ever need LED panels or full displays for church/worship walls, corporate video walls, digital signage, or fixed installations, I can help recommend options based on screen size, viewing distance, brightness, pixel pitch, and service access.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp/WeChat: +86 135-7087-1001
Email: allenma2ong@gmail.com
"""

base.TARGETS = [
    {"no": 919, "company_en": "CSAV Systems", "email": "info@csavsystems.com", "name": "CSAV Systems Team"},
    {"no": 920, "company_en": "S&L Integrated", "email": "info@slintegrated.com", "name": "S&L Integrated Team"},
    {"no": 921, "company_en": "Commercial AV Services", "email": "tomc@commercialavservices.com", "name": "Tom"},
    {"no": 922, "company_en": "Above AVL", "email": "gear@aboveavl.com", "name": "Above AVL Team"},
    {"no": 923, "company_en": "Video Walls 4 Less", "email": "consulting@videowalls4less.com", "name": "Video Walls 4 Less Team"},
]

if __name__ == "__main__":
    base.main()
