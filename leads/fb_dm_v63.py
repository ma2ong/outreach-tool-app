"""
FB DM v63 - verified USA LED targets with official Facebook pages.
Follows/likes first, attempts image attachment, then sends casual DM text.
"""
import fb_dm_v58 as base

base.TARGETS = [
    {
        "no": 810,
        "facebook": "profigroupus",
        "company_en": "Profigroup",
        "city": "Seattle, WA",
        "message": (
            "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. "
            "I saw your Seattle LED screens, video walls and LED panel rental work. "
            "Sharing a recent Korea LED installation reference. For local events, do clients ask more for modular LED walls or TV/LED panel packages?"
        ),
    },
    {
        "no": 811,
        "facebook": "bigwheeldigitalmedia",
        "company_en": "Big Wheel Digital Media",
        "city": "Broken Arrow / Tulsa, OK",
        "message": (
            "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. "
            "I saw your Big LED Screens page for LED video wall screen systems. "
            "Sharing a recent Korea LED installation reference. Are your LED screen projects mostly churches/casinos or rental/touring use?"
        ),
    },
    {
        "no": 813,
        "facebook": "HBLiveInc",
        "company_en": "HB Live",
        "city": "North Haven, CT",
        "message": (
            "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. "
            "I saw your Connecticut LED wall rental page for meetings, festivals and live events. "
            "Sharing a recent Korea LED installation reference. Are your LED wall jobs mostly indoor corporate events or outdoor community/festival screens?"
        ),
    },
]

if __name__ == "__main__":
    base.main()
