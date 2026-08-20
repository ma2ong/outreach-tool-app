"""
IG DM v62 - verified USA LED display targets only.
Follows first, sends latest case image, then sends casual DM text.
"""
import ig_dm_v58_safe as base

base.TARGETS = [
    {
        "no": 800,
        "username": "funflicksusa",
        "company_en": "FunFlicks Kentucky",
        "city": "Lexington / Louisville, KY",
        "message": (
            "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. "
            "I saw your Kentucky LED screen rental work for outdoor movies, live sports and community events. "
            "Sharing a recent Korea LED installation reference. For local events, do clients ask more for trailer LED screens or modular LED walls?"
        ),
    },
    {
        "no": 801,
        "username": "royalavsolutions",
        "company_en": "Royal AV Solutions",
        "city": "Seattle / Bellevue, WA",
        "message": (
            "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. "
            "I saw your Seattle/Pacific Northwest event AV work and LED video wall rental references. "
            "Sharing a recent Korea LED installation reference. For corporate events, do clients request more fine-pitch indoor LED or larger rental walls?"
        ),
    },
]

if __name__ == "__main__":
    base.main()
