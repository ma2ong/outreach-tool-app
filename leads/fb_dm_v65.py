"""
FB DM v65 - verified USA LED display / mobile LED truck targets.
Likes/follows first, attempts image attachment, then sends casual DM text.
"""
import fb_dm_v58 as base

base.TARGETS = [
    {"no": 824, "facebook": "MOBILELEDBILLBOARD", "company_en": "MVS Media Group", "city": "Hallandale Beach, FL",
     "message": "Hi Alex! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw MVS Media Group's mobile LED billboard truck work across the US. Sharing a recent Korea LED display reference. For LED truck fleets, do you usually care more about outdoor brightness, easier maintenance, or panel weight?"},
    {"no": 827, "facebook": "advancedmobileled", "company_en": "Advanced Mobile LED", "city": "Pompano Beach, FL",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your custom-built mobile digital billboard fleet. Sharing a recent Korea LED display reference. For truck displays, is outdoor brightness or easier field maintenance the bigger priority?"},
    {"no": 831, "facebook": "nomadicgeniusadvertisingcompany", "company_en": "Nomadic Genius", "city": "Nashville, TN",
     "message": "Hi Regis! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your LED mobile billboard and LED billboard truck work. Sharing a recent Korea LED display reference. What LED screen size or pitch do clients request most?"},
]

if __name__ == "__main__":
    base.main()
