"""
IG DM v71 - verified USA LED display / LED video wall targets only.
Follows first, sends latest case image, then sends casual DM text.
"""
import ig_dm_v58_safe as base

base.TARGETS = [
    {"no": 873, "username": "thepromediagroup", "company_en": "The ProMedia Group", "city": "Tampa, FL",
     "message": "Hi! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw your video wall, direct-view LED and digital signage integration work in Tampa. Sharing a recent Korea LED display reference. For fixed AV projects, do clients usually care more about pixel pitch, service access, or long-term reliability?"},
    {"no": 874, "username": "eventfab.pro", "company_en": "EventFab", "city": "Waterbury, CT / New York, NY",
     "message": "Hi Alex! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw EventFab's LED video wall and AV production work across CT, NY, MA and RI. Sharing a recent Korea LED display reference. For event video walls, do clients ask more for fast setup or higher-resolution indoor panels?"},
]

if __name__ == "__main__":
    base.main()
