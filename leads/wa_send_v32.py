"""
WhatsApp sender v32 - verified USA LED display / LED video wall targets.
Sends the recent project image with outreach text as the image caption.
"""
import wa_send_v29 as base

base.base.TARGETS = [
    {"no": 851, "company_en": "Staging Rental NYC", "phone": "+1 212 419 0119", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Staging Rental NYC's indoor and outdoor LED video wall rental work. Sharing a recent Korea LED display reference. For NYC stage jobs, do clients ask more for fine-pitch indoor LED walls or high-brightness outdoor screens?"},
    {"no": 852, "company_en": "LED Wall Masters", "phone": "+1 646 779 2675", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw LED Wall Masters' indoor, outdoor, mobile and custom LED screen rental work in New York. Sharing a recent Korea LED display reference. Which LED wall size or pitch is requested most often?"},
    {"no": 853, "company_en": "Eminence AV", "phone": "+1 407 686 1017", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Eminence AV's Orlando LED video wall rental packages. Sharing a recent Korea LED display reference. Are your LED wall jobs mostly corporate events, churches, or trade shows?"},
    {"no": 855, "company_en": "AV Event Rental", "phone": "+1 732 547 5423", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw AV Event Rental's LED video wall service for New Jersey and the Tri-State area. Sharing a recent Korea LED display reference. For event LED walls, do clients care more about fast setup or finer pixel pitch?"},
    {"no": 856, "company_en": "Karana Audio Visual Services", "phone": "+1 281 780 5625", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Karana's LED video screens and LED video wall work in Houston. Sharing a recent Korea LED display reference. Do you use more P3.9 outdoor LED panels or finer indoor panels for your events?"},
    {"no": 857, "company_en": "Nocturnal Audio Visual", "phone": "+1 210 833 4156", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Nocturnal Audio Visual's LED video wall rental and production work in San Antonio. Sharing a recent Korea LED display reference. For live events, what LED wall size or brightness do you need most often?"},
    {"no": 858, "company_en": "Achieve AV", "phone": "+1 214 884 5951", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Achieve AV's LED video wall rental, event production and commercial AV installation work in Dallas. Sharing a recent Korea LED display reference. Are your LED wall needs more rental events or fixed installs?"},
    {"no": 859, "company_en": "Intech Solutions Houston", "phone": "+1 832 734 6518", "verified": False, "country": "USA", "contact_note_prefix": "1",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Houston LED video wall installation and rental services. Sharing a recent Korea LED display reference. For fixed LED wall projects, do clients care more about pixel pitch, front maintenance, or brightness?"},
    {"no": 860, "company_en": "Multimedia Audio Visual", "phone": "+1 303 623 2324", "verified": False, "country": "USA", "contact_note_prefix": "2",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw Multimedia Audio Visual's LED video wall rental inventory in the Denver area. Sharing a recent Korea LED display reference. Are your event LED walls mostly indoor HD panels or outdoor rental screens?"},
]

if __name__ == "__main__":
    base.base.main()
