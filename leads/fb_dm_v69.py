"""
FB DM v69 - verified USA LED display / LED video wall targets.
Likes/follows first, attempts image attachment, then sends casual DM text.
"""
import fb_dm_v58 as base

base.TARGETS = [
    {"no": 863, "facebook": "EMIAUDIO", "company_en": "EMI Audio", "city": "Minneapolis, MN",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw EMI Audio's CHAUVET LED video wall panel rental package in Minneapolis. Sharing a recent Korea LED display reference. For Twin Cities events, do clients need outdoor-rated panels or indoor high-resolution walls more often?"},
    {"no": 864, "facebook": "AValive", "company_en": "AValive", "city": "Nationwide USA",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw AValive's LED video wall rental and trade show video wall category. Sharing a recent Korea LED display reference. For trade show LED walls, what pixel pitch or wall size is requested most?"},
    {"no": 865, "facebook": "electriceventsdc", "company_en": "Electric Events DC", "city": "Washington DC / MD / VA",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your LED poster rental and LED video wall poster rental work. Sharing a recent Korea LED display reference. For event signage, do clients prefer LED posters or larger modular LED walls?"},
    {"no": 866, "facebook": "NEPGroupInc", "company_en": "Screenworks NEP", "city": "Corona, CA",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Screenworks NEP's indoor rental LED video walls, outdoor rental LED displays and mobile LED screen work. Sharing a recent Korea LED display reference. For touring and live events, do clients care more about panel weight, brightness, or fast serviceability?"},
]

if __name__ == "__main__":
    base.main()
