"""
WhatsApp sender v35 - verified USA LED display / LED video wall targets.
Sends the recent project image with the outreach text as the image caption.
"""
import wa_send_v29 as base

base.base.TARGETS = [
    {"no": 872, "company_en": "Goodboy Multimedia", "phone": "+1 313 349 3234", "verified": False, "country": "USA", "contact_name": "Daniel", "contact_note_prefix": "2",
     "message": "Hi Daniel! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Goodboy Multimedia's LED wall installations and LED wall rental work in Detroit. Sharing a recent Korea LED display reference. For your event and church projects, do clients ask more for indoor fine-pitch walls or larger rental LED backdrops?"},
    {"no": 873, "company_en": "The ProMedia Group", "phone": "+1 800 881 6887", "verified": False, "country": "USA", "contact_note_prefix": "1",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw The ProMedia Group's video wall, direct-view LED and digital signage integration work in Tampa. Sharing a recent Korea LED display reference. For fixed AV projects, do clients usually care more about pixel pitch, service access, or long-term reliability?"},
    {"no": 874, "company_en": "EventFab", "phone": "+1 203 208 8909", "verified": False, "country": "USA", "contact_name": "Alex", "contact_note_prefix": "2",
     "message": "Hi Alex! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw EventFab's LED video wall and AV production work across CT, NY, MA and RI. Sharing a recent Korea LED display reference. For event video walls, do clients ask more for fast setup or higher-resolution indoor panels?"},
    {"no": 875, "company_en": "MARX entertainment", "phone": "+1 866 627 9357", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw MARX entertainment's LED wall rental and LED video wall work for Massachusetts events. Sharing a recent Korea LED display reference. For corporate events and galas, do clients usually ask for fine-pitch indoor walls or larger stage screens?"},
    {"no": 876, "company_en": "media mea", "phone": "+1 305 928 3311", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw media mea's LED rental services and full HD LED video wall options in Miami. Sharing a recent Korea LED display reference. For LED rental jobs, do clients ask more about indoor fine pitch, outdoor brightness, or fast setup?"},
]

if __name__ == "__main__":
    base.base.main()
