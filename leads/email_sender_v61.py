"""
Email sender v61 - verified USA LED display batch.
Attaches the latest recent Korea projects poster.
"""
import email_sender_v58 as base

base.SUBJECT = "Recent LED Display Installations in Korea"
base.BODY_TEMPLATE = """\
Hi {name},

I'm Allen, from an LED display manufacturing factory in Shenzhen, China.

I found your LED screen / LED video wall work and wanted to share a recent reference from Korea. The attached project sheet includes indoor fine-pitch LED walls, outdoor LED screens, creative LED columns, and commercial LED installations.

If you have upcoming LED display projects, I can help recommend panel options based on screen size, viewing distance, installation method, and indoor/outdoor use.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp/WeChat: +86 135-7087-1001
Email: allenma2ong@gmail.com
"""

base.TARGETS = [
    {"no": 792, "company_en": "Easy Audio Rental", "email": "james@jhansen.net", "name": "Easy Audio Rental Team"},
    {"no": 793, "company_en": "Full Swing Productions", "email": "admin@fullswingpro.com", "name": "Full Swing Productions Team"},
    {"no": 794, "company_en": "Queen City Screens", "email": "shaun@queencityscreens.com", "name": "Queen City Screens Team"},
    {"no": 795, "company_en": "Livestream Media Network", "email": "sales@livestreammedianetwork.com", "name": "Livestream Media Network Team"},
    {"no": 796, "company_en": "OVOMEDIA Audio / Video Services", "email": "ovoaudiovideo@gmail.com", "name": "OVOMEDIA Team"},
    {"no": 797, "company_en": "One Way Event Productions", "email": "WhatsUp@onewayep.com", "name": "One Way Event Productions Team"},
]

if __name__ == "__main__":
    base.main()
