import pytest

from app import replies, sequences
from app.db import connect, init_schema


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, email) VALUES
            (1, 'Alpha AV', 'USA', 'sales@alpha.com'),
            (2, 'Beta Screens', 'USA', 'b@beta.com'),
            (3, 'Gamma LED', 'Brazil', 'g@gamma.com');
        INSERT INTO outreach(lead_no, channel, status, touch_count) VALUES
            (1, 'email', 'messaged', 1),
            (2, 'email', 'messaged', 1);
    """)
    c.commit()
    return c


def test_match_marks_replied_case_insensitive(conn):
    res = replies.match_and_mark(conn, ["SALES@Alpha.com"])
    assert res == {"matched": 1, "newly_replied": 1, "lead_nos": [1]}
    row = conn.execute("SELECT status FROM outreach WHERE lead_no=1 AND channel='email'").fetchone()
    assert row["status"] == "replied"


def test_unknown_sender_ignored(conn):
    assert replies.match_and_mark(conn, ["stranger@nope.com"])["matched"] == 0


def test_already_replied_not_double_counted(conn):
    replies.match_and_mark(conn, ["b@beta.com"])
    res = replies.match_and_mark(conn, ["b@beta.com"])
    assert res["matched"] == 1 and res["newly_replied"] == 0


def test_reply_stops_sequence_enrollment(conn):
    sid = sequences.create_sequence(conn, "S", "email", [{"day_offset": 0, "body": "hi"}])
    sequences.enroll_leads(conn, sid, [1, 2])
    replies.match_and_mark(conn, ["sales@alpha.com"])
    assert {d["lead_no"] for d in sequences.due_queue(conn)} == {2}


def test_poll_uses_injected_fetcher(conn):
    fake = [{"from_addr": "g@gamma.com", "subject": "Re: LED", "body": "hi", "received_at": ""}]
    res = replies.poll_replies(conn, fetch_messages=lambda days: fake)
    assert res["lead_nos"] == [3]


def test_lookback_widens_to_cover_the_outage(conn, monkeypatch):
    """A fixed 7-day window drops every reply that arrived while polling was broken
    for longer than a week — the exact failure that hid replies for two weeks."""
    import datetime as dt
    from app import settings
    assert replies.adaptive_since_days(conn) == replies.SINCE_DAYS_MAX  # never synced

    settings.set_value(conn, "reply_sync_last_success_at",
                       (dt.datetime.now(dt.UTC) - dt.timedelta(days=14)).isoformat())
    assert replies.adaptive_since_days(conn) == 16

    settings.set_value(conn, "reply_sync_last_success_at", dt.datetime.now(dt.UTC).isoformat())
    assert replies.adaptive_since_days(conn) == replies.SINCE_DAYS_MIN


def test_failed_poll_does_not_narrow_the_next_window(conn, monkeypatch):
    from app import settings
    monkeypatch.setattr("app.channels.email_adapter.get_password", lambda: "pw")

    def boom(mailbox, since_days):
        raise OSError("[WinError 10060] network not up yet")

    res = replies.poll_all_replies(conn, fetcher=boom)
    assert res["mailboxes_checked"] == 0 and res["errors"]
    assert settings.get(conn, "reply_sync_last_status") == "error"
    # last_success untouched -> the retry still looks all the way back
    assert not settings.get(conn, "reply_sync_last_success_at")
    assert replies.adaptive_since_days(conn) == replies.SINCE_DAYS_MAX


def test_successful_poll_records_success_timestamp(conn, monkeypatch):
    from app import settings
    monkeypatch.setattr("app.channels.email_adapter.get_password", lambda: "pw")
    fake = [{"from_addr": "g@gamma.com", "subject": "Re: LED", "body": "hi", "received_at": ""}]
    res = replies.poll_all_replies(conn, fetcher=lambda mailbox, since_days: fake)
    assert res["replies"] == 1 and res["since_days"] == replies.SINCE_DAYS_MAX
    assert settings.get(conn, "reply_sync_last_success_at")


# Verbatim shapes taken from Allen's Gmail — the localised notice is exactly what the
# old blacklist regex choked on (27 of 34 bounces went unattributed).
_HARD_BOUNCE_CN = (
    "** 找不到地址 **\n\n由于系统找不到电子邮件地址 g@gamma.com，或该地址无法接收邮件，"
    "因此无法递送您的邮件。\n\n550 5.1.1 The email account that you tried to reach does not exist.\n")
_DELAY_CN = (
    "** 邮件延迟 **\n\n您发送给 g@gamma.com 的邮件尚未送达。系统将在 44 小时内继续尝试。\n"
    "421 4.7.0 Try again later\n")


def _bounce(body, subject="Delivery Status Notification (Failure)"):
    return [{"from_addr": "mailer-daemon@googlemail.com", "subject": subject,
             "body": body, "received_at": "2026-08-01T00:00:00+00:00"}]


def test_bounce_address_extracted_from_localised_notice(conn):
    res = replies.process_messages(conn, _bounce(_HARD_BOUNCE_CN))
    assert res["bounces"] == 1 and res["lead_nos"] == [3]
    assert conn.execute("SELECT email_status FROM leads WHERE no=3").fetchone()[0] == "invalid"


def test_full_width_comma_does_not_swallow_the_address(conn):
    found = replies._EMAIL_RE.findall("地址 g@gamma.com，或该地址无法接收邮件")
    assert found == ["g@gamma.com"]


def test_delay_notice_never_burns_a_live_address(conn):
    """Same mailer-daemon sender, temporary reason — marking it invalid would kill a
    good lead permanently over a transient server hiccup."""
    res = replies.process_messages(
        conn, _bounce(_DELAY_CN, "Delivery Status Notification (Delay)"))
    assert res["delayed"] == 1 and res["bounces"] == 0
    assert conn.execute("SELECT email_status FROM leads WHERE no=3").fetchone()[0] is None
    # nothing to read and nothing to do — it must not land in the inbox either
    assert conn.execute("SELECT COUNT(*) FROM inbox_messages WHERE lead_no=3").fetchone()[0] == 0


def test_bounce_without_a_clear_reason_is_not_acted_on(conn):
    res = replies.process_messages(conn, _bounce("Could not deliver to g@gamma.com\n"))
    assert res["bounces"] == 0 and res["delayed"] == 1
    assert conn.execute("SELECT email_status FROM leads WHERE no=3").fetchone()[0] is None
