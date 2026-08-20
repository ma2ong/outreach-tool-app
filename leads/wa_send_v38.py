"""
WhatsApp sender v38 - verified USA LED display / LED video wall targets.
Sends the recent project image with the outreach text as the image caption.
"""
import wa_send_v29 as base

base.base.TARGETS = [
    {"no": 889, "company_en": "Iowa Media", "phone": "+1 319 290 1644", "verified": False, "country": "USA", "contact_name": "Matt", "contact_note_prefix": "2",
     "message": "Hi Matt! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Iowa Media's LED video wall rentals and installs in Waterloo. Sharing a recent Korea LED display reference. For Iowa events, do clients ask more for indoor fine-pitch walls or outdoor high-brightness screens?"},
    {"no": 890, "company_en": "Assorted Studios", "phone": "+1 717 916 3050", "verified": False, "country": "USA", "contact_name": "Jesse", "contact_note_prefix": "2",
     "message": "Hi Jesse! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Assorted Studios' LED screen and video wall rentals around Harrisburg. Sharing a recent Korea LED display reference. For Mid-Atlantic rentals, do clients care more about fast setup, brightness, or spare panel support?"},
    {"no": 891, "company_en": "Blue Sky Productions", "phone": "+1 319 214 0460", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Blue Sky Productions' LED video wall and projection system rentals in Iowa. Sharing a recent Korea LED display reference. For rentals, do clients usually ask more for flexible wall size or higher-resolution indoor panels?"},
    {"no": 892, "company_en": "Crescent Event Productions", "phone": "+1 800 579 2737", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Crescent Event Productions' LED wall systems and event production work across Nashville, Charlotte and Atlanta. Sharing a recent Korea LED display reference. For LED wall rentals, is pixel pitch, rigging weight, or service access usually the bigger concern?"},
    {"no": 893, "company_en": "L/A Music Productions", "phone": "+1 207 783 0058", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw L/A Music Productions' LED video wall rentals and permanent LED installs in Maine. Sharing a recent Korea LED display reference. For concerts and school/business events, do clients ask more for outdoor brightness or easy modular setup?"},
]

if __name__ == "__main__":
    base.base.main()
