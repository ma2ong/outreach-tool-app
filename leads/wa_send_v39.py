"""
WhatsApp sender v39 - verified USA LED display / LED video wall targets.
Sends the recent project image with the outreach text as the image caption.
"""
import wa_send_v29 as base

base.base.TARGETS = [
    {"no": 894, "company_en": "SOHO LED Rentals", "phone": "+1 212 431 8920", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw SOHO LED Rentals' customized LED video wall solutions in NYC. Sharing a recent Korea LED display reference. For NYC event and install projects, do clients care more about pixel pitch, fast setup, or long-term service access?"},
    {"no": 895, "company_en": "Nerotek Industries", "phone": "+1 515 599 6376", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Nerotek Industries' mobile outdoor LED wall rental work in Iowa. Sharing a recent Korea LED display reference. For mobile LED walls, is outdoor brightness, generator setup, or quick deployment usually most important?"},
    {"no": 896, "company_en": "Ultimate Occasions", "phone": "+1 443 419 4360", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Ultimate Occasions' LED video wall and event production work across the DMV. Sharing a recent Korea LED display reference. For trade shows and event LED walls, do clients ask more for high brightness or finer pixel pitch?"},
    {"no": 897, "company_en": "1st Way Pro Rental", "phone": "+1 714 487 7419", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw 1st Way Pro Rental's LED video wall and live production work in Southern California. Sharing a recent Korea LED display reference. For concert LED walls, do you focus more on touring durability, refresh rate, or fast rigging?"},
    {"no": 899, "company_en": "Mystical Entertainment Group", "phone": "+1 973 542 8068", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Mystical Entertainment Group's P3.9 LED video wall rentals for NJ and NYC events. Sharing a recent Korea LED display reference. For event walls, do clients ask more for modular size flexibility or finer indoor resolution?"},
    {"no": 900, "company_en": "PhotoTek NYC", "phone": "+1 516 582 4422", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw PhotoTek NYC's LED video wall rentals for trade shows and corporate events. Sharing a recent Korea LED display reference. For NYC trade show walls, do clients usually care more about fast setup, screen size, or close-viewing pixel pitch?"},
]

if __name__ == "__main__":
    base.base.main()
