import json
from email.message import EmailMessage

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


def test_attachment_metadata_is_evidence_only():
    msg = EmailMessage()
    msg.set_content("Please check the drawing.")
    msg.add_attachment(b"drawing bytes", maintype="application", subtype="pdf",
                       filename="Cabinet drawing.pdf")

    found = replies._attachment_metadata(msg)

    assert found == [{
        "filename": "Cabinet drawing.pdf",
        "content_type": "application/pdf",
        "size": 13,
        "sha256": "597c3489ab2ffa7aad92c99eba241a5aadb43bca19c5d0d540e7da856c2f4ffa",
    }]
    assert "payload" not in found[0]


def test_rfc_message_id_dedupes_repoll_with_changed_received_at(conn):
    first = {
        "from_addr": "sales@alpha.com", "subject": "Re: LED",
        "body": "See the attached drawing.", "received_at": "2026-09-09T08:00:00+08:00",
        "rfc_message_id": "<stable-42@alpha.com>",
        "attachments": [{"filename": "drawing.pdf", "content_type": "application/pdf",
                         "size": 42, "sha256": "abc"}],
    }
    second = {**first, "received_at": "2026-09-09T00:00:01Z"}

    assert replies.process_messages(conn, [first])["stored"] == 1
    assert replies.process_messages(conn, [second])["stored"] == 0

    row = conn.execute(
        "SELECT rfc_message_id,attachments_json FROM inbox_messages WHERE lead_no=1"
    ).fetchone()
    assert row["rfc_message_id"] == "<stable-42@alpha.com>"
    assert json.loads(row["attachments_json"])[0]["filename"] == "drawing.pdf"


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
    # replies.py imports get_password directly; patch the dependency at its use site.
    monkeypatch.setattr("app.replies.get_password", lambda: "pw")

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
    monkeypatch.setattr("app.replies.get_password", lambda: "pw")
    fake = [{"from_addr": "g@gamma.com", "subject": "Re: LED", "body": "hi", "received_at": ""}]
    res = replies.poll_all_replies(conn, fetcher=lambda mailbox, since_days: fake)
    assert res["replies"] == 1 and res["since_days"] == replies.SINCE_DAYS_MAX
    assert settings.get(conn, "reply_sync_last_success_at")


def test_reply_enrichment_failure_is_visible_without_losing_the_reply(conn, monkeypatch):
    monkeypatch.setattr(
        "app.reply_details.apply",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("bad signature parser")),
    )
    result = replies.process_messages(conn, [{
        "from_addr": "sales@alpha.com", "subject": "Re: LED", "body": "hello",
        "received_at": "2026-09-10T10:00:00+08:00",
    }])

    assert result["stored"] == 1 and result["replies"] == 1
    assert result["enrichment_errors"] == [{
        "lead_no": 1, "message_id": 1, "stage": "reply_details",
        "error": "bad signature parser",
    }]
    assert conn.execute("SELECT COUNT(*) FROM inbox_messages").fetchone()[0] == 1


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


def _bounce_for(addr, subject="Delivery Status Notification (Failure)", body=None):
    return {"from_addr": "mailer-daemon@googlemail.com", "subject": subject,
            "body": body or f"550 5.1.1 user unknown: {addr}",
            "received_at": "2026-08-10T00:00:00+00:00"}


def test_hard_bounce_records_a_durable_date(conn):
    """email_status alone does not survive re-verification; bounced_at does."""
    conn.execute("UPDATE leads SET email = 'dead@acme.com' WHERE no = 1")
    conn.commit()
    replies.process_messages(conn, [_bounce_for("dead@acme.com")])
    row = conn.execute("SELECT email_status, bounced_at FROM leads WHERE no=1").fetchone()
    assert row["email_status"] == "invalid"
    assert row["bounced_at"] == "2026-08-10T00:00:00+00:00"


def test_a_second_bounce_keeps_the_first_date(conn):
    conn.execute("UPDATE leads SET email = 'dead@acme.com' WHERE no = 1")
    conn.commit()
    replies.process_messages(conn, [_bounce_for("dead@acme.com")])
    later = _bounce_for("dead@acme.com")
    later["received_at"] = "2026-08-12T00:00:00+00:00"
    replies.process_messages(conn, [later])
    row = conn.execute("SELECT bounced_at FROM leads WHERE no=1").fetchone()
    assert row["bounced_at"] == "2026-08-10T00:00:00+00:00"


def test_a_soft_bounce_records_no_date(conn):
    """A delay notice must not burn the address — nor look like a deliverability hit."""
    conn.execute("UPDATE leads SET email = 'slow@acme.com' WHERE no = 1")
    conn.commit()
    replies.process_messages(conn, [_bounce_for(
        "slow@acme.com", body="4.4.1 will keep trying for 44 hours: slow@acme.com")])
    row = conn.execute("SELECT email_status, bounced_at FROM leads WHERE no=1").fetchone()
    assert row["bounced_at"] is None and row["email_status"] != "invalid"


def test_backfill_recovers_dates_from_old_inbox_notices(conn):
    conn.execute(
        "INSERT INTO inbox_messages(lead_no, channel, kind, from_addr, subject, body,"
        " received_at) VALUES (1, 'email', 'bounce', 'mailer-daemon@x.com', 'Undeliverable',"
        " '5.1.1', '2026-07-02T00:00:00+00:00')")
    conn.execute(
        "INSERT INTO inbox_messages(lead_no, channel, kind, from_addr, subject, body,"
        " received_at) VALUES (1, 'email', 'bounce', 'mailer-daemon@x.com', 'Undeliverable',"
        " '5.1.1', '2026-07-09T00:00:00+00:00')")
    conn.commit()
    assert replies.backfill_bounced_at(conn) == 1
    row = conn.execute("SELECT bounced_at FROM leads WHERE no=1").fetchone()
    assert row["bounced_at"] == "2026-07-02T00:00:00+00:00"   # earliest notice wins
    assert replies.backfill_bounced_at(conn) == 0             # idempotent


def test_korean_opt_out_suppresses_the_lead(conn):
    """The Korean mail carries no opt-out line, so reading one in a reply is the only
    way a Korean customer can ask to be left alone."""
    for phrase in ("수신거부 부탁드립니다", "앞으로 연락하지 마세요", "메일 그만 보내주세요"):
        conn.execute("UPDATE leads SET do_not_contact=0 WHERE no=1")
        conn.commit()
        replies.process_messages(conn, [{
            "from_addr": "sales@alpha.com", "subject": "RE: LED",
            "body": phrase, "received_at": "2026-08-13T00:00:00+00:00"}])
        row = conn.execute("SELECT do_not_contact FROM leads WHERE no=1").fetchone()
        assert row["do_not_contact"] == 1, phrase


def test_an_ordinary_korean_reply_is_not_read_as_an_opt_out(conn):
    conn.execute("UPDATE leads SET do_not_contact=0 WHERE no=1")
    conn.commit()
    replies.process_messages(conn, [{
        "from_addr": "sales@alpha.com", "subject": "RE: LED",
        "body": "안녕하세요, 견적 부탁드립니다. P2.5 실내용으로 검토 중입니다.",
        "received_at": "2026-08-13T00:00:00+00:00"}])
    row = conn.execute("SELECT do_not_contact FROM leads WHERE no=1").fetchone()
    assert row["do_not_contact"] == 0


EIDIM_AUTO = (
    "##################################\n"
    "#####   This message is auto-reply   ######\n"
    "##### Please DO NOT reply to this email ######\n"
    "Dear Valued Customer,\n"
    "Thank you so much for reaching out! We have received your email and a team "
    "member will get back to you shortly.\n")


def test_auto_reply_does_not_end_the_conversation(conn):
    """Regression: eidim.com's autoresponder was filed as a human reply, which stopped
    the follow-up sequence for a lead nobody had actually read."""
    sid = sequences.create_sequence(conn, "S", "email", [{"day_offset": 0, "body": "hi"}])
    sequences.enroll_leads(conn, sid, [1])
    res = replies.process_messages(conn, [{
        "from_addr": "hello+noreply@alpha.com", "from_name": "Hello - Website Queries",
        "subject": "Re: LED", "body": EIDIM_AUTO, "received_at": ""}])
    assert res["replies"] == 0 and res["auto"] == 1
    assert conn.execute(
        "SELECT status FROM outreach WHERE lead_no=1 AND channel='email'"
    ).fetchone()["status"] == "messaged"
    assert [d["lead_no"] for d in sequences.due_queue(conn)] == [1]


def test_auto_reply_is_visible_but_creates_no_task(conn):
    from app import activities
    activities.ensure_schema(conn)
    replies.process_messages(conn, [{
        "from_addr": "sales@alpha.com", "subject": "Out of office",
        "body": EIDIM_AUTO, "received_at": ""}])
    row = conn.execute("SELECT kind FROM inbox_messages WHERE lead_no=1").fetchone()
    assert row["kind"] == "auto"
    assert conn.execute("SELECT COUNT(*) c FROM activities").fetchone()["c"] == 0


def test_no_reply_address_never_becomes_a_contact(conn):
    """'hello+noreply@' is not a person to sell to, however the mail is classified."""
    replies.process_messages(conn, [{
        "from_addr": "hello+noreply@alpha.com", "from_name": "Hello",
        "subject": "Re: LED", "body": "sure, send pricing", "received_at": ""}])
    assert conn.execute(
        "SELECT COUNT(*) c FROM contacts WHERE email LIKE '%noreply%'"
    ).fetchone()["c"] == 0


def test_auto_submitted_header_is_enough(conn):
    res = replies.process_messages(conn, [{
        "from_addr": "someone@alpha.com", "subject": "Re: LED",
        "body": "안녕하세요, 자료 잘 받았습니다.", "auto_submitted": True,
        "received_at": ""}])
    assert res["auto"] == 1 and res["replies"] == 0


def test_real_reply_still_becomes_a_contact_and_a_task(conn):
    res = replies.process_messages(conn, [{
        "from_addr": "john@alpha.com", "from_name": "John",
        "subject": "Re: LED", "body": "please send pricing for P2.5", "received_at": ""}])
    assert res["replies"] == 1 and res["auto"] == 0
    assert conn.execute(
        "SELECT COUNT(*) c FROM contacts WHERE email='john@alpha.com'"
    ).fetchone()["c"] == 1
    assert conn.execute("SELECT COUNT(*) c FROM activities").fetchone()["c"] == 1
