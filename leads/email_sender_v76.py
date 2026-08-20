"""
Email sender v76 - verified USA LED display / LED sign batch.
Attaches the latest recent Korea projects poster.
"""
import email_sender_v58 as base

base.SUBJECT = "Recent LED Display Installations in Korea"
base.BODY_TEMPLATE = """\
Hi {name},

I'm Allen, from an LED display manufacturing factory in Shenzhen, China.

I found your LED sign and LED display work and wanted to share a recent project reference from Korea. The attached project sheet includes indoor fine-pitch LED walls, outdoor LED screens, creative LED columns, and commercial LED installations.

If you ever need LED panels or full displays for outdoor signage, message centers, event video walls, or fixed installations, I can help recommend options based on screen size, viewing distance, brightness, pixel pitch, and service access.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp/WeChat: +86 135-7087-1001
Email: allenma2ong@gmail.com
"""

base.TARGETS = [
    {"no": 903, "company_en": "Sign On LLC", "email": "info@capeled.com", "name": "Sign On Team"},
]

if __name__ == "__main__":
    base.main()
