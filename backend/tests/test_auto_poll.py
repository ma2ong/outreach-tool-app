"""Startup auto-poll keeps the inbox current without a manual click, but it must be
impossible for it to crash the app or run when unwanted."""
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
