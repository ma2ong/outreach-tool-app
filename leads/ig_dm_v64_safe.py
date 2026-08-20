"""
IG DM v64 - verified USA LED display / LED truck targets only.
Follows first, sends latest case image, then sends casual DM text.
"""
import ig_dm_v58_safe as base

base.TARGETS = [
    {"no": 814, "username": "trailexled_events", "company_en": "Trailex LED Event Solutions", "city": "Canfield, OH",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your FrontRow LED display trailer work in Ohio. Sharing a recent Korea LED installation reference. For LED display trailers, do customers care more about brightness, cabinet weight, or fast serviceability?"},
    {"no": 815, "username": "led3displays", "company_en": "LED3", "city": "Canfield, OH",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your LED display sales, rentals, service and mobile LED display work in Canfield. Sharing a recent Korea LED installation reference. Are your current jobs more fixed installs or rental LED displays?"},
    {"no": 816, "username": "bigscreensonthego", "company_en": "Big Screens On The Go", "city": "Fort Worth, TX",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your big screen LED display rentals and mobile LED video trailers. Sharing a recent Korea LED installation reference. Do clients usually ask for trailer screens or modular LED video walls?"},
    {"no": 819, "username": "mobilebillboardmiami", "company_en": "Mobile Billboard Miami", "city": "Hollywood / West Park, FL",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your digital LED billboard truck campaigns across South Florida. Sharing a recent Korea LED installation reference. For your LED trucks, do clients ask more for outdoor brightness or live-stream/video input capability?"},
    {"no": 820, "username": "datmediafl", "company_en": "DAT Media FL", "city": "Orlando, FL",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Orlando mobile digital LED billboard trucks. Sharing a recent Korea LED installation reference. Is pixel pitch or weatherproof cabinet durability the bigger concern?"},
    {"no": 821, "username": "ledtruckmedia", "company_en": "LED Truck Media", "city": "Canoga Park, CA",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your mobile LED billboard truck and digital outdoor media work. Sharing a recent Korea LED installation reference. Do your customers ask more for truck screen upgrades or new mobile LED display builds?"},
    {"no": 822, "username": "limemediagroupinc", "company_en": "Lime Media", "city": "Rockwall, TX",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your nationwide mobile LED billboard truck fleet and experiential campaigns. Sharing a recent Korea LED installation reference. For large LED truck fleets, do you mainly care about brightness consistency or easier field maintenance?"},
]

if __name__ == "__main__":
    base.main()
