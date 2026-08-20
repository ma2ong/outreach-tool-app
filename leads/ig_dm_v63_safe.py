"""
IG DM v63 - verified USA LED display targets only.
Follows first, sends latest case image, then sends casual DM text.
"""
import ig_dm_v58_safe as base

base.TARGETS = [
    {
        "no": 810,
        "username": "profigroupus",
        "company_en": "Profigroup",
        "city": "Seattle, WA",
        "message": (
            "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. "
            "I saw your Seattle LED screens, video walls and LED panel rental work. "
            "Sharing a recent Korea LED installation reference. For local events, do clients ask more for modular LED walls or TV/LED panel packages?"
        ),
    },
    {
        "no": 813,
        "username": "hbliveinc",
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
