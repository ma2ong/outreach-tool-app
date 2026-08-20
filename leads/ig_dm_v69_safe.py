"""
IG DM v69 - verified USA LED display / LED video wall targets only.
Follows first, sends latest case image, then sends casual DM text.
"""
import ig_dm_v58_safe as base

base.TARGETS = [
    {"no": 863, "username": "EMIAudio", "company_en": "EMI Audio", "city": "Minneapolis, MN",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your CHAUVET LED video wall panel rental package in Minneapolis. Sharing a recent Korea LED display reference. For Twin Cities events, do clients need outdoor-rated panels or indoor high-resolution walls more often?"},
    {"no": 865, "username": "electriceventsdc", "company_en": "Electric Events DC", "city": "Washington DC / MD / VA",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your LED poster rental and LED video wall poster rental work. Sharing a recent Korea LED display reference. For event signage, do clients prefer LED posters or larger modular LED walls?"},
    {"no": 866, "username": "screenworksnep", "company_en": "Screenworks NEP", "city": "Corona, CA",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your indoor rental LED video walls, outdoor rental LED displays and mobile LED screen work. Sharing a recent Korea LED display reference. For touring and live events, do clients care more about panel weight, brightness, or fast serviceability?"},
]

if __name__ == "__main__":
    base.main()
