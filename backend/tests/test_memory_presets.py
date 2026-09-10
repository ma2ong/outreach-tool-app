"""A memory that stops the letter (docs/122).

Allen wrote "后续不发冷邮件" on six customers. The sentence went to a prompt; the send
path never saw it, and three of those six were due back in the cold queue on 09-18 and
09-22. These tests are about the outcome, not the column: after the preset, does the
cold sender still pick this company up?
"""
import datetime as dt

import pytest

from app import outreach as email_outreach
from app import repository as repo
from app.agent import memory_presets
from app.db import connect, init_schema


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, email, stage) VALUES
            (1, 'JDKAT', 'South Korea', 'buy@jdkat.com', 'contacted'),
            (2, 'Fresh Lead', 'USA', 'hi@fresh.com', 'new');
        INSERT INTO outreach(lead_no, channel, status, touch_count, message_sent_date)
            VALUES (1, 'email', 'messaged', 5, '2026-08-01');
    """)
    c.commit()
    return c


def cold(conn, no: int) -> bool:
    return bool(email_outreach.eligible_leads(conn, [no], "email"))


# ------------------------------------------------------------------ the one that matters

def test_the_cooldown_would_otherwise_hand_him_back_to_the_cold_queue(conn):
    """The starting position: written to five times, silent since 2026-08-01, so the
    14-day cooldown has expired and he is a cold prospect again."""
    assert cold(conn, 1) is True


def test_in_touch_stops_the_cold_email_for_good(conn):
    memory_presets.apply(conn, 1, "in_touch")
    assert cold(conn, 1) is False


def test_it_also_holds_for_a_company_we_never_wrote_to(conn):
    """#2 has no outreach row at all. The blocked-set query starts from `outreach`, so
    this is the case an extra AND would have missed."""
    memory_presets.apply(conn, 2, "in_touch")
    assert cold(conn, 2) is False


def test_the_sentence_is_filed_as_a_memory_in_his_words(conn):
    result = memory_presets.apply(conn, 1, "reorder")
    rows = [r["content"] for r in conn.execute(
        "SELECT content FROM lead_memory_items WHERE lead_no=1 AND origin='explicit'")]
    assert rows == [result["memory"]]
    assert "想办法让他重新下单" in rows[0]


def test_a_returning_customer_is_marked_won_as_well(conn):
    memory_presets.apply(conn, 1, "reorder")
    assert repo.get_lead(conn, 1).stage == "won"


# ------------------------------------- stop cold outreach is not "never contact again"

def test_stopping_cold_email_leaves_every_human_path_open(conn):
    """The whole point of a separate flag: 想办法让对方再次下单 needs a way to write."""
    memory_presets.apply(conn, 1, "in_touch")
    lead = repo.get_lead(conn, 1)
    assert lead.no_cold_outreach is True
    assert lead.do_not_contact is False


def test_a_competitor_is_silenced_on_every_channel(conn):
    memory_presets.apply(conn, 1, "peer")
    lead = repo.get_lead(conn, 1)
    assert lead.do_not_contact is True


def test_a_note_about_the_decider_changes_nothing_else(conn):
    memory_presets.apply(conn, 1, "not_decider")
    lead = repo.get_lead(conn, 1)
    assert lead.do_not_contact is False and lead.no_cold_outreach is False
    assert cold(conn, 1) is True


# ------------------------------------------------------------------ the other two paths

def test_the_social_dm_queue_skips_him_too(conn):
    """docs/122 R2: email, DMs and the daily social queue share one blocked-set query,
    which is why the rule was added there and not at three call sites."""
    from app import channel_outreach

    conn.execute("UPDATE leads SET instagram='jdkat' WHERE no=1")
    conn.commit()
    assert channel_outreach.eligible(conn, [1], "instagram")
    memory_presets.apply(conn, 1, "in_touch")
    assert channel_outreach.eligible(conn, [1], "instagram") == []


def test_an_unknown_preset_is_refused(conn):
    with pytest.raises(KeyError):
        memory_presets.apply(conn, 1, "nope")


def test_every_preset_says_what_it_did(conn):
    """docs/122 R4: a switch nobody can see is a switch nobody trusts."""
    for option in memory_presets.options():
        assert option["effect"] and option["label"] and option["memory"]


def test_the_stopped_ones_can_be_filtered_out_of_the_book(conn):
    """He asked for these to be selectable: automatic sending will never touch them
    again, so they only move when he remembers them."""
    memory_presets.apply(conn, 1, "in_touch")
    found = repo.list_leads(conn, status="no_cold")
    assert [l.no for l in found] == [1]
