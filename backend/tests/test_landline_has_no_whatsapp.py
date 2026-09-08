"""A landline is not a WhatsApp number, and a dialog Allen saw is a fact (docs/108).

docs/62 fixed the numbers that were dialled without a country code. What was left is a
different thing wearing the same dialog: `+27 12 809 1494` is a Pretoria landline, and
South African mobiles start `+27 6/7/8`. WhatsApp was telling the truth.

Two rules, and they cover different halves of the book. R2 keeps the 159 numbers we can
show are landlines out of the queue. The 490 North American numbers cannot be told apart
at all — NANP does not split by use — so R1 is the only thing that reaches them: Allen
presses a button on the dialog he is already reading.
"""
import pytest

from app import channel_outreach as co
from app import social_queue
from app.channel_outreach import dialable_whatsapp as dial
from app.db import connect, init_schema


# ---------------------------------------------------------------- R2: landlines

@pytest.mark.parametrize("phone,country", [
    ("+27 12 809 1494", None),          # Pretoria — the number in the dialog
    ("+27 21 555 0100", "South Africa"),  # Cape Town
    ("+82 31 504-3773", "South Korea"),   # Gyeonggi
    ("+82 2 555 1234", "South Korea"),    # Seoul
    ("+55 11 3044-4609", "Brazil"),       # São Paulo, 8-digit subscriber
    ("+56 2 2345 6789", "Chile"),         # Santiago
    ("+57 601 555 1234", "Colombia"),     # Bogotá
    ("+51 1 555 1234", "Peru"),           # Lima
    ("+34 91 555 1234", "Spain"),         # Madrid
    ("+44 161 555 1234", "UK"),           # Manchester
    ("+61 2 5550 1234", "Australia"),     # Sydney
    ("+7 495 555 1234", "Russia"),        # Moscow
])
def test_a_landline_has_no_whatsapp_channel(phone, country):
    assert dial(phone, country) == ""


@pytest.mark.parametrize("phone,country", [
    ("+27 82 555 1234", "South Africa"),
    ("+82 10 5504 3773", "South Korea"),
    ("+55 11 99044-4609", "Brazil"),
    ("+56 9 8765 4321", "Chile"),
    ("+57 310 555 1234", "Colombia"),
    ("+51 987 654 321", "Peru"),
    ("+34 612 345 678", "Spain"),
    ("+44 7700 900123", "UK"),
    ("+61 412 345 678", "Australia"),
    ("+7 912 555 1234", "Russia"),
])
def test_a_mobile_still_goes_to_the_queue(phone, country):
    assert dial(phone, country) != ""


@pytest.mark.parametrize("phone", [
    "+1 404 835 2230", "+1 202 695 3325", "404-835-2230", "+1 604 555 0123",
])
def test_a_north_american_number_is_never_excluded_as_a_landline(phone):
    """NANP carries no landline/mobile split, so any answer here would be invented.

    Excluding one costs the same as burning a good number: the company loses the
    channel. Dialling one costs a dialog Allen closes (docs/108 R2).
    """
    assert dial(phone, "USA") != ""


@pytest.mark.parametrize("phone,country", [
    ("+52 55 1234 5678", "Mexico"),     # Mexico dropped the split in 2019
    ("+54 11 4555 1234", "Argentina"),  # the mobile 9 is usually not written down
    ("+39 06 5555 1234", "Italy"),      # no rule for 39 — not in the table
])
def test_a_country_without_a_rule_keeps_its_channel(phone, country):
    assert dial(phone, country) != ""


def test_a_landline_is_not_recorded_as_having_no_whatsapp():
    """R2 proves the number is a landline, not that the company has no WhatsApp.

    Writing `none` here would keep the company out even after a mobile is added.
    """
    from app.phone_format import is_fixed_line
    assert is_fixed_line("27128091494") is True
    assert is_fixed_line("14048352230") is False


# ---------------------------------------------------------------- R1: the button

@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    social_queue.ensure_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, phone) VALUES
            (1, 'Ekm Exports', 'South Africa', '+27128091494'),
            (2, 'Atlanta Pro AV', 'USA', '+14048352230');
        INSERT INTO social_dm_queue(queue_date, lead_no, channel, target, body,
                                    rank_order, status, created_at)
        VALUES (date('now','localtime'), 1, 'whatsapp', '27128091494', 'Hi,', 1,
                'ready', datetime('now')),
               (date('now','localtime'), 2, 'whatsapp', '14048352230', 'Hi,', 2,
                'ready', datetime('now'));
    """)
    c.commit()
    return c


def status(conn, no):
    return conn.execute("SELECT whatsapp_status FROM leads WHERE no=?", (no,)).fetchone()[0]


def rows(conn):
    return conn.execute("SELECT COUNT(*) FROM social_dm_queue").fetchone()[0]


def test_marking_a_row_records_the_number_has_no_whatsapp(conn):
    qid = conn.execute("SELECT id FROM social_dm_queue WHERE lead_no=2").fetchone()[0]
    assert social_queue.mark_no_whatsapp(conn, qid) is True
    assert status(conn, 2) == "none"


def test_a_marked_row_leaves_todays_queue(conn):
    qid = conn.execute("SELECT id FROM social_dm_queue WHERE lead_no=2").fetchone()[0]
    social_queue.mark_no_whatsapp(conn, qid)
    assert rows(conn) == 1


def test_a_marked_number_is_not_offered_again(conn):
    qid = conn.execute("SELECT id FROM social_dm_queue WHERE lead_no=2").fetchone()[0]
    social_queue.mark_no_whatsapp(conn, qid)
    lead = dict(conn.execute(
        "SELECT no, phone, instagram, facebook, country, whatsapp_status"
        " FROM leads WHERE no=2").fetchone())
    assert social_queue._channel_for(conn, lead, set()) is None


def test_skipping_a_row_for_today_says_nothing_about_the_number(conn):
    """`不发` is about today; the mark is about the number. One button cannot be both."""
    qid = conn.execute("SELECT id FROM social_dm_queue WHERE lead_no=2").fetchone()[0]
    social_queue.drop(conn, qid)
    assert status(conn, 2) is None


def test_marking_only_applies_to_whatsapp_rows(conn):
    conn.execute("UPDATE social_dm_queue SET channel='instagram' WHERE lead_no=2")
    conn.commit()
    qid = conn.execute("SELECT id FROM social_dm_queue WHERE lead_no=2").fetchone()[0]
    assert social_queue.mark_no_whatsapp(conn, qid) is False
    assert status(conn, 2) is None


def test_marking_a_row_that_is_gone_reports_it(conn):
    assert social_queue.mark_no_whatsapp(conn, 9999) is False
