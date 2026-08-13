import pytest
from app.db import connect, init_schema


@pytest.fixture(autouse=True)
def _never_touch_the_live_db(tmp_path, monkeypatch):
    """No test may reach the real outreach.db.

    DB_PATH defaults to a bare 'outreach.db' and pytest runs from backend/, so any code
    path that connects by DB_PATH instead of the injected connection lands on the live
    lead base. That is not hypothetical: the poll-loop timing test ran auto_recheck and
    auto_scan_social against production on every single run — real website fetches, and
    a browser window whenever a channel happened to be logged in. Overriding the module
    attributes (not just the env var) closes it for good, whatever a test forgets.
    """
    from app import main, main_deps
    sandbox = str(tmp_path / "sandbox.db")
    monkeypatch.setenv("OUTREACH_DB", sandbox)
    monkeypatch.setattr(main_deps, "DB_PATH", sandbox)
    monkeypatch.setattr(main, "DB_PATH", sandbox)


@pytest.fixture(autouse=True)
def _auth_disabled(tmp_path, monkeypatch):
    """Tests run in local no-password mode; test_auth.py opts back in via its own paths."""
    from app import auth
    monkeypatch.setattr(auth, "PASSWORD_FILE", str(tmp_path / "no_pw.txt"))
    monkeypatch.setattr(auth, "SESSION_KEY_FILE", str(tmp_path / ".session_key"))
    # never let a test reach the real Gmail IMAP via the startup auto-poll
    monkeypatch.setenv("OUTREACH_AUTO_POLL", "0")
    monkeypatch.setenv("OUTREACH_AUTOSEND_SCHEDULER", "0")


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, website, instagram) VALUES
            (1, 'Alpha AV', 'USA', 'alpha.com', 'alphaig'),
            (2, 'Beta Screens', 'USA', 'beta.com', NULL),
            (3, 'Gamma LED', 'Brazil', 'gamma.com', 'gammaig');
        INSERT INTO outreach(lead_no, channel, status, touch_count, message_sent_date) VALUES
            (1, 'email', 'messaged', 1, '2026-07-01'),
            (2, 'email', 'prospect', 0, NULL),
            (1, 'instagram', 'messaged', 1, '2026-07-01'),
            (3, 'whatsapp', 'messaged', 1, '2026-06-30');
    """)
    c.commit()
    return c
