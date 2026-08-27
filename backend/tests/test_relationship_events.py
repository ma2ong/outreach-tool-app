"""One relationship's whole story in one place (docs/68 part 1).

Six tables held pieces of it — outreach, send_log, sequence_enrollments,
social_dm_queue, inbox_messages, activities — so the conversation view reassembled it on
every read, and a fact belonging to none of them (a direct line found while prospecting)
had nowhere to go at all.

The rule these tests exist for is the one that is easy to get wrong: this is a bystander
to the work it describes. A send that succeeded and then failed to be written down is
still a send.
"""
import sqlite3

import pytest

from app import campaigns, relationship_events as events
from app.db import connect, init_schema


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country) VALUES
            (1, 'Verum AV', 'USA'), (2, 'Kinoton', 'South Korea');
    """)
    c.commit()
    return c


def test_an_event_lands_on_the_timeline(conn):
    events.record(conn, 1, "fact", "补到直线电话", source="discovery",
                  detail={"fields": {"phone": "+13468378628"}})
    line = events.timeline(conn, 1)
    assert len(line) == 1
    assert line[0]["summary"] == "补到直线电话"
    assert line[0]["detail"]["fields"]["phone"] == "+13468378628"


def test_the_timeline_is_in_the_order_things_happened(conn):
    events.record(conn, 1, "sent", "first", at="2026-08-01T00:00:00Z")
    events.record(conn, 1, "received", "reply", at="2026-08-03T00:00:00Z")
    events.record(conn, 1, "sent", "second", at="2026-08-02T00:00:00Z")
    assert [e["summary"] for e in events.timeline(conn, 1)] == ["first", "second", "reply"]


def test_one_relationship_does_not_see_another(conn):
    events.record(conn, 1, "sent", "to Verum")
    events.record(conn, 2, "sent", "to Kinoton")
    assert [e["summary"] for e in events.timeline(conn, 2)] == ["to Kinoton"]


def test_writing_an_event_can_never_break_the_work_it_describes(conn):
    """The order is: do the thing, record it. If recording raised, a letter that went
    out would be reported as a failure — losing the send to save the note about it."""
    broken = sqlite3.connect(":memory:")     # no schema, every statement will fail
    broken.close()                           # and now it is closed as well
    assert events.record(broken, 1, "sent", "went out anyway") is None


def test_a_send_writes_itself_onto_the_timeline(conn):
    campaigns.log_send(conn, 1, "email", "序列:角度二",
                       subject="Which cabinet?", body="Hi there.")
    line = events.timeline(conn, 1)
    assert [e["kind"] for e in line] == ["sent"]
    assert line[0]["channel"] == "email"
    assert line[0]["detail"]["body"] == "Hi there."


def test_the_send_log_is_still_the_authoritative_row(conn):
    # The event is written beside the existing tables, never instead of them.
    campaigns.log_send(conn, 1, "email", "序列:角度二", subject="S", body="B")
    row = conn.execute("SELECT campaign, body FROM send_log WHERE lead_no=1").fetchone()
    assert row["campaign"] == "序列:角度二" and row["body"] == "B"


def test_todays_facts_are_countable_for_the_report(conn):
    events.record(conn, 1, "fact", "补到邮箱", source="discovery")
    events.record(conn, 2, "fact", "补到职位", source="discovery")
    events.record(conn, 1, "sent", "letter")
    assert events.count_today(conn, "fact") == 2
    assert events.count_today(conn, "sent") == 1


def test_recent_can_be_filtered_by_what_happened(conn):
    events.record(conn, 1, "fact", "补到邮箱", source="discovery")
    events.record(conn, 1, "sent", "letter")
    facts = events.recent(conn, kind="fact", days=1)
    assert len(facts) == 1
    assert facts[0]["company_en"] == "Verum AV"
