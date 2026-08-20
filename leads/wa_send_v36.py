"""
WhatsApp sender v36 - verified USA LED display / LED video wall targets.
Sends the recent project image with the outreach text as the image caption.
"""
import wa_send_v29 as base

base.base.TARGETS = [
    {"no": 877, "company_en": "Masato Events", "phone": "+1 929 284 5566", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Masato Events' LED video wall rental and indoor/outdoor LED wall production work in New Jersey. Sharing a recent Korea LED display reference. For event LED walls, do clients ask more for indoor fine-pitch panels or larger outdoor screens?"},
    {"no": 878, "company_en": "Radium Pictures", "phone": "+1 510 200 3409", "verified": False, "country": "USA", "contact_note_prefix": "1",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Radium Pictures' LED studio and XR LED wall work in Fremont. Sharing a recent Korea LED display reference. For XR stages, do you care more about refresh rate, color calibration, or service access?"},
    {"no": 879, "company_en": "AV Rentals NYC", "phone": "+1 888 691 4991", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw AV Rentals NYC's LED video wall rentals and event production work. Sharing a recent Korea LED display reference. For NYC rentals, do clients usually ask more for fast setup or higher-resolution indoor LED walls?"},
    {"no": 880, "company_en": "Affordable Sound Stages", "phone": "+1 818 641 0220", "verified": False, "country": "USA", "contact_name": "Vic Anthony", "contact_note_prefix": "2",
     "message": "Hi Vic! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Affordable Sound Stages' 30ft XR LED video wall and WhatsApp contact. Sharing a recent Korea LED display reference. For XR stage rentals, do you usually need replacement LED modules, spare panels, or future screen upgrades?"},
    {"no": 881, "company_en": "Interactive Vision Solutions", "phone": "+1 212 729 4305", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Interactive Vision Solutions' LED video wall rental work in NYC. Sharing a recent Korea LED display reference. For event video walls, do clients ask more for indoor fine-pitch panels or flexible screen sizes?"},
]

if __name__ == "__main__":
    base.base.main()
