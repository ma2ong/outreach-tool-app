"""Remembering which numbers have no WhatsApp account (docs/59).

The engine already recognised the "not on WhatsApp" dialog and raised. That RuntimeError
was caught as an ordinary send failure and went into an errors list that nobody kept, so
the same number was queued again the next morning and a browser trip was spent
rediscovering the same fact.

What these tests hold is the line between the two kinds of failure: WhatsApp saying the
number does not exist is a fact about the number; a timeout is a fact about our run.
"""
import pytest

from app import channel_outreach as co
from app import social_queue
from app.db import connect, init_schema


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, phone, hook) VALUES
            (1, 'Verum AV', 'USA', '+13468378628', 'Saw the rental work.'),
            (2, 'Bright AV', 'USA', '+13468370000', 'Saw the staging work.');
    """)
    c.commit()
    return c


def status(conn, no):
    return conn.execute("SELECT whatsapp_status FROM leads WHERE no=?", (no,)).fetchone()[0]


def test_a_number_starts_out_unknown_not_absent(conn):
    # NULL has to mean "never checked"; treating it as "no account" would discard
    # hundreds of reachable customers.
    assert status(conn, 1) is None


def test_whatsapp_saying_the_number_is_not_registered_is_recorded(conn):
    co._note_whatsapp_result(conn, 1, "whatsapp", "number not on WhatsApp")
    assert status(conn, 1) == "none"


@pytest.mark.parametrize("error", [
    "Timeout 45000ms exceeded",
    "Target page, context or browser has been closed",
    "net::ERR_CONNECTION_RESET",
])
def test_our_own_failures_say_nothing_about_the_number(conn, error):
    co._note_whatsapp_result(conn, 1, "whatsapp", error)
    assert status(conn, 1) is None


def test_a_delivered_message_proves_the_number_is_on_whatsapp(conn):
    co._note_whatsapp_result(conn, 1, "whatsapp", None)
    assert status(conn, 1) == "active"


def test_other_channels_do_not_touch_the_whatsapp_field(conn):
    co._note_whatsapp_result(conn, 1, "instagram", "account not found")
    assert status(conn, 1) is None


def test_a_number_with_no_account_is_not_eligible_again(conn):
    co._note_whatsapp_result(conn, 1, "whatsapp", "number not on WhatsApp")
    picked = {r["no"] for r in co.eligible(conn, [1, 2], "whatsapp")}
    assert picked == {2}


def test_that_same_number_stays_eligible_on_other_channels(conn):
    conn.execute("UPDATE leads SET instagram='verumav' WHERE no=1")
    co._note_whatsapp_result(conn, 1, "whatsapp", "number not on WhatsApp")
    conn.commit()
    picked = {r["no"] for r in co.eligible(conn, [1, 2], "instagram")}
    assert 1 in picked


def test_the_daily_queue_skips_a_number_with_no_account(conn):
    conn.execute("UPDATE leads SET whatsapp_status='none' WHERE no=1")
    conn.commit()
    lead = dict(conn.execute(
        "SELECT no, phone, instagram, facebook, whatsapp_status FROM leads WHERE no=1"
    ).fetchone())
    assert social_queue._channel_for(conn, lead, taken=set()) is None


def test_the_queue_still_takes_a_number_never_checked(conn):
    lead = dict(conn.execute(
        "SELECT no, phone, instagram, facebook, whatsapp_status FROM leads WHERE no=2"
    ).fetchone())
    picked = social_queue._channel_for(conn, lead, taken=set())
    assert picked and picked[0] == "whatsapp"
