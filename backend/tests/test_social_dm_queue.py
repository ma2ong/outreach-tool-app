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


def test_a_lead_with_a_hook_is_queued_before_one_without(conn):
    """docs/80 replaced the old rule here. It used to be that a company with no hook was
    left out entirely; Allen's call is that a generic trade-to-trade opener is fine, so
    the ranking does the work instead of an exclusion."""
    conn.execute("UPDATE leads SET hook='' WHERE no <= 55")
    conn.commit()
    social_queue.build_today(conn, now=_monday())
    queued = [r["lead_no"] for r in conn.execute(
        "SELECT lead_no FROM social_dm_queue ORDER BY rank_order")]
    assert queued
    hooked = [no for no in queued if no > 55]
    assert hooked, "the five companies with a hook should all be in"
    assert queued[:len(hooked)] == hooked, "hooks first, then the generic ones"


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


def test_the_sentence_shape_varies_too(conn):
    """The first real run produced 31 messages differing only in the hook: same opening,
    same clause order, same closing. A platform reads the pattern, not the nouns."""
    social_queue.build_today(conn, now=_monday())
    bodies = [r["body"] for r in conn.execute("SELECT body FROM social_dm_queue")]
    assert len(bodies) >= 5
    openings = {b.split(".")[-2][-30:] for b in bodies if b.count(".") >= 2}
    assert len(openings) > 1, "所有私信的句式一模一样，只换了名词"


# --- docs/80: no hook is not a reason not to write ---------------------------------

@pytest.fixture
def bare(tmp_path):
    """Only the companies each test puts there: the shared fixture's 60 leads all carry
    hooks and would fill the day's allowance before these ever ranked."""
    c = connect(str(tmp_path / "bare.db"))
    init_schema(c)
    return c


def _add(conn, no, handle, tags=None, hook=None):
    conn.execute("INSERT INTO leads(no, company_en, country, instagram, tags, hook)"
                 " VALUES (?,?,'USA',?,?,?)", (no, f"Co{no}", handle, tags, hook))
    conn.commit()


def _body(conn, no):
    row = conn.execute("SELECT body FROM social_dm_queue WHERE lead_no=?", (no,)).fetchone()
    assert row is not None, f"lead {no} never made the queue"
    return row["body"]


def test_a_company_with_no_hook_still_gets_a_dm(bare):
    """It used to be excluded outright, while email had always written to it."""
    _add(bare, 900, "silentco", tags="工程商")
    social_queue.build_today(bare, now=_monday())
    body = _body(bare, 900)
    assert "{hook}" not in body
    # The hook templates all point back at a sentence that would not be there.
    for dangling in ("that kind of work", "exactly this", "the sort of work"):
        assert dangling not in body


def test_the_generic_message_follows_the_customer_type(bare):
    """docs/80 R2. 工程商 is an installer, 租赁商 rents — the letter leads with each."""
    _add(bare, 901, "installco", tags="工程商")
    _add(bare, 902, "rentco", tags="租赁商")
    social_queue.build_today(bare, now=_monday())
    install, rental = _body(bare, 901), _body(bare, 902)
    assert "integrator" in install or "install" in install
    assert "rental" in rental or "stage" in rental


def test_two_companies_in_one_segment_do_not_get_the_same_sentence(bare):
    """docs/52 R6: a platform reads the shape, not the nouns."""
    _add(bare, 910, "aco", tags="工程商")
    _add(bare, 911, "bco", tags="工程商")
    social_queue.build_today(bare, now=_monday())
    assert _body(bare, 910) != _body(bare, 911)


def test_a_company_with_a_hook_still_gets_the_hook_message(bare):
    _add(bare, 920, "loudco", hook="Saw the arena job on your site.")
    social_queue.build_today(bare, now=_monday())
    assert "Saw the arena job on your site." in _body(bare, 920)


def test_a_hook_still_outranks_a_generic_opener(bare):
    """docs/80 R3. Eight to fifteen slots a day; the ones we can open with something
    specific spend them first."""
    _add(bare, 930, "generic1", tags="工程商")
    _add(bare, 931, "specific", hook="Saw the arena job on your site.")
    _add(bare, 932, "generic2", tags="工程商")
    social_queue.build_today(bare, now=_monday())
    order = [r["lead_no"] for r in bare.execute(
        "SELECT lead_no FROM social_dm_queue ORDER BY rank_order")]
    assert order[0] == 931


def test_a_price_is_still_refused_in_a_generic_message(bare):
    """docs/80 R3.1. Only the personalization half of the guard is dropped; the price
    check runs before the channel gate and applies to every channel."""
    from app import message_guard
    lead = {"no": 940, "company_en": "Co940", "hook": ""}
    verdict = message_guard.check(
        "Hi, we manufacture LED panels. P2.5 at USD 320 per sqm.", lead,
        channel="instagram")
    assert verdict.blocked and verdict.reason == "pricing"
