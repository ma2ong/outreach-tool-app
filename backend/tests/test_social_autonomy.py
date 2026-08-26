"""The social DM autonomy switch: manual by default, auto only when Allen says so.

`AGENTS.md` used to forbid auto-starting a social conversation outright. `docs/53`
changes that in the open — the risk did not move, only the person deciding to spend it —
so these tests hold the parts that make the decision real: it must be typed, it is per
channel, and turning it on does not turn up the volume.
"""
import datetime as dt

import pytest

from app import social_autonomy, social_queue
from app.db import connect, init_schema


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    rows = ", ".join(
        f"({i}, 'Co{i}', 'USA', 'ig{i}', 'fb{i}', '+1555000{i:04d}',"
        f" 'Saw the P{i} video wall on your site.')"
        for i in range(1, 41))
    c.executescript("INSERT INTO leads(no, company_en, country, instagram, facebook, phone,"
                    f" hook) VALUES {rows};")
    c.commit()
    return c


def _monday(hour: int = 10) -> dt.datetime:
    return dt.datetime(2026, 8, 24, hour, 0)


# ---------------------------------------------------------------- the setting

def test_every_channel_starts_manual(conn):
    """Nothing may raise this on Allen's behalf — not a migration, not a default."""
    for channel in social_queue.CHANNELS:
        assert social_autonomy.get(conn, channel) == "manual"


def test_turning_on_auto_costs_a_typed_confirmation(conn):
    """Not a "are you sure" — the channel's own name, because this spends an account
    that cannot be recovered."""
    with pytest.raises(social_autonomy.ConfirmationRequired):
        social_autonomy.set_mode(conn, "instagram", "auto", confirm="")
    with pytest.raises(social_autonomy.ConfirmationRequired):
        social_autonomy.set_mode(conn, "instagram", "auto", confirm="whatsapp")
    social_autonomy.set_mode(conn, "instagram", "auto", confirm="instagram")
    assert social_autonomy.get(conn, "instagram") == "auto"


def test_the_switch_is_per_channel(conn):
    """The WhatsApp number and the Instagram account are not worth the same, so Allen
    may well automate one and confirm the other by hand."""
    social_autonomy.set_mode(conn, "instagram", "auto", confirm="instagram")
    assert social_autonomy.get(conn, "whatsapp") == "manual"
    assert social_autonomy.get(conn, "facebook") == "manual"


def test_going_back_down_needs_no_ceremony(conn):
    """Stopping is never the risky direction."""
    social_autonomy.set_mode(conn, "instagram", "auto", confirm="instagram")
    social_autonomy.set_mode(conn, "instagram", "manual")
    assert social_autonomy.get(conn, "instagram") == "manual"


def test_an_off_channel_is_not_even_prepared(conn):
    social_autonomy.set_mode(conn, "facebook", "off")
    social_queue.build_today(conn, now=_monday())
    queued = {r["channel"] for r in conn.execute("SELECT channel FROM social_dm_queue")}
    assert "facebook" not in queued


# ---------------------------------------------------------------- the pacing

def test_the_send_time_moves_every_day(conn):
    """A job that fires at the same minute daily is one of the plainest bot signatures,
    and a person pressing send never produces that pattern in the first place."""
    times = {social_autonomy.send_at(dt.date(2026, 9, day)) for day in range(1, 15)}
    assert len(times) > 1
    for moment in times:
        assert 9 <= moment.hour < 18


def test_auto_runs_once_a_day_and_does_not_chase_the_backlog(conn, monkeypatch):
    """Falling behind is fine. Catching up by sending twice is how an account gets
    rate-limited."""
    social_autonomy.set_mode(conn, "instagram", "auto", confirm="instagram")
    social_queue.build_today(conn, now=_monday())
    sent = []
    def fake(conn, items):
        sent.append(items)
        return {"sent": len(items), "failed": 0}

    monkeypatch.setattr(social_autonomy, "_deliver", fake)

    late = _monday(hour=23)
    assert social_autonomy.run_due(conn, now=late)["sent_batches"] == 1
    assert social_autonomy.run_due(conn, now=late)["sent_batches"] == 0
    assert len(sent) == 1


def test_manual_channels_are_never_sent_by_the_scheduler(conn, monkeypatch):
    """The rule the whole feature is built around: without the switch, nothing sends."""
    social_queue.build_today(conn, now=_monday())
    monkeypatch.setattr(social_autonomy, "_deliver",
                        lambda conn, items: (_ for _ in ()).throw(
                            AssertionError("manual 挡不允许自动发送")))
    assert social_autonomy.run_due(conn, now=_monday(hour=23))["sent_batches"] == 0


def test_switching_off_stops_the_next_run(conn, monkeypatch):
    social_autonomy.set_mode(conn, "instagram", "auto", confirm="instagram")
    social_autonomy.set_mode(conn, "instagram", "manual")
    social_queue.build_today(conn, now=_monday())
    monkeypatch.setattr(social_autonomy, "_deliver",
                        lambda conn, items: (_ for _ in ()).throw(AssertionError("关掉了还发")))
    assert social_autonomy.run_due(conn, now=_monday(hour=23))["sent_batches"] == 0


# ---------------------------------------------------------------- the record

def test_an_automatic_send_always_leaves_a_record(conn, monkeypatch):
    """Quiet when there is nothing to say (docs/48 R3), but a send spent account risk —
    that is never nothing."""
    social_autonomy.set_mode(conn, "whatsapp", "auto", confirm="whatsapp")
    social_queue.build_today(conn, now=_monday())
    monkeypatch.setattr(social_autonomy, "_deliver",
                        lambda conn, items: {"sent": len(items), "failed": 0})
    social_autonomy.run_due(conn, now=_monday(hour=23))
    log = social_autonomy.last_run(conn)
    assert log and log["channels"]["whatsapp"] > 0


def test_a_quiet_day_writes_no_noise(conn, monkeypatch):
    social_autonomy.set_mode(conn, "whatsapp", "auto", confirm="whatsapp")
    monkeypatch.setattr(social_autonomy, "_deliver", lambda conn, items: {"sent": 0, "failed": 0})
    social_autonomy.run_due(conn, now=_monday(hour=23))
    assert social_autonomy.last_run(conn) is None
