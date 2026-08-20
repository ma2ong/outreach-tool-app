"""
Email sender v81 - verified USA LED display integrator batch (broadcast/esports).
Attaches the latest recent Korea projects poster.
"""
import email_sender_v58 as base

base.SUBJECT = "Recent LED Display Installations in Korea"
base.BODY_TEMPLATE = """\
Hi {name},

I'm Allen, from an LED display manufacturing factory in Shenzhen, China.

I came across your LED video wall and display integration work and wanted to share a recent project reference from Korea. The attached project sheet includes indoor fine-pitch LED walls, outdoor LED screens, creative LED columns, and commercial LED installations.

If you ever need LED panels or full displays for broadcast/studio walls, esports & education spaces, corporate video walls, or fixed installations, I can help recommend options based on screen size, viewing distance, brightness, pixel pitch, and service access.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp/WeChat: +86 135-7087-1001
Email: allenma2ong@gmail.com
"""

base.TARGETS = [
    {"no": 930, "company_en": "Data Projections", "email": "DPIWeb@dataprojections.com", "name": "Data Projections Team"},
    {"no": 931, "company_en": "Horizon AVL", "email": "info@horizonavl.com", "name": "Horizon AVL Team"},
]

if __name__ == "__main__":
    base.main()
