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
