"""
FB DM v68 - verified USA LED display / LED video wall targets.
Likes/follows first, attempts image attachment, then sends casual DM text.
"""
import fb_dm_v58 as base

base.TARGETS = [
    {"no": 853, "facebook": "eminenceav", "company_en": "Eminence AV", "city": "Orlando, FL",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Eminence AV's Orlando LED video wall rental packages. Sharing a recent Korea LED display reference. Are your LED wall jobs mostly corporate events, churches, or trade shows?"},
    {"no": 854, "facebook": "imaginiled", "company_en": "IMAGINI", "city": "Orlando, FL",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw IMAGINI's LED video wall rental and sales work in Orlando. Sharing a recent Korea LED display reference. For Orlando jobs, are clients asking more for rental LED walls or permanent installs?"},
    {"no": 856, "facebook": "karanaAV", "company_en": "Karana Audio Visual Services", "city": "Houston, TX",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Karana's LED video screens and LED video wall work in Houston. Sharing a recent Korea LED display reference. Do you use more P3.9 outdoor LED panels or finer indoor panels for your events?"},
]

if __name__ == "__main__":
    base.main()
