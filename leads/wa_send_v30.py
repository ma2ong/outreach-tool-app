"""
WhatsApp sender v30 - verified USA LED display / LED video wall targets.
Sends the recent project image with outreach text as the image caption.
"""
import wa_send_v29 as base

base.base.TARGETS = [
    {"no": 833, "company_en": "Titan Production Group", "phone": "+1 844 544 3786", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Titan Production Group's P2.6mm LED wall rental work across Atlanta and the Southeast. Sharing a recent Korea LED display reference. For your LED wall rentals, do clients care more about outdoor brightness or fast setup/maintenance?"},
    {"no": 834, "company_en": "BezaLED", "phone": "+1 786 826 7016", "verified": False, "country": "USA", "contact_note_prefix": "1",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw BezaLED's commercial LED video walls for churches, concerts, stadiums and corporate spaces. Sharing a recent Korea LED display reference. Are your projects mostly fixed installations or event/rental LED walls?"},
    {"no": 835, "company_en": "Event Technology Rentals (Rentipads)", "phone": "+1 866 840 1472", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your nationwide LED video wall rental and modular LED tile rental services. Sharing a recent Korea LED display reference. For trade show rentals, what pixel pitch or screen size is requested most?"},
    {"no": 836, "company_en": "Access Audio", "phone": "+1 513 771 1500", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Access Audio's Absen PL3.9 indoor/outdoor LED video wall rental work in Cincinnati. Sharing a recent Korea LED display reference. Are your LED wall jobs mostly church/event rentals or fixed installs?"},
    {"no": 837, "company_en": "EventStarts", "phone": "+1 800 231 3132", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw EventStarts' LED wall inventory from 1.9mm to 4.8mm and custom shaped LED screens. Sharing a recent Korea LED display reference. For your rental inventory, do customers ask more for fine pitch or larger outdoor screens?"},
    {"no": 838, "company_en": "Santiago Perez Productions", "phone": "+1 305 780 9409", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your indoor/outdoor LED video wall rental and AV production work across Florida. Sharing a recent Korea LED display reference. For Florida events, do clients care more about outdoor brightness or camera-friendly refresh?"},
    {"no": 839, "company_en": "Dionysus Creative", "phone": "+1 951 264 8339", "verified": False, "country": "USA", "contact_note_prefix": "1",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Dionysus Creative's LED wall integration, rental and permanent installation work across NM, LA and North Bay. Sharing a recent Korea LED display reference. Are your projects currently more rental deployments or permanent installs?"},
    {"no": 840, "company_en": "Snell Vision", "phone": "+1 833 763 5563", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Snell Vision's LED video wall rental and sales work in Memphis. Sharing a recent Korea LED display reference. For your LED screen projects, do clients ask more for rental walls or purchase/install solutions?"},
    {"no": 841, "company_en": "Turning Point AV", "phone": "+1 855 487 2811", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Turning Point AV lists LED video wall rental and nationwide conference AV services. Sharing a recent Korea LED display reference. For conference LED walls, what size or pixel pitch do clients request most often?"},
]

if __name__ == "__main__":
    base.base.main()
