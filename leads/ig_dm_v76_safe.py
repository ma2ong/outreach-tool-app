"""
IG DM v76 - verified USA LED display / LED video wall targets only.
Follows first, sends latest case image, then sends casual DM text.
No company name, no email-style signature - just "from Shenzhen, China".
"""
import ig_dm_v58_safe as base

base.TARGETS = [
    {
        "no": 901,
        "username": "av_vegas",
        "company_en": "AV Vegas",
        "city": "Las Vegas, NV",
        "message": (
            "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. "
            "I saw AV Vegas's modular LED video wall rentals for Vegas trade shows and conventions. "
            "Sharing a recent Korea LED display reference. For your rental fleet, do you restock more "
            "for fine-pitch indoor walls or high-brightness outdoor screens?"
        ),
    },
    {
        "no": 902,
        "username": "exhibit.experience",
        "company_en": "Exhibit Experience",
        "city": "Las Vegas, NV",
        "message": (
            "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. "
            "I saw Exhibit Experience's LED video walls for last-minute trade show setups in Vegas. "
            "Sharing a recent Korea LED display reference. For quick booth builds, do your clients care "
            "most about fast setup, panel weight, or close-viewing pixel pitch?"
        ),
    },
]

if __name__ == "__main__":
    base.main()
