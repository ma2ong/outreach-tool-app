"""
Email sender v78 - verified USA LED display integrator / cross-hire rental batch.
Attaches the latest recent Korea projects poster.
"""
import email_sender_v58 as base

base.SUBJECT = "Recent LED Display Installations in Korea"
base.BODY_TEMPLATE = """\
Hi {name},

I'm Allen, from an LED display manufacturing factory in Shenzhen, China.

I came across your LED video wall and display integration work and wanted to share a recent project reference from Korea. The attached project sheet includes indoor fine-pitch LED walls, outdoor LED screens, creative LED columns, and commercial LED installations.

If you ever need LED panels or full displays for video walls, digital signage, sports-bar/restaurant screens, rental inventory, or fixed installations, I can help recommend options based on screen size, viewing distance, brightness, pixel pitch, and service access.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp/WeChat: +86 135-7087-1001
Email: allenma2ong@gmail.com
"""

base.TARGETS = [
    {"no": 910, "company_en": "APG Rentals", "email": "rentals@apgrents.com", "name": "APG Rentals Team"},
    {"no": 911, "company_en": "Coffman Media", "email": "sales@coffmanmedia.com", "name": "Coffman Media Team"},
    {"no": 912, "company_en": "Soflo Systems", "email": "info@soflosystems.com", "name": "Soflo Systems Team"},
    {"no": 913, "company_en": "Jireh Supplies", "email": "sales@jirehsupplies.com", "name": "Jireh Supplies Team"},
    {"no": 914, "company_en": "BCI Integrated Solutions", "email": "service@bcifl.net", "name": "BCI Integrated Solutions Team"},
]

if __name__ == "__main__":
    base.main()
