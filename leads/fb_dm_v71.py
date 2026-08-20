"""
FB DM v71 - verified USA LED display / LED video wall targets.
Likes/follows first, attempts image attachment, then sends casual DM text.
"""
import fb_dm_v58 as base

base.TARGETS = [
    {"no": 874, "facebook": "eventfab", "company_en": "EventFab", "city": "Waterbury, CT / New York, NY",
     "message": "Hi Alex! I'm Allen, from an LED display manufacturing factory in Shenzhen, China. I saw EventFab's LED video wall and AV production work across CT, NY, MA and RI. Sharing a recent Korea LED display reference. For event video walls, do clients ask more for fast setup or higher-resolution indoor panels?"},
]

if __name__ == "__main__":
    base.main()
