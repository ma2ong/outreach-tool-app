"""
IG DM v66 - verified USA LED display / LED video wall targets only.
Follows first, sends latest case image, then sends casual DM text.
"""
import ig_dm_v58_safe as base

base.TARGETS = [
    {"no": 834, "username": "bezaleddisplays", "company_en": "BezaLED", "city": "USA",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw BezaLED's commercial LED video walls for churches, concerts, stadiums and corporate spaces. Sharing a recent Korea LED display reference. Are your projects mostly fixed installations or event/rental LED walls?"},
    {"no": 836, "username": "accessaudioinc", "company_en": "Access Audio", "city": "Cincinnati, OH",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Absen PL3.9 indoor/outdoor LED video wall rental work in Cincinnati. Sharing a recent Korea LED display reference. Are your LED wall jobs mostly church/event rentals or fixed installs?"},
    {"no": 837, "username": "eventstarts", "company_en": "EventStarts", "city": "New York, NY / Nationwide USA",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your LED wall inventory from 1.9mm to 4.8mm and custom shaped LED screens. Sharing a recent Korea LED display reference. For rental inventory, do customers ask more for fine pitch or larger outdoor screens?"},
    {"no": 838, "username": "santiagoperezproductions", "company_en": "Santiago Perez Productions", "city": "Miami / Florida",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your indoor/outdoor LED video wall rental and AV production work across Florida. Sharing a recent Korea LED display reference. For Florida events, do clients care more about outdoor brightness or camera-friendly refresh?"},
    {"no": 840, "username": "snell_audio", "company_en": "Snell Vision", "city": "Memphis, TN",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Snell Vision's LED video wall rental and sales work in Memphis. Sharing a recent Korea LED display reference. Are customers asking more for rental walls or purchase/install solutions?"},
    {"no": 841, "username": "turning_point_av", "company_en": "Turning Point AV", "city": "Savannah, GA / Nationwide USA",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Turning Point AV lists LED video wall rental and nationwide conference AV services. Sharing a recent Korea LED display reference. For conference LED walls, what size or pixel pitch do clients request most often?"},
]

if __name__ == "__main__":
    base.main()
