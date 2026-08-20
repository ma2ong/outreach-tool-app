"""
WhatsApp sender v28 - verified USA LED display / LED truck targets.
Reuses the v27 sender and swaps in the current batch.
"""
import wa_send_v27 as base

base.TARGETS = [
    {"no": 814, "company_en": "Trailex LED Event Solutions", "phone": "+1 330 207 0818", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your FrontRow LED display trailer work in Ohio and wanted to share a recent Korea LED installation reference. For LED display trailers, do customers care more about brightness, cabinet weight, or fast serviceability?"},
    {"no": 815, "company_en": "LED3", "phone": "+1 330 533 6988", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your LED display sales, rentals, service and mobile LED display work in Canfield. Sharing a recent Korea LED installation reference. Are your current jobs more fixed installs or rental LED displays?"},
    {"no": 816, "company_en": "Big Screens On The Go", "phone": "+1 888 830 8011", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your big screen LED display rentals and mobile LED video trailers. Sharing a recent Korea LED installation reference. For Jumbotron rental work, do clients usually ask for trailer screens or modular LED video walls?"},
    {"no": 817, "company_en": "Brands In Motion", "phone": "+1 888 708 5558", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your mobile Jumbotron and LED screen advertising vehicles. Sharing a recent Korea LED installation reference. For mobile billboard fleets, what pixel pitch and brightness are most important in your market?"},
    {"no": 818, "company_en": "Rolling Outdoor Media", "phone": "+1 818 452 6526", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your mobile billboard vehicles with high-resolution LED display screens. Sharing a recent Korea LED installation reference. Are your truck displays usually upgraded by module/panel replacement or full screen replacement?"},
    {"no": 819, "company_en": "Mobile Billboard Miami", "phone": "+1 305 814 5880", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your digital LED billboard truck campaigns across South Florida. Sharing a recent Korea LED installation reference. For your LED trucks, do clients ask more for outdoor brightness or live-stream/video input capability?"},
    {"no": 820, "company_en": "DAT Media FL", "phone": "+1 407 559 7065", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Orlando mobile digital LED billboard trucks. Sharing a recent Korea LED installation reference. For your trucks, is pixel pitch or weatherproof cabinet durability the bigger concern?"},
    {"no": 821, "company_en": "LED Truck Media", "phone": "+1 917 224 3633", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your mobile LED billboard truck and digital outdoor media work. Sharing a recent Korea LED installation reference. Do your customers ask more for truck screen upgrades or new mobile LED display builds?"},
    {"no": 822, "company_en": "Lime Media", "phone": "+1 972 475 1200", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your nationwide mobile LED billboard truck fleet and experiential campaigns. Sharing a recent Korea LED installation reference. For large LED truck fleets, do you mainly care about brightness consistency or easier field maintenance?"},
    {"no": 823, "company_en": "Ad Runner Trucks", "phone": "+1 253 350 0804", "verified": False,
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Seattle/Tacoma LED digital mobile billboard truck work. Sharing a recent Korea LED installation reference. For West Coast campaigns, do clients usually ask for higher outdoor brightness or larger screen size?"},
]

if __name__ == "__main__":
    base.main()
