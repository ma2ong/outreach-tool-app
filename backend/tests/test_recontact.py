"""A company we wrote to years ago is a lead again (docs/73).

Every test here is about one line that used to read `status IN ('messaged','replied')`
and exclude a company forever. It was holding back 329 companies whose last contact was
over a year old — the oldest nearly four years, imported from Xiaoman — while the pool
reported eight sendable leads and the daily volume sat at a fifth of what Allen asked for.

The cases that must NOT come back are the point of the change, not an afterthought: one
`won` customer really is sitting in the re-approachable set, and a cold introduction to
someone who has already paid is the worst thing this system can do (docs/54 R1).
"""
import pytest

from app import channel_outreach, outreach, recontact


@pytest.fixture(autouse=True)
def _clean(conn):
    conn.executescript("DELETE FROM outreach; DELETE FROM leads;")
    conn.commit()


def _lead(conn, no, **kw):
    cols = {"company_en": f"C{no}", "email": f"c{no}@x.com", "country": "USA"}
    cols.update(kw)
    conn.execute(f"INSERT INTO leads(no,{','.join(cols)}) VALUES (?,{','.join('?' * len(cols))})",
                 [no, *cols.values()])


def _sent(conn, no, days_ago, status="messaged", channel="email"):
    conn.execute(
        "INSERT INTO outreach(lead_no,channel,status,touch_count,message_sent_date)"
        " VALUES (?,?,?,1,date('now',?))", (no, channel, status, f"-{days_ago} days"))


def _elig(conn, nos, channel="email"):
    return [l["no"] for l in outreach.eligible_leads(conn, nos, channel)]


# --- the way out --------------------------------------------------------------------

def test_a_company_silent_for_years_is_a_lead_again(conn):
    _lead(conn, 1)
    _sent(conn, 1, 1421)          # the oldest row in the real book
    conn.commit()
    assert _elig(conn, [1]) == [1]


def test_a_recent_conversation_is_left_alone(conn):
    _lead(conn, 1)
    _sent(conn, 1, 30)
    conn.commit()
    assert _elig(conn, [1]) == []


def test_the_line_sits_at_the_cooldown_and_not_a_day_earlier(conn):
    _lead(conn, 1)
    _lead(conn, 2)
    _sent(conn, 1, recontact.COOLDOWN_DAYS - 1)
    _sent(conn, 2, recontact.COOLDOWN_DAYS + 1)
    conn.commit()
    assert _elig(conn, [1, 2]) == [2]


# --- the ones that must never come back ---------------------------------------------

def test_a_customer_who_paid_is_never_cold_pitched_again(conn):
    """docs/54 R1. One `won` lead is genuinely in the re-approachable window today."""
    _lead(conn, 1, stage="won")
    _sent(conn, 1, 1000)
    conn.commit()
    assert _elig(conn, [1]) == []
    assert 1 not in recontact.reapproachable(conn)


def test_a_lead_written_off_is_not_revived_by_the_calendar(conn):
    _lead(conn, 1, stage="lost")
    _sent(conn, 1, 1000)
    conn.commit()
    assert _elig(conn, [1]) == []


def test_a_reply_is_a_relationship_and_never_expires(conn):
    _lead(conn, 1)
    _sent(conn, 1, 1000, status="replied")
    conn.commit()
    assert _elig(conn, [1]) == []


def test_a_send_with_no_date_is_not_gambled_on(conn):
    # We do not know when it went out, so it does not get a cooldown clock.
    _lead(conn, 1)
    conn.execute("INSERT INTO outreach(lead_no,channel,status) VALUES (1,'email','messaged')")
    conn.commit()
    assert _elig(conn, [1]) == []


def test_a_bounced_address_is_not_retried_years_later(conn):
    """Allen's rule is to find another contact, not to redial a dead mailbox. All 36
    bounced leads already carry email_status='invalid'."""
    _lead(conn, 1, email_status="invalid")
    _sent(conn, 1, 1000)
    conn.commit()
    assert _elig(conn, [1]) == []
    assert 1 not in recontact.reapproachable(conn)


def test_do_not_contact_still_means_do_not_contact(conn):
    _lead(conn, 1, do_not_contact=1)
    _sent(conn, 1, 1000)
    conn.commit()
    assert _elig(conn, [1]) == []


# --- the other channels -------------------------------------------------------------

def test_the_cooldown_applies_to_social_channels_too(conn):
    _lead(conn, 1, instagram="c1")
    _sent(conn, 1, 1000, channel="instagram")
    conn.commit()
    assert [l["no"] for l in channel_outreach.eligible(conn, [1], "instagram")] == [1]


def test_each_channel_keeps_its_own_clock(conn):
    # An old email does not license a fresh Instagram DM's cooldown, or the reverse.
    _lead(conn, 1, instagram="c1")
    _sent(conn, 1, 1000, channel="email")
    _sent(conn, 1, 5, channel="instagram")
    conn.commit()
    assert channel_outreach.eligible(conn, [1], "instagram") == []
    assert _elig(conn, [1]) == [1]


# --- what the queue hands back ------------------------------------------------------

def test_the_longest_silent_company_is_offered_first(conn):
    for no, days in ((1, 200), (2, 1400), (3, 700)):
        _lead(conn, no)
        _sent(conn, no, days)
    conn.commit()
    assert recontact.reapproachable(conn) == [2, 3, 1]


def test_a_lead_with_no_address_on_that_channel_is_not_offered(conn):
    _lead(conn, 1, email=None)
    _sent(conn, 1, 1000)
    conn.commit()
    assert recontact.reapproachable(conn) == []


# --- putting them back to work (R3) -------------------------------------------------

def _angle_two(conn):
    """The two live sequences, minimal but real: the Korean one must contain Korean
    text, because `is_korean_sequence` reads the copy and ignores the name."""
    from app import sequences
    from app.seed_angle2 import EN_NAME, KO_NAME
    en = sequences.create_sequence(conn, EN_NAME, "email", [
        {"step_index": 0, "day_offset": 0, "subject": "Which cabinet?", "body": "Hi"}])
    ko = sequences.create_sequence(conn, KO_NAME, "email", [
        {"step_index": 0, "day_offset": 0, "subject": "안녕하세요", "body": "제품 문의"}])
    return en, ko


def test_a_thin_day_is_topped_up_from_the_dormant_pool(conn):
    from app import autosend
    _angle_two(conn)
    for no in range(1, 6):
        _lead(conn, no)
        _sent(conn, no, 1000)
    conn.commit()
    assert autosend._top_up(conn, 3) == 3
    due = [d["lead_no"] for d in __import__("app.sequences", fromlist=["x"]).due_queue(conn, "email")]
    assert len(due) == 3


def test_korea_is_topped_up_in_korean_and_everyone_else_in_english(conn):
    from app import autosend
    en, ko = _angle_two(conn)
    _lead(conn, 1, country="South Korea")
    _lead(conn, 2, country="USA")
    _sent(conn, 1, 1000)
    _sent(conn, 2, 1000)
    conn.commit()
    autosend._top_up(conn, 10)
    got = {r["lead_no"]: r["sequence_id"] for r in
           conn.execute("SELECT lead_no, sequence_id FROM sequence_enrollments")}
    assert got == {1: ko, 2: en}


def test_a_company_that_already_had_this_angle_is_not_sent_it_twice(conn):
    from app import autosend, sequences
    en, _ = _angle_two(conn)
    _lead(conn, 1)
    _sent(conn, 1, 1000)
    conn.commit()
    sequences.enroll_leads(conn, en, [1])
    conn.execute("UPDATE sequence_enrollments SET status='completed'")
    conn.commit()
    assert autosend._top_up(conn, 10) == 0


def test_the_top_up_never_exceeds_the_gap(conn):
    from app import autosend
    _angle_two(conn)
    for no in range(1, 21):
        _lead(conn, no)
        _sent(conn, no, 1000)
    conn.commit()
    assert autosend._top_up(conn, 4) == 4


def test_a_record_named_after_a_mailbox_is_not_topped_up(conn):
    """44 Xiaoman rows carry someone's naver/gmail address in the company-name column;
    a letter cannot address a company by mailbox."""
    from app import autosend
    _angle_two(conn)
    _lead(conn, 1, company_en="jsy5129@naver.com", city="Seoul")
    _lead(conn, 2, company_en="SNA Displays", city="New York")
    _sent(conn, 1, 1000)
    _sent(conn, 2, 1001)
    conn.commit()
    autosend._top_up(conn, 10)
    assert [r["lead_no"] for r in conn.execute(
        "SELECT lead_no FROM sequence_enrollments")] == [2]


def test_a_lead_with_nothing_personal_to_say_is_not_topped_up(conn):
    # The guard refuses these at send time; enrolling them parks the day in quality_hold
    # instead of sending more (the 110 stuck follow-ups seed_angle2 had to rescue).
    from app import autosend
    _angle_two(conn)
    _lead(conn, 1, company_en="LED", city=None, website=None)
    _sent(conn, 1, 1000)
    conn.commit()
    assert autosend._top_up(conn, 10) == 0


def test_the_longest_silent_writable_company_is_topped_up_first(conn):
    from app import autosend
    _angle_two(conn)
    _lead(conn, 1, company_en="Vantage LED", city="Corona")
    _lead(conn, 2, company_en="Trans-Lux", city="Norwalk")
    _sent(conn, 1, 700)
    _sent(conn, 2, 1400)
    conn.commit()
    autosend._top_up(conn, 1)
    assert [r["lead_no"] for r in conn.execute(
        "SELECT lead_no FROM sequence_enrollments")] == [2]
