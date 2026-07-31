import pytest
from app.db import connect, init_schema


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
