import email_sender_v58 as base

base.SUBJECT = "Recent LED Display Installations in Korea"
base.BODY_TEMPLATE = """\
Hi {name},

I'm Allen, from an LED display manufacturing factory in Shenzhen, China.

I found your LED display / LED video wall work and wanted to share a recent reference from Korea.

The attached project sheet includes indoor fine-pitch LED walls, outdoor LED screens, creative LED columns, and commercial LED installations.

If you have upcoming LED display projects, I can help recommend panel options based on screen size, viewing distance, installation method, and indoor/outdoor use.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp/WeChat: +86 135-7087-1001
Email: allenma2ong@gmail.com
"""

base.TARGETS = [
    {"no": 780, "company_en": "Aplus Exhibits", "email": "jacky@aplusexhibits.com", "name": "Jacky"},
    {"no": 781, "company_en": "Brilliant Event Lighting", "email": "hello@brillianteventlighting.com", "name": "Brilliant Event Lighting Team"},
    {"no": 782, "company_en": "Bolt LED", "email": "info@boltled.net", "name": "Bolt LED Team"},
    {"no": 783, "company_en": "ADMFA Audio", "email": "info@admfaaudio.com", "name": "ADMFA Audio Team"},
]

if __name__ == "__main__":
    base.main()
