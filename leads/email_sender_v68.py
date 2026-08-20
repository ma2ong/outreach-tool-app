"""
Email sender v68 - verified USA LED display / LED video wall batch.
Attaches the latest recent Korea projects poster.
"""
import email_sender_v58 as base

base.SUBJECT = "Recent LED Display Installations in Korea"
base.BODY_TEMPLATE = """\
Hi {name},

I'm Allen, from an LED display manufacturing factory in Shenzhen, China.

I found your LED video wall / LED screen work and wanted to share a recent reference from Korea. The attached project sheet includes indoor fine-pitch LED walls, outdoor LED screens, creative LED columns, and commercial LED installations.

If you ever need LED display panels for rental inventory, studio LED walls, outdoor LED screens, or fixed installations, I can help recommend panel options based on size, viewing distance, brightness, pixel pitch, and maintenance needs.

Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp/WeChat: +86 135-7087-1001
Email: allenma2ong@gmail.com
"""

base.TARGETS = [
    {"no": 851, "company_en": "Staging Rental NYC", "email": "info@stagingrentalnyc.com", "name": "Staging Rental NYC Team"},
    {"no": 852, "company_en": "LED Wall Masters", "email": "info@led-video-wall-rental.com", "name": "LED Wall Masters Team"},
    {"no": 853, "company_en": "Eminence AV", "email": "info@eminenceent.com", "name": "Eminence AV Team"},
    {"no": 855, "company_en": "AV Event Rental", "email": "info@aveventrental.com", "name": "AV Event Rental Team"},
    {"no": 856, "company_en": "Karana Audio Visual Services", "email": "info@karana-audiovisual.com", "name": "Karana Audio Visual Team"},
    {"no": 857, "company_en": "Nocturnal Audio Visual", "email": "Avtechray1@gmail.com", "name": "Nocturnal Audio Visual Team"},
    {"no": 858, "company_en": "Achieve AV", "email": "info@achieveav.com", "name": "Achieve AV Team"},
    {"no": 859, "company_en": "Intech Solutions Houston", "email": "info@intechsolutions.com", "name": "Intech Solutions Team"},
    {"no": 860, "company_en": "Multimedia Audio Visual", "email": "info@multimediaav.com", "name": "Multimedia Audio Visual Team"},
]

if __name__ == "__main__":
    base.main()
