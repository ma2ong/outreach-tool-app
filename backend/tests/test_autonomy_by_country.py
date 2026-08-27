"""Korea waits for Allen; the rest can go on their own (docs/63).

docs/53 put the send decision on the channel, because the risk it guards is account
level. This adds the other risk: 176 of the 303 Korean companies carry tags Allen typed
himself and some are marked 成交客户. An automatic opener to a stranger costs nothing when
ignored. The same opener to a customer of several years reads as bulk mail.

The direction of the override is the thing worth protecting: a country may hold a send
back, never push one forward, or the typed confirmation docs/53 requires would be
reachable without typing it.
"""
import datetime as dt

import pytest

from app import social_autonomy as sa
from app.db import connect, init_schema


@pytest.mark.parametrize("country", ["South Korea", "KR", "korea", "  south korea  "])
def test_korea_is_held_back(country):
    assert sa.effective_mode("auto", country) == "manual"


@pytest.mark.parametrize("country", ["USA", "Brazil", "Mexico", "Canada"])
def test_other_countries_follow_the_channel(country):
    assert sa.effective_mode("auto", country) == "auto"


@pytest.mark.parametrize("country", [None, "", "   "])
def test_a_missing_country_follows_the_channel(country):
    # Blanks are unread pages, not Korea. Making him confirm a pile of American leads
    # turns confirmation into reflex clicking, and reflex clicking stops nothing.
    assert sa.effective_mode("auto", country) == "auto"


def test_a_country_can_never_raise_a_channel():
    # The whole point: no country setting may reach `auto` on a channel Allen left at
    # manual, or docs/53's typed confirmation is reachable without typing it.
    for country in ["USA", "South Korea", None, "Brazil"]:
        assert sa.effective_mode("manual", country) in ("manual", "off")
        assert sa.effective_mode("off", country) == "off"


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    from app import social_queue
    social_queue.ensure_schema(c)
    today = "2026-08-27"
    c.executescript(f"""
        INSERT INTO leads(no, company_en, country, phone, instagram) VALUES
            (1, 'Atlanta Pro AV', 'USA', '+14048352230', NULL),
            (2, 'Kinoton Korea', 'South Korea', '+82269231900', NULL),
            (3, 'Nowhere Co', NULL, '+5511304446090', NULL);
        INSERT INTO social_dm_queue(queue_date, lead_no, channel, target, body,
                                    rank_order, status, created_at)
        VALUES
            ('{today}', 1, 'whatsapp', '14048352230', 'Hi Atlanta', 1, 'ready', '{today}'),
            ('{today}', 2, 'whatsapp', '82269231900', 'Hi Kinoton', 2, 'ready', '{today}'),
            ('{today}', 3, 'whatsapp', '5511304446090', 'Hi Nowhere', 3, 'ready', '{today}');
    """)
    c.commit()
    return c


def _walk_a_day(conn, day: dt.date):
    """Run the loop across the day and the one after it, the way the real cycle does.

    Two days because a customer's afternoon can fall after UTC midnight — that is the
    whole reason run_due also looks at yesterday's queue (docs/65).
    """
    start = dt.datetime.combine(day, dt.time(0, 0), tzinfo=dt.UTC)
    for minute in range(0, 48 * 60, 10):
        sa.run_due(conn, now=start + dt.timedelta(minutes=minute))


def test_the_automatic_run_skips_korea_but_sends_the_rest(conn, monkeypatch):
    sa.set_mode(conn, "whatsapp", "auto", confirm="whatsapp")
    sent: list[dict] = []
    monkeypatch.setattr(sa, "_deliver",
                        lambda c, items: sent.extend(items) or {"sent": len(items)})

    _walk_a_day(conn, dt.date(2026, 8, 27))   # a Thursday everywhere that matters
    # #2 is Korean (held for Allen) and #3 has no country, so neither goes on its own.
    assert {i["lead_no"] for i in sent} == {1}


def test_the_korean_row_stays_in_the_queue_for_him(conn, monkeypatch):
    sa.set_mode(conn, "whatsapp", "auto", confirm="whatsapp")
    monkeypatch.setattr(sa, "_deliver", lambda c, items: {"sent": len(items)})

    _walk_a_day(conn, dt.date(2026, 8, 27))
    still = conn.execute(
        "SELECT status FROM social_dm_queue WHERE lead_no=2").fetchone()[0]
    assert still == "ready"


def test_turning_a_channel_on_still_needs_the_typed_name(conn):
    with pytest.raises(sa.ConfirmationRequired):
        sa.set_mode(conn, "whatsapp", "auto")
