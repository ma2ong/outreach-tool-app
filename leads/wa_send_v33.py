"""
WhatsApp sender v33 - verified USA LED display / LED video wall targets.
Sends the recent project image with outreach text as the image caption.
"""
import wa_send_v29 as base

base.base.TARGETS = [
    {"no": 861, "company_en": "Beantown Audio Rentals", "phone": "+1 617 286 4757", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Beantown Audio Rentals' indoor LED video walls and outdoor LED video wall trailers in Boston. Sharing a recent Korea LED display reference. For New England events, do clients ask more for indoor fine-pitch walls or outdoor trailer screens?"},
    {"no": 862, "company_en": "A. A. Rental", "phone": "+1 703 644 1660", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw A. A. Rental's LED and LCD video wall rental work for DC, Virginia and Maryland events. Sharing a recent Korea LED display reference. Are your video wall requests mostly conferences or trade shows?"},
    {"no": 863, "company_en": "EMI Audio", "phone": "+1 612 789 2496", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw EMI Audio's CHAUVET LED video wall panel rental package in Minneapolis. Sharing a recent Korea LED display reference. For Twin Cities events, do clients need outdoor-rated panels or indoor high-resolution walls more often?"},
    {"no": 864, "company_en": "AValive", "phone": "+1 866 937 7628", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw AValive's LED video wall rental and trade show video wall category. Sharing a recent Korea LED display reference. For trade show LED walls, what pixel pitch or wall size is requested most?"},
    {"no": 865, "company_en": "Electric Events DC", "phone": "+1 301 370 1125", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Electric Events DC's LED poster rental and LED video wall poster rental work. Sharing a recent Korea LED display reference. For event signage, do clients prefer LED posters or larger modular LED walls?"},
    {"no": 866, "company_en": "Screenworks NEP", "phone": "+1 951 279 8877", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Screenworks NEP's indoor rental LED video walls, outdoor rental LED displays and mobile LED screen work. Sharing a recent Korea LED display reference. For touring and live events, do clients care more about panel weight, brightness, or fast serviceability?"},
]

if __name__ == "__main__":
    base.base.main()
