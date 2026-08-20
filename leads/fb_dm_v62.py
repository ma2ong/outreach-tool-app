"""
FB DM v62 - verified USA LED targets with official Facebook pages.
Follows/likes first, attempts image attachment, then sends casual DM text.
"""
import fb_dm_v58 as base

base.TARGETS = [
    {
        "no": 799,
        "facebook": "ledtrucks",
        "company_en": "Legion LED Trucks",
        "city": "Bellevue, NE",
        "message": (
            "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. "
            "I saw your Legion LED truck and mobile billboard trailer work. "
            "Sharing a recent Korea LED installation reference. For LED trucks, what pixel pitch and cabinet serviceability do your buyers care about most?"
        ),
    },
    {
        "no": 800,
        "facebook": "funflicks",
        "company_en": "FunFlicks Kentucky",
        "city": "Lexington / Louisville, KY",
        "message": (
            "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. "
            "I saw your Kentucky LED screen rental work for outdoor movies and live sports. "
            "Sharing a recent Korea LED installation reference. Do clients usually ask for trailer LED screens or modular LED walls?"
        ),
    },
    {
        "no": 801,
        "facebook": "royalavsolutions",
        "company_en": "Royal AV Solutions",
        "city": "Seattle / Bellevue, WA",
        "message": (
            "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. "
            "I saw your Seattle/Pacific Northwest event AV work and LED video wall rental references. "
            "Sharing a recent Korea LED installation reference. For corporate events, do clients request more fine-pitch indoor LED or larger rental walls?"
        ),
    },
    {
        "no": 802,
        "facebook": "GameCrazeParty",
        "company_en": "Game Craze Party Rentals",
        "city": "Northeast Ohio",
        "message": (
            "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. "
            "I saw your Northeast Ohio LED video wall rental page with 14ft x 8ft LED walls. "
            "Sharing a recent Korea LED installation reference. Are your LED wall jobs mostly schools/churches or corporate events?"
        ),
    },
]

if __name__ == "__main__":
    base.main()
