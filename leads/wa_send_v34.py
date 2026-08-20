"""
WhatsApp sender v34 - verified USA LED display / LED video wall targets.
Sends the recent project image with outreach text as the image caption.
"""
import wa_send_v29 as base

base.base.TARGETS = [
    {"no": 867, "company_en": "Metat3ch", "phone": "+1 469 232 7039", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Metat3ch's LED video wall rental, LED display and event production work. Sharing a recent Korea LED display reference. For trade shows and corporate events, do clients ask more for fine-pitch indoor walls or larger LED backdrops?"},
    {"no": 868, "company_en": "Reventals", "phone": "+1 888 857 0071", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Reventals' LED Video Wall rental listing for New Orleans and nearby cities. Sharing a recent Korea LED display reference. For rental listings, do clients usually ask for indoor LED walls or outdoor screens?"},
    {"no": 869, "company_en": "GC Event Studio", "phone": "+1 844 844 4160", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw GC Event Studio's LED Video Wall Rentals page for corporate events and brand activations. Sharing a recent Korea LED display reference. For event LED walls, do clients care more about quick setup or high-resolution panels?"},
    {"no": 870, "company_en": "Fox Audio Visual", "phone": "+1 843 608 9473", "verified": False, "country": "USA", "contact_name": "Joseph", "contact_note_prefix": "2",
     "message": "Hi Joseph! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Fox Audio Visual's LED wall rentals and mobile LED video display work in Charleston. Sharing a recent Korea LED display reference. Are your LED display needs mostly rental events or mobile LED displays?"},
    {"no": 871, "company_en": "Eciruam", "phone": "+1 702 900 9795", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Eciruam's LED video wall rental and event production work in Las Vegas. Sharing a recent Korea LED display reference. For Vegas events, do clients ask more for modular LED walls or larger stage backdrops?"},
]

if __name__ == "__main__":
    base.base.main()
