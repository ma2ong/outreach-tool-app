"""
Email sender v66 - verified USA LED display / LED video wall batch.
Attaches the latest recent Korea projects poster.
"""
import email_sender_v58 as base

base.SUBJECT = "Recent LED Display Installations in Korea"
base.BODY_TEMPLATE = """\
Hi {name},

I'm Allen, from an LED display manufacturing factory in Shenzhen, China.

I found your LED video wall / LED screen work and wanted to share a recent reference from Korea. The attached project sheet includes indoor fine-pitch LED walls, outdoor LED screens, creative LED columns, and commercial LED installations.

If you ever need LED display panels for rental inventory, truck/screen upgrades, outdoor LED walls, or fixed installations, I can help recommend panel options based on size, viewing distance, brightness, pixel pitch, and maintenance needs.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp/WeChat: +86 135-7087-1001
Email: allenma2ong@gmail.com
"""

base.TARGETS = [
    {"no": 833, "company_en": "Titan Production Group", "email": "info@titanproductiongroup.com", "name": "Titan Production Group Team"},
    {"no": 834, "company_en": "BezaLED", "email": "info@bezaled.com", "name": "BezaLED Team"},
    {"no": 835, "company_en": "Event Technology Rentals (Rentipads)", "email": "info@rentipads.com", "name": "Event Technology Rentals Team"},
    {"no": 836, "company_en": "Access Audio", "email": "info@accessaudio.com", "name": "Access Audio Team"},
    {"no": 837, "company_en": "EventStarts", "email": "mllegeorgesand@gmail.com", "name": "EventStarts Team"},
    {"no": 838, "company_en": "Santiago Perez Productions", "email": "info@santiagoperezproductions.com", "name": "Santiago Perez Productions Team"},
    {"no": 839, "company_en": "Dionysus Creative", "email": "info@dionysuscreative.com", "name": "Dionysus Creative Team"},
    {"no": 840, "company_en": "Snell Vision", "email": "Info@snellvision.com", "name": "Snell Vision Team"},
    {"no": 841, "company_en": "Turning Point AV", "email": "info@turningpointav.com", "name": "Turning Point AV Team"},
]

if __name__ == "__main__":
    base.main()
