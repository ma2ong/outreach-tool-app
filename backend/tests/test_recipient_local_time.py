"""对方的钟还剩下什么作用（docs/92 R3）。

`docs/65` 让收件人时区当闸门：不在当地 8–20 点不发、凌晨不发、周末不发、国家认不出来不发。
四条闸门碰上一个按深圳日期删除的队列，结果是 31 条里 24 条永远排不到自己的时刻 —— 六天
一条没发出去，而且四条闸门每一条单独看都是对的。

现在它只排序：此刻正落在对方 7–22 点的排前面，不在的排后面，**没有一条因此不发**。
这些测试守的就是「只排序、不否决」这条线。
"""
import datetime as dt

import pytest

from app import local_time as lt


def utc(y, m, d, h, mi=0):
    return dt.datetime(y, m, d, h, mi, tzinfo=dt.UTC)


@pytest.mark.parametrize("hour_utc,local,suits", [
    (13, "07:00", True),    # 开始的那一点是开着的
    (14, "08:00", True),
    (20, "14:00", True),
    (3, "21:00 (prev)", True),
    (4, "22:00 (prev)", False),   # 结束的那一点是关着的
    (12, "06:00", False),         # 早了一小时
    (8, "02:00", False),          # 人家的半夜
])
def test_the_preference_reads_their_clock(hour_utc, local, suits):
    # 2026-08-27 是周四；美国那一档是 -6。
    assert lt.suits_recipient("USA", utc(2026, 8, 27, hour_utc)) is suits, local


def test_their_weekend_ranks_last_but_still_goes():
    # 2026-08-29 是周六。按对方的日历问，不是按深圳的。
    assert lt.suits_recipient("USA", utc(2026, 8, 29, 20)) is False


def test_a_country_we_cannot_place_ranks_last():
    """docs/65 R4 反过来了：认不出国家不再是不发的理由。

    这个 False 只花掉一个排队位置。真正「发不发」的判断在 `local_time.phase()`，
    那里只看深圳的钟，根本不问国家 —— 所以一家国家为空的公司照样会发出去，
    见 test_shenzhen_clock.py::test_a_country_we_cannot_place_is_sent_too。
    """
    for country in [None, "", "Freedonia"]:
        assert lt.suits_recipient(country, utc(2026, 8, 27, 14)) is False


def test_the_preference_never_reaches_the_send_decision():
    """写死这条边界：这个模块里没有任何函数能对社媒私信说「不发」。"""
    assert not hasattr(lt, "may_send"), "对方时区不再是闸门（docs/92 R3）"
    assert not hasattr(lt, "WINDOW"), "旧的 8–20 点窗口已经换成 PREFERRED"


# ---------------------------------------------------------------- 时区表本身

def test_the_old_five_in_the_morning_is_still_recognised_as_bad():
    # 深圳 2026-08-27 17:07 是 09:07 UTC，也就是美中 03:07 —— 就是那条深夜私信。
    # 现在它不再被拦下，但它照样排在所有醒着的客户后面。
    assert lt.suits_recipient("USA", utc(2026, 8, 27, 9, 7)) is False


@pytest.mark.parametrize("country,offset", [
    ("USA", -6), ("Brazil", -3), ("South Korea", 9), ("Germany", 2), ("uae", 4),
])
def test_the_table_covers_the_countries_he_actually_works(country, offset):
    assert lt.offset_for(country) == offset


def test_an_unknown_country_has_no_local_time():
    assert lt.local_now("Freedonia", utc(2026, 8, 27, 14)) is None
