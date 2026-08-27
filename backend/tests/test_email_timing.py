"""When an email may go out (docs/66).

Not a copy of docs/65. A DM lights up a phone; an email waits in an inbox. The costs are
different, so the rules are different, and matching them for the sake of symmetry would
make one of them wrong.
"""
import datetime as dt

import pytest

from app import local_time as lt


def utc(y, m, d, h, mi=0):
    return dt.datetime(y, m, d, h, mi, tzinfo=dt.UTC)


def test_email_is_allowed_later_in_their_evening_than_a_dm():
    # 22:00 US Central. A letter then sits at the top of the pile next morning; a DM
    # then is an interruption.
    evening = utc(2026, 8, 27, 4)
    assert lt.may_email("USA", evening)[0] is True
    assert lt.may_send("USA", evening)[0] is False


def test_email_is_allowed_earlier_in_their_morning_than_a_dm():
    morning = utc(2026, 8, 27, 13)   # 07:00 US Central
    assert lt.may_email("USA", morning)[0] is True
    assert lt.may_send("USA", morning)[0] is False


@pytest.mark.parametrize("hour_utc", [6, 8, 10, 11])   # 00:00–05:00 US Central
def test_the_small_hours_are_closed_for_email_too(hour_utc):
    allowed, why = lt.may_email("USA", utc(2026, 8, 27, hour_utc))
    assert allowed is False
    assert "凌晨" in why


def test_an_unknown_country_still_gets_email():
    # The opposite of the DM rule, on purpose: guessing wrong here costs "it arrived
    # after they left", which is email's normal condition.
    for country in [None, "", "Freedonia"]:
        assert lt.may_email(country, utc(2026, 8, 27, 14))[0] is True
        assert lt.may_send(country, utc(2026, 8, 27, 14))[0] is False


def test_the_windows_intersect_where_the_spec_says_they_do():
    """Shenzhen morning reaches the US the evening before, which is the point."""
    from app.autosend import WINDOW as HIS_WINDOW

    reachable = []
    for shenzhen_hour in range(24):
        moment = utc(2026, 8, 27, (shenzhen_hour - 8) % 24)
        if not (HIS_WINDOW[0] <= shenzhen_hour < HIS_WINDOW[1]):
            continue
        if lt.may_email("USA", moment)[0]:
            reachable.append(shenzhen_hour)
    assert 9 in reachable and 12 in reachable
    assert 18 not in reachable      # 04:00 for them
