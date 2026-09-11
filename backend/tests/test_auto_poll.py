"""Reply polling keeps the inbox current without a manual click, but it must be
impossible for it to crash the app or run when unwanted."""
import pytest

from app import background_jobs, scheduler
from app.db import connect, init_schema


def test_disabled_by_env_never_touches_anything(monkeypatch):
    monkeypatch.setenv("OUTREACH_AUTO_POLL", "0")
    monkeypatch.setattr("app.channels.email_adapter.get_password",
                        lambda: (_ for _ in ()).throw(AssertionError("must not be called")))
    assert background_jobs.email_poll("unused.db") == {"status": "disabled"}


def test_database_failure_is_returned_to_the_runtime_recorder(monkeypatch):
    monkeypatch.setenv("OUTREACH_AUTO_POLL", "1")
    monkeypatch.setattr("app.channels.email_adapter.get_password", lambda: "")
    monkeypatch.setattr("app.background_jobs.connect",
                        lambda path: (_ for _ in ()).throw(OSError("db unavailable")))
    with pytest.raises(OSError, match="db unavailable"):
        background_jobs.email_poll("unavailable.db")


def test_poll_failure_is_returned_to_the_runtime_recorder(monkeypatch, tmp_path):
    monkeypatch.setenv("OUTREACH_AUTO_POLL", "1")
    monkeypatch.setattr("app.channels.email_adapter.get_password", lambda: "pw")
    path = str(tmp_path / "t.db")
    c = connect(path); init_schema(c); c.close()
    monkeypatch.setattr("app.replies.poll_all_replies",
                        lambda conn, **kw: (_ for _ in ()).throw(OSError("imap down")))
    with pytest.raises(OSError, match="imap down"):
        background_jobs.email_poll(path)


def test_poll_reports_success_and_failure(monkeypatch, tmp_path):
    """The loop needs a truthful answer to decide retry-fast vs settle-down."""
    monkeypatch.setenv("OUTREACH_AUTO_POLL", "1")
    path = str(tmp_path / "t.db")
    c = connect(path); init_schema(c); c.close()

    monkeypatch.setattr("app.replies.poll_all_replies", lambda conn, **kw: {"errors": []})
    assert background_jobs.email_poll(path)["errors"] == []

    monkeypatch.setattr("app.replies.poll_all_replies",
                        lambda conn, **kw: {"errors": [{"email": "a@b.c", "error": "timeout"}]})
    failed = background_jobs.email_poll(path)
    assert failed["errors"][0]["error"] == "timeout"


def test_loop_retries_fast_until_first_success(monkeypatch):
    """Regression: the startup-only poll died on the logon-time network timeout and
    nothing ever retried, so replies stayed invisible."""
    monkeypatch.setenv("OUTREACH_AUTO_POLL", "1")
    outcomes = iter([False, False, True])
    slept = []

    def fake_sleep(seconds):
        slept.append(seconds)
        if len(slept) == 3:
            raise KeyboardInterrupt  # break out of the infinite loop

    def leased(*_args, **_kwargs):
        ok = next(outcomes)
        return {"acquired": True, "cycle_ok": ok, "email_poll_ok": ok}

    monkeypatch.setattr(scheduler.runtime, "run_leased_cycle", leased)
    with pytest.raises(KeyboardInterrupt):
        scheduler.run_forever(
            "unused.db", lambda: True, poll_seconds=900, retry_seconds=60,
            sleep_fn=fake_sleep,
        )
    assert slept == [60, 60, 900]


def test_disabling_email_poll_keeps_scheduler_alive(monkeypatch, tmp_path):
    """Email sync is one capability, not the switch for the whole autonomous operator."""
    monkeypatch.setenv("OUTREACH_AUTO_POLL", "0")
    calls = []
    path = str(tmp_path / "cycle.db")
    c = connect(path); init_schema(c); c.close()
    monkeypatch.setattr(background_jobs, "social_scan", lambda _p: calls.append("social") or True)
    monkeypatch.setattr(background_jobs, "website_recheck", lambda _p: calls.append("recheck") or True)
    monkeypatch.setattr(background_jobs, "sequence_maintenance", lambda _p: calls.append("prune") or True)
    monkeypatch.setattr(background_jobs, "email_send", lambda _p: True)
    monkeypatch.setattr(background_jobs, "social_send", lambda _p: True)
    monkeypatch.setattr(background_jobs, "contact_names", lambda _p: True)
    monkeypatch.setattr(background_jobs, "agent", lambda _p: calls.append("agent") or True)

    assert background_jobs.run_cycle(path) is True
    assert calls == ["social", "recheck", "prune", "agent"]
