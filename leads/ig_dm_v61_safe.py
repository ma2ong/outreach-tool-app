"""
IG DM v61 - verified USA LED display targets only.
Follows first, sends latest case image, then sends casual DM text.
"""
import ig_dm_v58_safe as base

base.TARGETS = [
    {
        "no": 792,
        "username": "easy_audio_rental_video_walls",
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
        "username": "full.swing.pro",
        "company_en": "Full Swing Productions",
        "city": "Minneapolis, MN",
        "message": (
            "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. "
            "I saw your high-resolution LED panels, video walls and custom LED installation work. "
            "Sharing a recent Korea LED installation reference. Are your projects mostly rental walls or fixed LED installs?"
        ),
    },
    {
        "no": 795,
        "username": "livestreammedianetwork",
        "company_en": "Livestream Media Network",
        "city": "San Antonio, TX",
        "message": (
            "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. "
            "I saw your LED video wall rental and livestream production work in San Antonio. "
            "Sharing a recent Korea LED installation reference. For live events, do you use more 3.9mm rental walls or finer indoor LED walls?"
        ),
    },
    {
        "no": 796,
        "username": "ovomedia.live",
        "company_en": "OVOMEDIA Audio / Video Services",
        "city": "Central Florida",
        "message": (
            "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. "
            "I saw your 1.9 pixel LED video wall rental work in Florida. "
            "Sharing a recent Korea LED installation reference. Do your clients usually ask for fine-pitch indoor walls or larger outdoor screens?"
        ),
    },
    {
        "no": 797,
        "username": "oneway_ep",
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
