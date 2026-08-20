"""
Email sender v80 - verified USA LED display integrator / dealer batch.
Attaches the latest recent Korea projects poster.
"""
import email_sender_v58 as base

base.SUBJECT = "Recent LED Display Installations in Korea"
base.BODY_TEMPLATE = """\
Hi {name},

I'm Allen, from an LED display manufacturing factory in Shenzhen, China.

I came across your LED video wall and display integration work and wanted to share a recent project reference from Korea. The attached project sheet includes indoor fine-pitch LED walls, outdoor LED screens, creative LED columns, and commercial LED installations.

If you ever need LED panels or full displays for casino/hospitality walls, corporate lobbies, digital signage, rental inventory, or fixed installations, I can help recommend options based on screen size, viewing distance, brightness, pixel pitch, and service access.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp/WeChat: +86 135-7087-1001
Email: allenma2ong@gmail.com
"""

base.TARGETS = [
    {"no": 925, "company_en": "Alpha Video & Audio", "email": "boxsales@alphax.us", "name": "Alpha Video Team"},
    {"no": 926, "company_en": "Texadia Systems", "email": "support@texadiasystems.com", "name": "Texadia Systems Team"},
    {"no": 927, "company_en": "Ford AV", "email": "sales@fordav.com", "name": "Ford AV Team"},
    {"no": 928, "company_en": "E.C. Pro Video", "email": "info@ecprovideo.com", "name": "E.C. Pro Video Team"},
]

if __name__ == "__main__":
    base.main()
