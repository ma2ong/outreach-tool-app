"""The daily social DM queue: prepared by the Agent, sent only when Allen presses send.

`AGENTS.md` still forbids auto-starting a WhatsApp/Instagram/Facebook conversation, and
`channel_outreach.py` carries the reason in a comment: exceeding ~20 in one run got the
WhatsApp account rate-limited on 2026-05-15. So these tests care about two things — that
the preparation is good enough to be worth a click, and that nothing here ever sends.
"""
import datetime as dt

import pytest

from app import social_queue
from app.db import connect, init_schema


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    # Each lead carries its own hook, the way enrich writes one per website. Several
    # companies do legitimately end up with the same sentence, which is what
    # test_two_identical_dms_never_go_out_the_same_day covers separately.
    rows = []
    for i in range(1, 61):
        rows.append(f"({i}, 'Co{i}', 'USA', 'c{i}@x.com', '+1555000{i:04d}',"
                    f" 'ig{i}', 'fb{i}', 'Saw the P{i} video wall on your site.')")
    c.executescript(
        "INSERT INTO leads(no, company_en, country, email, phone, instagram, facebook, hook)"
        f" VALUES {', '.join(rows)};")
    c.commit()
    return c


def _monday(hour: int = 10) -> dt.datetime:
    return dt.datetime(2026, 8, 24, hour, 0)  # a Monday


def _saturday(hour: int = 10) -> dt.datetime:
    return dt.datetime(2026, 8, 29, hour, 0)


# ---------------------------------------------------------------- pacing

def test_a_day_takes_between_eight_and_fifteen_per_channel(conn):
    """Not the old 40/40/20 daily cap: a script sending its full allowance every day at
    the same time is the pattern platforms recognise first."""
    result = social_queue.build_today(conn, now=_monday())
    per_channel = result["per_channel"]
    for channel in ("whatsapp", "instagram"):
        assert 8 <= per_channel[channel] <= 15, (channel, per_channel)
    assert per_channel["facebook"] <= per_channel["instagram"]


def test_the_daily_number_is_not_the_same_every_day(conn):
    """A fixed number is a signature just like a fixed hour is."""
    social_queue.ensure_schema(conn)
    seen = set()
    for day in range(1, 15):
        conn.execute("DELETE FROM social_dm_queue")
        conn.commit()
        seen.add(social_queue.build_today(
            conn, now=dt.datetime(2026, 9, day, 10, 0))["per_channel"]["instagram"])
    assert len(seen) > 1, "每天条数一样就等于签名"


def test_weekends_are_quieter(conn):
    """Nobody sends a batch of cold DMs to strangers at the same rate on a Saturday."""
    weekday = social_queue.build_today(conn, now=_monday())["per_channel"]["instagram"]
    conn.execute("DELETE FROM social_dm_queue")
    conn.commit()
    weekend = social_queue.build_today(conn, now=_saturday())["per_channel"]["instagram"]
    assert weekend < weekday


# ---------------------------------------------------------------- who gets picked

def test_one_company_never_lands_in_two_channels_on_the_same_day(conn):
    """From the customer's side that is harassment; from the platform's, batch behaviour."""
    social_queue.build_today(conn, now=_monday())
    dupes = conn.execute(
        "SELECT lead_no, COUNT(*) c FROM social_dm_queue GROUP BY lead_no HAVING c > 1"
    ).fetchall()
    assert dupes == []


def test_a_lead_getting_email_today_is_left_alone(conn):
    """We only just finished cleaning up leads enrolled in two sequences at once."""
    sid = conn.execute("INSERT INTO sequences(name, channel, active, created_at)"
                       " VALUES ('S','email',1,'2026-08-01')").lastrowid
    conn.execute("INSERT INTO sequence_steps(sequence_id, step_order, day_offset, body)"
                 " VALUES (?,0,0,'Hi {company}')", (sid,))
    conn.execute("INSERT INTO sequence_enrollments"
                 "(lead_no, sequence_id, current_step, status, enrolled_at, next_due_date)"
                 " VALUES (1, ?, 0, 'active', '2026-08-01', '2026-08-24')", (sid,))
    conn.commit()
    social_queue.build_today(conn, now=_monday())
    assert conn.execute("SELECT 1 FROM social_dm_queue WHERE lead_no=1").fetchone() is None


def test_a_lead_with_nothing_to_say_about_it_is_not_queued(conn):
    """A cold DM that says nothing about the recipient is worse than a cold email: an
    email at least has a subject line, a DM is only that one sentence."""
    conn.execute("UPDATE leads SET hook='' WHERE no <= 55")
    conn.commit()
    social_queue.build_today(conn, now=_monday())
    queued = {r["lead_no"] for r in conn.execute("SELECT lead_no FROM social_dm_queue")}
    assert queued and all(no > 55 for no in queued)


def test_buying_signals_come_first(conn):
    """Eight to fifteen is a small allowance, so the order is the whole value."""
    from app import sales_intelligence

    sales_intelligence.ensure_schema(conn)
    conn.execute(
        "INSERT INTO buying_signals(lead_no, signal_type, headline, evidence, source_url,"
        " captured_at, confidence, status, fingerprint, created_at, updated_at)"
        " VALUES (42,'tender','New arena RFQ','RFQ posted','http://x','2026-08-20',"
        " 90, 'new', 'fp-42', '2026-08-20', '2026-08-20')")
    conn.commit()
    social_queue.build_today(conn, now=_monday())
    first = conn.execute(
        "SELECT lead_no FROM social_dm_queue ORDER BY rank_order LIMIT 1").fetchone()
    assert first["lead_no"] == 42


# ---------------------------------------------------------------- the copy

def test_the_queue_holds_the_finished_message(conn):
    """Allen sends what he reads; nothing is left to substitute at send time."""
    social_queue.build_today(conn, now=_monday())
    row = conn.execute("SELECT body FROM social_dm_queue LIMIT 1").fetchone()
    assert "{" not in row["body"]
    assert "video wall on your site" in row["body"]


def test_copy_the_guard_would_hold_never_reaches_the_queue(conn):
    """And the reason is kept: it usually means that lead's hook needs fixing."""
    conn.execute("UPDATE leads SET hook='We offer USD 1,200 per sqm.' WHERE no<=60")
    conn.commit()
    result = social_queue.build_today(conn, now=_monday())
    assert conn.execute("SELECT COUNT(*) c FROM social_dm_queue").fetchone()["c"] == 0
    assert result["held"] > 0
    assert any("pricing" in h["reason"] for h in result["holds"])


def test_an_edited_message_is_never_overwritten(conn):
    social_queue.build_today(conn, now=_monday())
    row = conn.execute("SELECT id FROM social_dm_queue LIMIT 1").fetchone()
    social_queue.edit(conn, row["id"], "Allen 自己改过的一句话")
    social_queue.build_today(conn, now=_monday())
    kept = conn.execute("SELECT body, edited FROM social_dm_queue WHERE id=?",
                        (row["id"],)).fetchone()
    assert kept["body"] == "Allen 自己改过的一句话" and kept["edited"] == 1


# ---------------------------------------------------------------- the boundary

def test_yesterdays_queue_does_not_survive_into_today(conn):
    """A three-day-old DM queue is stale, and stale queues become the next 89-item pile."""
    social_queue.build_today(conn, now=_monday())
    yesterday_ids = {r["id"] for r in conn.execute("SELECT id FROM social_dm_queue")}
    social_queue.build_today(conn, now=_monday() + dt.timedelta(days=1))
    today = social_queue.today(conn, now=_monday() + dt.timedelta(days=1))
    assert yesterday_ids.isdisjoint({row["id"] for row in today})


def test_building_the_queue_sends_nothing(conn, monkeypatch):
    """The one rule this whole feature exists to keep."""
    import app.channel_outreach as co

    def explode(*args, **kwargs):
        raise AssertionError("队列生成绝不允许发送任何东西")

    monkeypatch.setattr(co, "send_channel_campaign", explode)
    social_queue.build_today(conn, now=_monday())


def test_two_identical_dms_never_go_out_the_same_day(conn):
    """A hook is generated from website keywords, so several companies legitimately end
    up with the same sentence — and two identical DMs in one morning is the plainest bot
    signature there is."""
    conn.execute("UPDATE leads SET hook='Saw the rental work on your site.'")
    conn.commit()
    result = social_queue.build_today(conn, now=_monday())
    bodies = [r["body"] for r in conn.execute("SELECT body FROM social_dm_queue")]
    assert len(bodies) == len(set(bodies))
    # The fixture gives every lead the same hook, so all but one are held, and the reason
    # says which lead needs a better opening line.
    assert result["held"] > 0
    assert any(h["reason"] == "duplicate" for h in result["holds"])
