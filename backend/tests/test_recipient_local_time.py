"""Send when it is daytime where the customer is (docs/65).

The queue went out at one moment a day, picked in Shenzhen time. For the 432 American
companies in the book that moment was 05:07 their time — a phone lighting up on a
bedside table, which settles the first impression before anyone reads a word.

These tests hold the two rules that cannot bend: never in their small hours, and never
on their weekend.
"""
import datetime as dt

import pytest

from app import local_time as lt


def utc(y, m, d, h, mi=0):
    return dt.datetime(y, m, d, h, mi, tzinfo=dt.UTC)


def test_the_old_send_moment_would_have_been_five_in_the_morning():
    # Shenzhen 17:07 on 2026-08-27 is 09:07 UTC, which is 03:07 US Central.
    allowed, why = lt.may_send("USA", utc(2026, 8, 27, 9, 7))
    assert allowed is False
    assert "凌晨" in why


@pytest.mark.parametrize("hour_utc,local,allowed", [
    (14, "08:00", True),    # the start of their day
    (20, "14:00", True),
    (1, "19:00 (prev)", True),   # still their evening
    (2, "20:00 (prev)", False),  # 20:00 is the edge, and the edge is closed
    (13, "07:00", False),        # an hour too early
])
def test_the_window_follows_their_clock(hour_utc, local, allowed):
    # 2026-08-27 is a Thursday; the US entry is -6.
    got, _ = lt.may_send("USA", utc(2026, 8, 27, hour_utc))
    assert got is allowed, local


@pytest.mark.parametrize("country,hour_utc", [
    ("USA", 8),          # 02:00 Central
    ("Germany", 3),      # 05:00 CEST
    ("South Korea", 19),  # 04:00 next day KST
])
def test_the_small_hours_are_never_open(country, hour_utc):
    allowed, why = lt.may_send(country, utc(2026, 8, 27, hour_utc))
    assert allowed is False
    assert "凌晨" in why


def test_their_saturday_is_closed_even_when_it_is_friday_here():
    # 2026-08-29 is a Saturday. 06:00 UTC is Saturday 00:00 US Central and already
    # Saturday afternoon in Shenzhen — the point is that we ask their calendar.
    allowed, why = lt.may_send("USA", utc(2026, 8, 29, 20))
    assert allowed is False
    assert "周末" in why


def test_our_sunday_morning_is_their_saturday_night_and_both_are_closed():
    # Shenzhen Sunday 09:00 = 01:00 UTC Sunday = Saturday 19:00 US Central.
    allowed, _ = lt.may_send("USA", utc(2026, 8, 30, 1))
    assert allowed is False


def test_a_country_we_cannot_place_is_never_sent_automatically():
    # Guessing a timezone from an area code costs a midnight interruption when wrong,
    # and saves one click when right.
    for country in [None, "", "Freedonia"]:
        allowed, why = lt.may_send(country, utc(2026, 8, 27, 14))
        assert allowed is False
        assert "国家未知" in why


def test_each_message_gets_its_own_moment():
    day = dt.date(2026, 8, 27)
    moments = {lt.send_minute(no, day, "USA") for no in range(1, 30)}
    # 23 messages leaving in the same minute is the least human thing the sender does.
    assert len(moments) > 15


def test_a_message_moment_lands_inside_their_working_day():
    day = dt.date(2026, 8, 27)
    for no in range(1, 40):
        due = lt.send_minute(no, day, "Brazil")
        local = due + dt.timedelta(hours=lt.offset_for("Brazil"))
        assert lt.WINDOW[0] <= local.hour < lt.WINDOW[1]


def test_the_moment_is_stable_for_the_same_lead_and_day():
    # The cycle runs every five minutes; a moment that moved each time would either
    # never arrive or fire twice.
    a = lt.send_minute(7, dt.date(2026, 8, 27), "USA")
    b = lt.send_minute(7, dt.date(2026, 8, 27), "USA")
    assert a == b


def test_a_country_with_no_offset_has_no_moment():
    assert lt.send_minute(1, dt.date(2026, 8, 27), "Freedonia") is None
