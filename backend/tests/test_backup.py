import os
import sqlite3

from app.main import BACKUP_KEEP, backup_db


def test_backup_creates_dated_copy(tmp_path):
    db = tmp_path / "outreach.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE sample(value TEXT)")
    conn.execute("INSERT INTO sample VALUES ('data')")
    conn.commit(); conn.close()
    dest = backup_db(str(db))
    assert dest and os.path.isfile(dest)
    assert os.path.dirname(dest).endswith("backups")
    copied = sqlite3.connect(dest)
    assert copied.execute("SELECT value FROM sample").fetchone()[0] == "data"
    copied.close()


def test_backup_idempotent_same_day(tmp_path):
    db = tmp_path / "outreach.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE sample(value TEXT)")
    conn.execute("INSERT INTO sample VALUES ('v1')")
    conn.commit(); conn.close()
    dest = backup_db(str(db))
    conn = sqlite3.connect(db)
    conn.execute("UPDATE sample SET value='v2'")
    conn.commit(); conn.close()
    backup_db(str(db))  # same day: must NOT overwrite the morning snapshot
    copied = sqlite3.connect(dest)
    assert copied.execute("SELECT value FROM sample").fetchone()[0] == "v1"
    copied.close()


def test_backup_missing_db_noop(tmp_path):
    assert backup_db(str(tmp_path / "nope.db")) is None


def test_backup_prunes_old(tmp_path):
    db = tmp_path / "outreach.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE sample(value TEXT)")
    conn.commit(); conn.close()
    bdir = tmp_path / "backups"
    bdir.mkdir()
    for i in range(20):
        (bdir / f"outreach-2026-01-{i + 1:02d}.db").write_bytes(b"old")
    backup_db(str(db))
    assert len(list(bdir.glob("outreach-*.db"))) == BACKUP_KEEP


def test_backup_includes_committed_wal_rows(tmp_path):
    db = tmp_path / "outreach.db"
    live = sqlite3.connect(db)
    live.execute("PRAGMA journal_mode=WAL")
    live.execute("PRAGMA wal_autocheckpoint=0")
    live.execute("CREATE TABLE sample(value TEXT)")
    live.execute("INSERT INTO sample VALUES ('latest deal')")
    live.commit()
    assert os.path.exists(str(db) + "-wal")

    dest = backup_db(str(db))
    copied = sqlite3.connect(dest)
    assert copied.execute("SELECT value FROM sample").fetchone()[0] == "latest deal"
    copied.close(); live.close()
