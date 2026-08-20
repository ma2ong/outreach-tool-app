"""
IG DM v77 - verified USA LED display / AV integrator targets only.
Follows first, sends latest case image, then sends casual DM text.
No company name, no email-style signature - just "from Shenzhen, China".
"""
import ig_dm_v58_safe as base

base.TARGETS = [
    {
        "no": 905,
        "username": "infiniteavsolutions",
        "company_en": "Infinite AV Solutions",
        "city": "Little Silver, NJ",
        "message": (
            "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. "
            "I saw Infinite AV Solutions' LED video wall and AV integration work in New Jersey. "
            "Sharing a recent Korea LED display reference. For your fixed installs, do clients ask "
            "more for indoor fine-pitch walls or outdoor high-brightness screens?"
        ),
    },
    {
        "no": 908,
        "username": "procorela",
        "company_en": "ProCore Productions",
        "city": "Los Angeles, CA",
        "message": (
            "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. "
            "I saw ProCore's LED wall rentals for LA events and productions. "
            "Sharing a recent Korea LED display reference. For your rental inventory, do you restock "
            "more for fine-pitch indoor walls or outdoor high-brightness panels?"
        ),
    },
    {
        "no": 909,
        "username": "crunchy_tech",
        "company_en": "Crunchy Tech",
        "city": "Orlando, FL",
        "message": (
            "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. "
            "I saw Crunchy Tech's LED video wall equipment and installs in Orlando. "
            "Sharing a recent Korea LED display reference. For your projects, do clients care most "
            "about pixel pitch, brightness, or service access for repairs?"
        ),
    },
    {
        "no": 907,
        "username": "light.it.up.av.and.turf",
        "company_en": "Light It Up AV & Turf",
        "city": "Fort Worth, TX",
        "message": (
            "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. "
            "I saw Light It Up's LED video display installs around DFW. "
            "Sharing a recent Korea LED display reference. For your installs, do you go more for "
            "indoor fine-pitch walls or outdoor high-brightness screens?"
        ),
    },
]

if __name__ == "__main__":
    base.main()
