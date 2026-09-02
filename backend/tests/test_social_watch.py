"""Reading social profiles, carefully (docs/71).

Allen's correction is why this exists: a company's website can go three years without an
edit while its Instagram still has last week's show on it. What changes, changes there.

Every limit tested here is about keeping the account rather than about manners. docs/53
already established the cost — a banned Instagram does not come back, and the WhatsApp
number carries WeChat and every customer contact.
"""
import datetime as dt

import pytest

from app import relationship_events as events
from app import social_watch as watch
from app.db import connect, init_schema


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    from app import social_queue
    social_queue.ensure_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, instagram, facebook) VALUES
            (1, 'Verum AV', 'USA', 'verumav', NULL),
            (2, 'Kinoton', 'South Korea', NULL, 'kinotonkorea'),
            (3, 'No Social', 'USA', NULL, NULL);
    """)
    c.commit()
    return c


class FakeEngine:
    def __init__(self, pages=None, fail=(), follow_fails=False):
        self.pages = pages or {}
        self.fail = set(fail)
        self.follow_fails = follow_fails
        self.seen: list[str] = []
        self.followed: list[str] = []

    def read_profile(self, channel, handle):
        self.seen.append(handle)
        if handle in self.fail:
            raise RuntimeError("需要登录才能看")
        return {"handle": handle, "channel": channel,
                "url": f"https://x/{handle}", "text": self.pages.get(handle, "")}

    def follow(self, channel, handle):
        if self.follow_fails:
            raise RuntimeError("action blocked")
        self.followed.append(handle)
        return {"handle": handle, "already": False}


# A real bio, from the account Allen pointed at.
REAL_BIO = ("DC Event Production - LED Walls, Photo Booth, Dance Floors, Event "
            "Technology, AV Production & More. 20+ Years of D.C. "
            "18630 Woodfield Rd Suite A, Gaithersburg, Maryland 20879. "
            "electriceventsdc.com")


# --- what a visit is for -----------------------------------------------------------

@pytest.mark.parametrize("text,kind", [
    ("Just wrapped the installation at the arena", "项目"),
    ("무대 시공 완료했습니다", "项目"),
    ("See us at our booth at InfoComm", "展会"),
    ("We're hiring an AV technician", "招聘"),
    ("Great concert last night", "活动"),
])
def test_a_post_that_says_work_is_happening_is_noticed(text, kind):
    assert watch.read_signals(text)[0]["kind"] == kind


def test_a_signal_carries_the_words_it_came_from():
    # A claim Allen cannot quote back is a claim he cannot safely use in an email.
    found = watch.read_signals("Proud of the installation we finished in Houston")
    assert "installation" in found[0]["excerpt"]


def test_a_quiet_profile_yields_nothing_rather_than_a_guess():
    assert watch.read_signals("Welcome to our page.") == []


def test_contact_details_published_on_a_profile_are_read():
    got = watch.read_contacts("Bookings: hello@verumav.com  +1 346-837-8628  "
                              "https://verumav.com")
    assert got == {"email": "hello@verumav.com", "phone": "+1 346-837-8628",
                   "website": "verumav.com"}


def test_the_social_links_on_a_profile_are_not_its_website():
    got = watch.read_contacts("Follow https://www.instagram.com/verumav")
    assert "website" not in got


# --- keeping the account -----------------------------------------------------------

def _queue_a_dm(conn):
    today = dt.date.today().isoformat()
    conn.execute("INSERT INTO social_dm_queue(queue_date, lead_no, channel, target,"
                 " body, rank_order, status, created_at)"
                 " VALUES (?,1,'instagram','verumav','hi',1,'ready',?)", (today, today))
    conn.commit()


def _sent_at(conn, when):
    from app import settings
    settings.set_value(conn, "social_last_send_at_instagram", when.isoformat())


def test_a_queue_waiting_on_allen_does_not_stop_reading(conn):
    """docs/77. The old rule asked this and the answer was never no, so nothing ran."""
    _queue_a_dm(conn)
    engine = FakeEngine(pages={"verumav": "installation done"})
    out = watch.watch(conn, engine, limit=1, sleeper=lambda _s: None)
    assert out["looked"] == 1
    assert engine.seen == ["verumav"]


def test_nothing_is_read_in_the_same_cycle_a_message_went_out(conn):
    now = dt.datetime(2026, 8, 31, 12, 0, tzinfo=dt.UTC)
    _sent_at(conn, now - dt.timedelta(minutes=3))
    engine = FakeEngine()
    out = watch.watch(conn, engine, sleeper=lambda _s: None, now=now)
    assert out["looked"] == 0
    assert engine.seen == []
    assert "私信" in out["skipped"]


def test_reading_resumes_once_the_quiet_window_has_passed(conn):
    now = dt.datetime(2026, 8, 31, 12, 0, tzinfo=dt.UTC)
    _sent_at(conn, now - watch.QUIET_AFTER_SEND - dt.timedelta(minutes=1))
    engine = FakeEngine(pages={"verumav": "installation done"})
    out = watch.watch(conn, engine, limit=1, sleeper=lambda _s: None, now=now)
    assert out["looked"] == 1


def test_the_daily_allowance_is_spent_and_then_gone(conn):
    engine = FakeEngine(pages={"verumav": "installation done"})
    watch.watch(conn, engine, limit=1, sleeper=lambda _s: None)
    assert watch.remaining(conn) == watch.DAILY_LIMIT - 1

    from app import settings
    settings.set_value(conn, "social_watch_count", str(watch.DAILY_LIMIT))
    out = watch.watch(conn, engine, sleeper=lambda _s: None)
    assert out["looked"] == 0 and "额度" in out["skipped"]


def test_visits_are_spaced_out(conn):
    slept: list[int] = []
    engine = FakeEngine(pages={"verumav": "", "kinotonkorea": ""})
    watch.watch(conn, engine, limit=2, sleeper=slept.append)
    assert slept and min(slept) >= watch.GAP_SECONDS[0]


def test_a_refusal_is_recorded_and_not_retried_today(conn):
    engine = FakeEngine(fail={"verumav"})
    out = watch.watch(conn, engine, limit=1, sleeper=lambda _s: None)
    assert out["failures"] == 1
    # Being told no once is information; asking three times is a signature.
    assert "verumav" in watch.failed_today(conn)
    assert [t["handle"] for t in watch.due_profiles(conn)] == ["kinotonkorea"]


def test_a_failed_visit_still_costs_its_allowance(conn):
    # Otherwise a page that always refuses would be retried until the budget is gone.
    engine = FakeEngine(fail={"verumav"})
    watch.watch(conn, engine, limit=1, sleeper=lambda _s: None)
    assert watch.remaining(conn) == watch.DAILY_LIMIT - 1


# --- what gets written -------------------------------------------------------------

def test_what_the_profile_said_lands_on_the_timeline(conn):
    # docs/91 R2：一条动态得说得出自己是哪天的，否则它可能是六年前的帖子。
    engine = FakeEngine(pages={
        "verumav": "2026年8月20日 · Finished the installation at the arena"})
    watch.watch(conn, engine, limit=1, sleeper=lambda _s: None)
    line = events.timeline(conn, 1)
    assert any("社媒动态" in e["summary"] for e in line)
    assert line[0]["detail"]["url"].endswith("verumav")


def test_a_published_email_fills_a_blank_but_never_replaces_one(conn):
    conn.execute("UPDATE leads SET email='old@verumav.com' WHERE no=1")
    conn.commit()
    engine = FakeEngine(pages={"verumav": "hello@verumav.com +1 346-837-8628"})
    watch.watch(conn, engine, limit=1, sleeper=lambda _s: None)
    row = conn.execute("SELECT email, phone FROM leads WHERE no=1").fetchone()
    assert row["email"] == "old@verumav.com"      # his record wins
    assert row["phone"] == "+1 346-837-8628"      # the blank is filled


def test_a_lead_with_no_handle_is_never_a_target(conn):
    assert 3 not in [t["lead_no"] for t in watch.due_profiles(conn)]


# --- following, added by docs/72 --------------------------------------------------

def test_a_real_led_company_is_followed(conn):
    engine = FakeEngine(pages={"verumav": REAL_BIO})
    out = watch.watch(conn, engine, limit=1, sleeper=lambda _s: None)
    assert engine.followed == ["verumav"]
    assert out["followed"] == 1


def test_a_bio_with_nothing_checkable_is_not_followed(conn):
    """Following an unrelated account also makes this account's following list look
    less like someone in the LED trade, which platforms read."""
    engine = FakeEngine(pages={"verumav": "We love LED walls"})
    watch.watch(conn, engine, limit=1, sleeper=lambda _s: None)
    assert engine.followed == []


def test_a_bio_that_is_not_this_trade_at_all_is_not_followed(conn):
    engine = FakeEngine(pages={"verumav": "Wedding photography · hello@snaps.com"})
    watch.watch(conn, engine, limit=1, sleeper=lambda _s: None)
    assert engine.followed == []


def test_the_follow_budget_is_tighter_than_the_reading_budget():
    # Following is a write action, and platforms tolerate those far less.
    assert watch.FOLLOW_LIMIT < watch.DAILY_LIMIT


def test_a_refused_follow_stops_all_following_for_the_day(conn):
    """A platform refusing a write action is its last warning before a block."""
    engine = FakeEngine(pages={"verumav": REAL_BIO, "kinotonkorea": REAL_BIO},
                        follow_fails=True)
    watch.watch(conn, engine, limit=2, sleeper=lambda _s: None)
    assert engine.followed == []
    assert watch.follows_left(conn) == 0


def test_reading_continues_after_a_follow_is_refused(conn):
    # The read budget and the write budget are different resources.
    engine = FakeEngine(pages={"verumav": REAL_BIO, "kinotonkorea": REAL_BIO},
                        follow_fails=True)
    out = watch.watch(conn, engine, limit=2, sleeper=lambda _s: None)
    assert out["looked"] == 2


def test_the_bio_website_is_saved_onto_the_record(conn):
    engine = FakeEngine(pages={"verumav": REAL_BIO})
    watch.watch(conn, engine, limit=1, sleeper=lambda _s: None)
    site = conn.execute("SELECT website FROM leads WHERE no=1").fetchone()[0]
    assert site == "electriceventsdc.com"
