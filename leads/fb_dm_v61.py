"""
FB DM v61 - verified USA LED targets with official Facebook pages.
Follows/likes first, attempts image attachment, then sends casual DM text.
"""
import fb_dm_v58 as base

base.TARGETS = [
    {
        "no": 792,
        "facebook": "easyaudiorental",
        "company_en": "Easy Audio Rental",
        "city": "Kansas City, KS",
        "message": (
            "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. "
            "I saw your Kansas City LED video wall rental work and wanted to share a recent Korea LED installation reference. "
            "For KC events, do clients ask more for turn-key 12ft LED walls or larger custom video walls?"
        ),
    },
    {
        "no": 793,
        "facebook": "61556137492975",
        "company_en": "Full Swing Productions",
        "city": "Minneapolis, MN",
        "message": (
            "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. "
            "I saw your LED panels, video walls and digital signage work. "
            "Sharing a recent Korea LED installation reference. Are your projects mostly rental walls or fixed LED installs?"
        ),
    },
    {
        "no": 795,
        "facebook": "livestreammedianetwork",
        "company_en": "Livestream Media Network",
        "city": "San Antonio, TX",
        "message": (
            "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. "
            "I saw your LED video wall rental and livestream production work in San Antonio. "
            "Sharing a recent Korea LED installation reference. For live events, do you use more 3.9mm rental walls or finer indoor LED walls?"
        ),
    },
    {
        "no": 797,
        "facebook": "1wayav",
        "company_en": "One Way Event Productions",
        "city": "New York, NY",
        "message": (
            "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. "
            "I saw your NYC LED video wall and LED rental work. "
            "Sharing a recent Korea LED installation reference. For corporate events, what pixel pitch or cabinet size do clients request most?"
        ),
    },
]

if __name__ == "__main__":
    base.main()
