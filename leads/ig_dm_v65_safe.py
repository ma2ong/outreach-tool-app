"""
IG DM v65 - verified USA LED display / mobile LED truck targets only.
Follows first, sends latest case image, then sends casual DM text.
"""
import ig_dm_v58_safe as base

base.TARGETS = [
    {"no": 827, "username": "advancedmobileled", "company_en": "Advanced Mobile LED", "city": "Pompano Beach, FL",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your custom-built mobile digital billboard fleet. Sharing a recent Korea LED display reference. For truck displays, is outdoor brightness or easier field maintenance the bigger priority?"},
    {"no": 828, "username": "unlimitedmobileled", "company_en": "Unlimited Mobile LED", "city": "Miami, FL",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Miami digital LED billboard trucks and live broadcasting capability. Sharing a recent Korea LED display reference. Do clients ask more for outdoor brightness or live-video input support?"},
    {"no": 830, "username": "luxmediaads", "company_en": "Lux Media", "city": "Dallas, TX",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your high-resolution mobile LED billboard trucks serving all 50 states. Sharing a recent Korea LED display reference. For LED trucks, do clients care more about screen brightness or fast maintenance?"},
    {"no": 831, "username": "the_billboard_guy", "company_en": "Nomadic Genius", "city": "Nashville, TN",
     "message": "Hi Regis! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your LED mobile billboard and LED billboard truck work. Sharing a recent Korea LED display reference. What LED screen size or pitch do clients request most?"},
]

if __name__ == "__main__":
    base.main()
