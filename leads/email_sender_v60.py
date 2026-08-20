import email_sender_v58 as base

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
    {"no": 784, "company_en": "Evix Rentals", "email": "info@evixrentals.com", "name": "Evix Rentals Team"},
    {"no": 785, "company_en": "AVPLED", "email": "info@avpled.com", "name": "AVPLED Team"},
    {"no": 786, "company_en": "Stage Kings", "email": "info@StageKings.com", "name": "Stage Kings Team"},
    {"no": 787, "company_en": "DJ Peoples", "email": "Rentals@DJPeoples.com", "name": "DJ Peoples Team"},
]

if __name__ == "__main__":
    base.main()
