"""
IG DM v70 - verified USA LED display / LED video wall targets only.
Follows first, sends latest case image, then sends casual DM text.
"""
import ig_dm_v58_safe as base

base.TARGETS = [
    {"no": 868, "username": "reventals", "company_en": "Reventals", "city": "New Orleans / Nationwide USA",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your LED Video Wall rental listing for New Orleans and nearby cities. Sharing a recent Korea LED display reference. For rental listings, do clients usually ask for indoor LED walls or outdoor screens?"},
]

if __name__ == "__main__":
    base.main()
