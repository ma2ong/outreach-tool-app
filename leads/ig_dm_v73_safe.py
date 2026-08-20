"""
IG DM v73 - verified USA LED display / LED video wall targets only.
Follows first, sends latest case image, then sends casual DM text.
"""
import ig_dm_v58_safe as base

base.TARGETS = [
    {"no": 885, "username": "soflomainevents", "company_en": "SOFLO Main Events", "city": "Hialeah, FL",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Miami event production work and the LED video wall listed on your site. Sharing a recent Korea LED display reference. For larger South Florida events, do clients ask more for indoor fine-pitch LED or bigger outdoor LED screens?"},
]

if __name__ == "__main__":
    base.main()
