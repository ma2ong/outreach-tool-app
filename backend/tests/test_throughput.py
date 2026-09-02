"""Did the work come out, not is the wire connected (docs/86 R2)."""
import datetime as dt

import pytest

from app import readiness, throughput


def _sent(conn, channel, day, n=1):
    for i in range(n):
        conn.execute(
            "INSERT INTO send_log(lead_no, channel, campaign, sent_at) VALUES (1,?,'test',?)",
            (channel, f"{day}T09:0{i}:00+00:00"))
    conn.commit()


TODAY = dt.date(2026, 9, 2)


def test_a_channel_that_ran_and_went_quiet_is_named(conn):
    _sent(conn, "instagram", "2026-08-26")
    rows = throughput.stalled(conn, TODAY)
    assert [r["channel"] for r in rows] == ["instagram"]
    assert rows[0]["quiet_days"] == 7
    assert "Instagram 已 7 天" in throughput.summary(conn, TODAY)


def test_a_channel_that_sent_today_is_fine(conn):
    _sent(conn, "email", "2026-09-02")
    assert throughput.stalled(conn, TODAY) == []


def test_a_channel_that_never_ran_is_not_called_stalled(conn):
    """It has not started, which is a different sentence and a different fix — saying
    'quiet for 300 days' about a channel nobody switched on is noise."""
    assert throughput.stalled(conn, TODAY) == []
    assert throughput.summary(conn, TODAY) == ""


def test_a_channel_switched_off_is_allowed_to_be_silent(conn):
    _sent(conn, "instagram", "2026-08-01")
    conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES"
                 " ('channel_autonomy_instagram','off')")
    conn.commit()
    assert throughput.stalled(conn, TODAY) == []


@pytest.mark.parametrize("channel,days,expected", [
    ("email", 2, True),      # daily pipeline: two days is already odd
    ("email", 1, False),
    ("instagram", 5, True),  # batched: a weekend of silence is normal
    ("instagram", 4, False),
])
def test_each_channel_gets_the_quiet_window_its_cadence_deserves(conn, channel, days, expected):
    _sent(conn, channel, (TODAY - dt.timedelta(days=days)).isoformat())
    assert bool(throughput.stalled(conn, TODAY)) is expected


def test_the_readiness_centre_carries_it(conn):
    _sent(conn, "instagram", "2026-08-01")
    ids = {c["id"]: c for c in readiness.build(conn)["checks"]}
    assert "throughput" in ids, "就绪中心必须带上产出检查"
