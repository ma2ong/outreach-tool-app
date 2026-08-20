"""
WhatsApp sender v37 - verified USA LED display / LED video wall targets.
Sends the recent project image with the outreach text as the image caption.
"""
import wa_send_v29 as base

base.base.TARGETS = [
    {"no": 882, "company_en": "Lead Innovations", "phone": "+1 402 809 7502", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Lead Innovations' LED trailer and outdoor LED video wall rental work in Omaha. Sharing a recent Korea LED display reference. For outdoor LED trailer jobs, do clients care more about brightness, fast setup, or screen size?"},
    {"no": 883, "company_en": "Lehigh Valley Events & Productions", "phone": "+1 610 390 2861", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Lehigh Valley Events & Productions' LED walls for events and AV production work in Pennsylvania. Sharing a recent Korea LED display reference. For local event LED walls, do clients usually ask more for indoor fine-pitch or larger outdoor screens?"},
    {"no": 884, "company_en": "American Movie Company", "phone": "+1 212 219 1075", "verified": False, "country": "USA", "contact_note_prefix": "1",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw American Movie Company's XR LED wall studio and 27ft LED video wall in Brooklyn. Sharing a recent Korea LED display reference. For virtual production, do you care more about refresh rate, color calibration, or service access?"},
    {"no": 885, "company_en": "SOFLO Main Events", "phone": "+1 305 714 0402", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw SOFLO Main Events' LED video wall and event production work in South Florida. Sharing a recent Korea LED display reference. For Miami events, do clients ask more for fast-rig rental walls or higher-resolution indoor LED panels?"},
    {"no": 886, "company_en": "Pure AV", "phone": "+1 800 929 7089", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Pure AV's LED/LCD video wall rentals and 2mm/4mm/7mm LED panel options in Las Vegas. Sharing a recent Korea LED display reference. For trade shows, do clients care more about pixel pitch, fast setup, or spare panel support?"},
    {"no": 887, "company_en": "Digital Sign Distributors", "phone": "+1 813 547 5008", "verified": False, "country": "USA", "contact_note_prefix": "1",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Digital Sign Distributors' indoor LED displays, outdoor LED billboards and video wall systems in Florida. Sharing a recent Korea LED display reference. For fixed LED sign projects, do customers ask more about brightness, easy installation, or long-term maintenance?"},
    {"no": 888, "company_en": "DVS LED Systems", "phone": "+1 813 563 8005", "verified": False, "country": "USA", "contact_note_prefix": "1",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw DVS LED Systems' direct-view LED video wall panels and showroom in Florida. Sharing a recent Korea LED display reference. For LED system projects, is pixel pitch, service access, or controller compatibility usually the biggest concern?"},
]

if __name__ == "__main__":
    base.base.main()
