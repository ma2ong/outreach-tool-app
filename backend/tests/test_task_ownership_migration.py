import sqlite3

from app import activities
from app.agent import task_ownership
from app.db import connect, init_schema


def test_existing_activities_table_gets_work_owner(tmp_path):
    db = str(tmp_path / "legacy-activities.db")
    conn = connect(db)
    init_schema(conn)
    activities.ensure_schema(conn)
    before = {row["name"] for row in conn.execute("PRAGMA table_info(activities)")}
    assert "work_owner" not in before

    task_ownership.ensure_schema(conn)

    after = {row["name"] for row in conn.execute("PRAGMA table_info(activities)")}
    assert "work_owner" in after
    index_names = {row["name"] for row in conn.execute("PRAGMA index_list(activities)")}
    assert "idx_activities_owner_status_due" in index_names
    conn.close()


def test_old_agent_proposals_without_execution_result_does_not_break_backfill(tmp_path):
    db = str(tmp_path / "legacy-proposals.db")
    conn = connect(db)
    init_schema(conn)
    activities.ensure_schema(conn)
    conn.execute(
        "CREATE TABLE agent_proposals ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, lead_no INTEGER,"
        "inbox_message_id INTEGER, status TEXT NOT NULL DEFAULT 'pending',"
        "created_at TEXT NOT NULL)"
    )
    conn.commit()

    result = task_ownership.backfill(conn)

    assert result["provenance_backfilled"] == 0
    assert result["owners_changed"] == 0
    assert "work_owner" in {
        row["name"] for row in conn.execute("PRAGMA table_info(activities)")
    }
    conn.close()
