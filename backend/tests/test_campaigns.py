import pytest

from app import campaigns, channel_outreach, outreach, repository
from app.browser_engine import FakeEngine
from app.db import connect, init_schema


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, email) VALUES
            (1,'A','USA','a@a.com'),(2,'B','USA','b@b.com'),
            (3,'C','Brazil','c@c.com'),(4,'D','Brazil','d@d.com');
    """)
    c.commit()
    return c


def test_send_campaign_logs_with_label(conn):
    outreach.send_campaign(conn, [1, 2], subject="S", body="B", attachment=None,
                           sender=lambda *a: None, delay_range=(0, 0), campaign="七月美国话术A")
    rows = conn.execute("SELECT campaign, channel FROM send_log").fetchall()
    assert len(rows) == 2
    assert all(r["campaign"] == "七月美国话术A" and r["channel"] == "email" for r in rows)


def test_campaign_stats_reply_attribution(conn):
    outreach.send_campaign(conn, [1, 2], subject="S", body="B", attachment=None,
                           sender=lambda *a: None, delay_range=(0, 0), campaign="话术A")
    outreach.send_campaign(conn, [3], subject="S", body="B", attachment=None,
                           sender=lambda *a: None, delay_range=(0, 0), campaign="话术B")
    repository.mark_replied(conn, 1, "email")
    stats = {s["campaign"]: s for s in campaigns.campaign_stats(conn)}
    assert stats["话术A"]["leads"] == 2 and stats["话术A"]["replied"] == 1
    assert stats["话术A"]["reply_rate"] == 50.0
    assert stats["话术B"]["replied"] == 0


def test_default_label_when_no_campaign(conn):
    outreach.send_campaign(conn, [1], subject="S", body="B", attachment=None,
                           sender=lambda *a: None, delay_range=(0, 0))
    row = conn.execute("SELECT campaign FROM send_log").fetchone()
    assert row["campaign"].startswith("email 20")


def test_country_stats(conn):
    for no in (1, 2, 3, 4):
        conn.execute("INSERT INTO outreach(lead_no, channel, status) VALUES (?, 'email', 'messaged')", (no,))
    conn.commit()
    repository.mark_replied(conn, 3, "email")
    rows = {r["country"]: r for r in campaigns.country_stats(conn, min_touched=2)}
    assert rows["Brazil"]["touched"] == 2 and rows["Brazil"]["replied"] == 1
    assert rows["Brazil"]["reply_rate"] == 50.0
    assert rows["USA"]["replied"] == 0
    # Brazil sorts first (higher reply rate)
    assert campaigns.country_stats(conn, min_touched=2)[0]["country"] == "Brazil"


def test_template_lang_roundtrip(conn):
    tid = repository.add_template(conn, "ES 开场", "whatsapp", None, "Hola {name}", lang="es")
    t = next(x for x in repository.list_templates(conn) if x.id == tid)
    assert t.lang == "es"


def test_one_bulk_touch_per_lead_per_day_across_channels(conn):
    conn.execute("UPDATE leads SET phone='+1 555 100 2000', instagram='a_ig' WHERE no=1")
    conn.commit()
    outreach.send_campaign(
        conn, [1], subject="S", body="B", attachment=None,
        sender=lambda *a: None, delay_range=(0, 0),
    )
    assert campaigns.contacted_today(conn, 1)
    assert channel_outreach.eligible(conn, [1], "whatsapp") == []
    assert channel_outreach.eligible(conn, [1], "instagram") == []
    result = channel_outreach.send_channel_campaign(
        conn, [1], "whatsapp", "Hi", FakeEngine(), delay_range=(0, 0),
    )
    assert result["sent"] == 0


def test_quality_stats_splits_reply_rate_by_email_quality(conn):
    conn.execute("UPDATE leads SET email_status='role' WHERE no IN (1,2)")
    conn.execute("UPDATE leads SET email_status='valid' WHERE no IN (3,4)")
    conn.commit()
    outreach.send_campaign(conn, [1, 2, 3, 4], subject="S", body="B", attachment=None,
                           sender=lambda *a: None, delay_range=(0, 0))
    repository.mark_replied(conn, 3, "email")
    rows = {r["quality"]: r for r in campaigns.quality_stats(conn)}
    assert rows["role"]["touched"] == 2 and rows["role"]["replied"] == 0
    assert rows["role"]["reply_rate"] == 0.0
    assert rows["valid"]["touched"] == 2 and rows["valid"]["replied"] == 1
    assert rows["valid"]["reply_rate"] == 50.0


def test_quality_stats_buckets_never_verified_separately(conn):
    outreach.send_campaign(conn, [1], subject="S", body="B", attachment=None,
                           sender=lambda *a: None, delay_range=(0, 0))
    assert campaigns.quality_stats(conn)[0]["quality"] == "unverified"


def test_quality_stats_ignores_browser_channels(conn):
    """email_status says nothing about a WhatsApp send — counting those would
    make the role/valid split read as better than it is."""
    conn.execute("UPDATE leads SET email_status='role', phone='+1 555 100 2000' WHERE no=1")
    conn.commit()
    channel_outreach.send_channel_campaign(
        conn, [1], "whatsapp", "Hi", FakeEngine(), delay_range=(0, 0))
    assert campaigns.quality_stats(conn) == []


def test_deliverability_flags_a_reputation_risk(conn):
    outreach.send_campaign(conn, [1, 2, 3, 4], subject="S", body="B", attachment=None,
                           sender=lambda *a: None, delay_range=(0, 0))
    conn.execute("UPDATE leads SET bounced_at=datetime('now') WHERE no=1")
    conn.commit()
    d = campaigns.deliverability(conn)
    assert d["sends"] == 4 and d["bounced"] == 1
    assert d["bounce_rate"] == 25.0 and d["danger"] is True


def test_deliverability_ignores_a_bounce_older_than_the_window(conn):
    """The alarm is about the list being sent now, not one cleaned up months ago."""
    outreach.send_campaign(conn, [1, 2, 3, 4], subject="S", body="B", attachment=None,
                           sender=lambda *a: None, delay_range=(0, 0))
    conn.execute("UPDATE leads SET bounced_at='2026-01-01T00:00:00+00:00' WHERE no=1")
    conn.commit()
    d = campaigns.deliverability(conn, days=30)
    assert d["bounced"] == 0 and d["danger"] is False


def test_deliverability_quiet_when_nothing_sent(conn):
    d = campaigns.deliverability(conn)
    assert d["sends"] == 0 and d["bounce_rate"] == 0.0 and d["danger"] is False


def test_deliverability_admits_when_it_cannot_see_bounces(conn):
    """A broken inbox poll must not read as a clean bounce rate: no IMAP, no bounces."""
    from app import settings
    outreach.send_campaign(conn, [1, 2, 3, 4], subject="S", body="B", attachment=None,
                           sender=lambda *a: None, delay_range=(0, 0))
    assert campaigns.deliverability(conn)["blind"] is True   # never polled at all
    settings.set_value(conn, "reply_sync_last_status", "success")
    assert campaigns.deliverability(conn)["blind"] is False
    settings.set_value(conn, "reply_sync_last_status", "error")
    assert campaigns.deliverability(conn)["blind"] is True


def test_deliverability_is_blind_while_a_send_only_mailbox_is_active(conn):
    """The trap: replies still arrive via Reply-To so the sweep reads 'success', while
    every bounce goes to the envelope sender's unreadable mailbox."""
    from app import mailboxes, settings
    outreach.send_campaign(conn, [1, 2, 3, 4], subject="S", body="B", attachment=None,
                           sender=lambda *a: None, delay_range=(0, 0))
    settings.set_value(conn, "reply_sync_last_status", "success")
    assert campaigns.deliverability(conn)["blind"] is False

    mid = mailboxes.add_mailbox(conn, "send@only.com", "smtp.only.com", 465,
                                "send@only.com", "pw", imap_enabled=False)
    assert campaigns.deliverability(conn)["blind"] is True
    mailboxes.set_active(conn, mid, False)
    assert campaigns.deliverability(conn)["blind"] is False


def test_a_mailbox_that_can_receive_does_not_blind_the_meter(conn):
    from app import mailboxes, settings
    settings.set_value(conn, "reply_sync_last_status", "success")
    mailboxes.add_mailbox(conn, "both@ok.com", "smtp.ok.com", 465, "both@ok.com", "pw")
    assert campaigns.deliverability(conn)["blind"] is False
