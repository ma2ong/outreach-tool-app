"""
WhatsApp sender v31 - verified USA LED display / LED video wall targets.
Sends the recent project image with outreach text as the image caption.
"""
import wa_send_v29 as base

base.base.TARGETS = [
    {"no": 842, "company_en": "Crispy Audio", "phone": "+1 925 222 4155", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Crispy Audio's LED wall and video wall rental work in the Bay Area. Sharing a recent Korea LED display reference. For your LED wall jobs, do clients care more about fine pitch or outdoor brightness?"},
    {"no": 844, "company_en": "Las Vegas LED Walls", "phone": "+1 702 351 9986", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Las Vegas LED Walls' indoor and outdoor LED video wall rental work. Sharing a recent Korea LED display reference. For Vegas trade shows, what LED wall size or pixel pitch is requested most?"},
    {"no": 845, "company_en": "Murray Scott Production Services", "phone": "+1 602 600 2056", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw MSPS Global's LED wall rental and digital display screen rental work in Phoenix. Sharing a recent Korea LED display reference. Are your LED wall needs mainly corporate events or fixed installs?"},
    {"no": 846, "company_en": "Brightlight Film", "phone": "+1 929 300 1763", "verified": False, "country": "USA", "contact_note_prefix": "1",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Brightlight Film's curved P1.53 LED wall virtual production studio in Los Angeles. Sharing a recent Korea LED display reference. For studio LED walls, is refresh rate or panel flatness the bigger priority?"},
    {"no": 847, "company_en": "Riverside LED Video Walls", "phone": "+1 909 527 6761", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Southern California indoor/outdoor LED video wall rental and sales work. Sharing a recent Korea LED display reference. Do clients ask more for curved LED walls or standard outdoor screens?"},
    {"no": 848, "company_en": "Audio Design Rentals", "phone": "+1 619 286 4580", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Audio Design Rentals' large LED video wall panel inventory and creative LED builds in San Diego. Sharing a recent Korea LED display reference. Are your rentals mostly indoor fine-pitch or outdoor festival screens?"},
    {"no": 849, "company_en": "RCC Events", "phone": "+1 818 983 5788", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw RCC Events' LED video screen and LED video wall rental work in Los Angeles. Sharing a recent Korea LED display reference. For premieres and live events, do clients prefer modular LED walls or larger outdoor screens?"},
    {"no": 850, "company_en": "Angels Music Productions", "phone": "+1 949 394 2572", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your P3.9 and P2.6 LED screen rental work in Southern California. Sharing a recent Korea LED display reference. For LA events, do clients care more about fine pitch or quick setup?"}
]

if __name__ == "__main__":
    base.base.main()
