from app.db import connect, init_schema


def test_init_schema_creates_tables(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    init_schema(conn)
    names = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    assert {"leads", "outreach"} <= names
    inbox_cols = {row[1] for row in conn.execute("PRAGMA table_info(inbox_messages)")}
    assert {"handled_at", "contact_id"} <= inbox_cols
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 30000


def test_outreach_unique_lead_channel(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    init_schema(conn)
    conn.execute("INSERT INTO leads(no, company_en) VALUES (1, 'A')")
    conn.execute("INSERT INTO outreach(lead_no, channel, status) VALUES (1,'email','messaged')")
    import sqlite3
    import pytest
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO outreach(lead_no, channel, status) VALUES (1,'email','prospect')")
