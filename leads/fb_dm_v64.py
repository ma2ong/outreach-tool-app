"""
FB DM v64 - verified USA LED targets with official Facebook pages.
Follows/likes first, attempts image attachment, then sends casual DM text.
"""
import fb_dm_v58 as base

base.TARGETS = [
    {"no": 815, "facebook": "LED3Displays", "company_en": "LED3", "city": "Canfield, OH",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your LED display sales, rentals, service and mobile LED display work in Canfield. Sharing a recent Korea LED installation reference. Are your current jobs more fixed installs or rental LED displays?"},
    {"no": 816, "facebook": "gobigscreens", "company_en": "Big Screens On The Go", "city": "Fort Worth, TX",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your big screen LED display rentals and mobile LED video trailers. Sharing a recent Korea LED installation reference. Do clients usually ask for trailer screens or modular LED video walls?"},
    {"no": 817, "facebook": "BrandsInMotionUSA", "company_en": "Brands In Motion", "city": "Nationwide USA",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your mobile Jumbotron and LED screen advertising vehicles. Sharing a recent Korea LED installation reference. For mobile billboard fleets, what pixel pitch and brightness are most important in your market?"},
    {"no": 819, "facebook": "mobilebillboardmiami", "company_en": "Mobile Billboard Miami", "city": "Hollywood / West Park, FL",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your digital LED billboard truck campaigns across South Florida. Sharing a recent Korea LED installation reference. For your LED trucks, do clients ask more for outdoor brightness or live-stream/video input capability?"},
    {"no": 820, "facebook": "datmediafl", "company_en": "DAT Media FL", "city": "Orlando, FL",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Orlando mobile digital LED billboard trucks. Sharing a recent Korea LED installation reference. Is pixel pitch or weatherproof cabinet durability the bigger concern?"},
    {"no": 821, "facebook": "ledtruckmediaagency", "company_en": "LED Truck Media", "city": "Canoga Park, CA",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your mobile LED billboard truck and digital outdoor media work. Sharing a recent Korea LED installation reference. Do your customers ask more for truck screen upgrades or new mobile LED display builds?"},
    {"no": 823, "facebook": "runninads", "company_en": "Ad Runner Trucks", "city": "Seattle / Tacoma, WA",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your Seattle/Tacoma LED digital mobile billboard truck work. Sharing a recent Korea LED installation reference. For West Coast campaigns, do clients usually ask for higher outdoor brightness or larger screen size?"},
]

if __name__ == "__main__":
    base.main()
