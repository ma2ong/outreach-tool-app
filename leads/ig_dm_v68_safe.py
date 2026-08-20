"""
IG DM v68 - verified USA LED display / LED video wall targets only.
Follows first, sends latest case image, then sends casual DM text.
"""
import ig_dm_v58_safe as base

base.TARGETS = [
    {"no": 854, "username": "imaginiled", "company_en": "IMAGINI", "city": "Orlando, FL",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw IMAGINI's LED video wall rental and sales work in Orlando. Sharing a recent Korea LED display reference. For Orlando jobs, are clients asking more for rental LED walls or permanent installs?"},
    {"no": 856, "username": "karana.audiovisual", "company_en": "Karana Audio Visual Services", "city": "Houston, TX",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your LED video screens and LED video wall work in Houston. Sharing a recent Korea LED display reference. Do you use more P3.9 outdoor LED panels or finer indoor panels for your events?"},
]

if __name__ == "__main__":
    base.main()
