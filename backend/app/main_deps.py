import os
import sqlite3

from app.db import connect

DB_PATH = os.environ.get("OUTREACH_DB", "outreach.db")


def get_conn() -> sqlite3.Connection:
    conn = connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def database_path(conn: sqlite3.Connection) -> str:
    """Return the file backing the request connection for deferred work.

    Dependency overrides are allowed to point a request at a preview or test database.
    Falling back to the process default here would make the background half of the same
    request operate on a different customer book.
    """
    rows = conn.execute("PRAGMA database_list").fetchall()
    for row in rows:
        name = row["name"] if isinstance(row, sqlite3.Row) else row[1]
        if name == "main":
            path = row["file"] if isinstance(row, sqlite3.Row) else row[2]
            if path:
                return str(path)
            break
    raise RuntimeError("background work requires a file-backed SQLite database")
