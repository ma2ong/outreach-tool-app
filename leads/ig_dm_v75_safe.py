"""
IG DM v75 - verified USA LED display / LED video wall target only.
Follows first, sends latest case image, then sends casual DM text.
"""
import ig_dm_v58_safe as base

base.TARGETS = [
    {
        "no": 900,
        "username": "phototeknyc",
        "company_en": "PhotoTek NYC",
        "city": "New York, NY",
        "message": (
            "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. "
            "I saw PhotoTek NYC's LED video wall rentals for trade shows and corporate events. "
            "Sharing a recent Korea LED display reference. For NYC trade show walls, do clients "
            "usually care more about fast setup, screen size, or close-viewing pixel pitch?"
        ),
    },
]

if __name__ == "__main__":
    base.main()
