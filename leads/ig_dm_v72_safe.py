"""
IG DM v72 - verified USA LED display / LED video wall targets only.
Follows first, sends latest case image, then sends casual DM text.
"""
import ig_dm_v58_safe as base

base.TARGETS = [
    {"no": 877, "username": "masatoevents", "company_en": "Masato Events", "city": "South Plainfield, NJ",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your LED video wall rental and indoor/outdoor LED wall production work in New Jersey. Sharing a recent Korea LED display reference. For event LED walls, do clients ask more for indoor fine-pitch panels or larger outdoor screens?"},
]

if __name__ == "__main__":
    base.main()
