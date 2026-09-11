from app import copy_experiments, copy_versions, sequence_edit, sequences
from app.agent import project_facts
from app import opportunities


def _sequence(conn):
    return sequences.create_sequence(conn, "Install v1", "email", [{
        "day_offset": 0,
        "subject": "A question for {company}",
        "body": "Saw your fixed installation work. Is indoor LED relevant this quarter?",
    }])


def test_sequence_edits_are_versioned_and_rollback_creates_another_version(conn):
    sid = _sequence(conn)
    sequence_edit.update_step(
        conn, sid, 0, subject="For {company}",
        body="Saw your installation work. Are you planning an indoor LED project?",
        day_offset=2,
    )
    versions = copy_versions.list_sequence_step(conn, sid, 0)
    assert [v["version"] for v in versions] == [2, 1]
    assert versions[-1]["body"].startswith("Saw your fixed")

    restored = copy_versions.rollback_sequence_step(conn, sid, 0, versions[-1]["id"])
    current = conn.execute(
        "SELECT subject,body,day_offset FROM sequence_steps WHERE sequence_id=? AND step_order=0",
        (sid,),
    ).fetchone()
    assert current["body"] == versions[-1]["body"]
    assert restored["version"] == 3
    assert restored["change_kind"] == "rollback"
    assert restored["rollback_of_id"] == versions[-1]["id"]


def test_copy_outcomes_include_meaningful_reply_requirements_and_opportunity_progress(conn):
    opportunities.ensure_schema(conn)
    project_facts.ensure_schema(conn)
    conn.execute(
        "INSERT INTO send_log(lead_no,channel,campaign,sent_at,variant,step,audience,market)"
        " VALUES (1,'email','Install','2026-09-09 10:00:00','Install v2',0,'install','USA')"
    )
    conn.execute(
        "INSERT INTO inbox_messages(lead_no,channel,kind,body,received_at)"
        " VALUES (1,'email','reply','Need 20 sqm P2.5 indoor','2026-09-09 11:00:00')"
    )
    message_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO project_fact_evidence(lead_no,source_message_id,field,value,normalized_value,"
        " source_quote,created_at) VALUES (1,?,'pixel_pitch','P2.5','2.5','P2.5','2026-09-09 11:00:00')",
        (message_id,),
    )
    conn.execute(
        "INSERT INTO opportunities(lead_no,title,stage,created_at,updated_at,last_activity_at)"
        " VALUES (1,'Lobby LED','qualified','2026-09-09','2026-09-09 12:00:00','2026-09-09')"
    )
    conn.commit()

    row = copy_experiments.breakdown(conn, by=("variant",), days=365)[0]
    assert row["meaningful_replies"] == 1
    assert row["requirements_captured"] == 1
    assert row["opportunities_progressed"] == 1
    assert row["sample_quality"] == "insufficient"
