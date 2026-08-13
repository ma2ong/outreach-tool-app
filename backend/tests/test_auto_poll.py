"""Reply polling keeps the inbox current without a manual click, but it must be
impossible for it to crash the app or run when unwanted."""
import pytest

import app.main as main


def test_disabled_by_env_never_touches_anything(monkeypatch):
    monkeypatch.setenv("OUTREACH_AUTO_POLL", "0")
    monkeypatch.setattr("app.channels.email_adapter.get_password",
                        lambda: (_ for _ in ()).throw(AssertionError("must not be called")))
    main.auto_poll_replies()  # returns before looking at credentials


def test_no_password_skips_quietly(monkeypatch):
    monkeypatch.setenv("OUTREACH_AUTO_POLL", "1")
    monkeypatch.setattr("app.channels.email_adapter.get_password", lambda: "")
    monkeypatch.setattr(main, "connect",
                        lambda path: (_ for _ in ()).throw(OSError("db unavailable")))
    main.auto_poll_replies()  # best-effort startup task never crashes the app


def test_poll_failure_never_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("OUTREACH_AUTO_POLL", "1")
    monkeypatch.setattr("app.channels.email_adapter.get_password", lambda: "pw")
    monkeypatch.setattr(main, "DB_PATH", str(tmp_path / "t.db"))
    from app.db import connect, init_schema
    c = connect(str(tmp_path / "t.db")); init_schema(c); c.close()
    monkeypatch.setattr("app.replies.poll_all_replies",
                        lambda conn, **kw: (_ for _ in ()).throw(OSError("imap down")))
    main.auto_poll_replies()  # a network failure at startup is not an app failure


def test_poll_reports_success_and_failure(monkeypatch, tmp_path):
    """The loop needs a truthful answer to decide retry-fast vs settle-down."""
    monkeypatch.setenv("OUTREACH_AUTO_POLL", "1")
    monkeypatch.setattr(main, "DB_PATH", str(tmp_path / "t.db"))
    from app.db import connect, init_schema
    c = connect(str(tmp_path / "t.db")); init_schema(c); c.close()

    monkeypatch.setattr("app.replies.poll_all_replies", lambda conn, **kw: {"errors": []})
    assert main.auto_poll_replies() is True

    monkeypatch.setattr("app.replies.poll_all_replies",
                        lambda conn, **kw: {"errors": [{"email": "a@b.c", "error": "timeout"}]})
    assert main.auto_poll_replies() is False


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

    monkeypatch.setattr(main, "auto_poll_replies", lambda: next(outcomes))
    # The other three do real work against DB_PATH — website fetches, a browser window,
    # a write to the enrollment table. This test is about retry timing, so stub them:
    # left live they ran three rounds of production side effects on every test run.
    monkeypatch.setattr(main, "auto_scan_social", lambda: None)
    monkeypatch.setattr(main, "auto_recheck", lambda: None)
    monkeypatch.setattr(main, "auto_prune_sequences", lambda: None)
    monkeypatch.setattr(main.time, "sleep", fake_sleep)
    with pytest.raises(KeyboardInterrupt):
        main.reply_poll_loop()
    assert slept == [main.REPLY_RETRY_SECONDS, main.REPLY_RETRY_SECONDS,
                     main.REPLY_POLL_SECONDS]


def test_loop_disabled_by_env_returns_immediately(monkeypatch):
    monkeypatch.setenv("OUTREACH_AUTO_POLL", "0")
    monkeypatch.setattr(main.time, "sleep",
                        lambda s: (_ for _ in ()).throw(AssertionError("must not loop")))
    main.reply_poll_loop()
