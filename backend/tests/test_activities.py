import datetime as dt

import pytest

from app import activities, opportunities


def test_activity_lifecycle_syncs_the_lead_next_action(conn):
    today = dt.date.today()
    first = activities.create(conn, 1, {
        "title": "Call purchasing manager",
        "type": "call",
        "due_at": today.isoformat(),
        "priority": "high",
    })
    activities.create(conn, 1, {
        "title": "Send cabinet drawing",
        "due_at": (today + dt.timedelta(days=2)).isoformat(),
    })

    lead = conn.execute(
        "SELECT next_action, follow_up_date FROM leads WHERE no=1").fetchone()
    assert lead["next_action"] == "Call purchasing manager"
    assert lead["follow_up_date"] == today.isoformat()

    done = activities.complete(conn, first["id"])
    assert done["status"] == "done" and done["completed_at"]
    lead = conn.execute(
        "SELECT next_action, follow_up_date FROM leads WHERE no=1").fetchone()
    assert lead["next_action"] == "Send cabinet drawing"


def test_activity_scopes_and_stats(conn):
    today = dt.date.today()
    for title, due in (
        ("Overdue", today - dt.timedelta(days=1)),
        ("Today", today),
        ("Upcoming", today + dt.timedelta(days=1)),
    ):
        activities.create(conn, 1, {"title": title, "due_at": due.isoformat()})
    activities.create(conn, 2, {"title": "No due date"})

    assert [a["title"] for a in activities.list_all(conn, scope="overdue")] == ["Overdue"]
    assert [a["title"] for a in activities.list_all(conn, scope="today")] == ["Today"]
    assert [a["title"] for a in activities.list_all(conn, scope="upcoming")] == ["Upcoming"]
    assert [a["title"] for a in activities.list_all(conn, scope="no_due")] == ["No due date"]
    assert activities.stats(conn) == {
        "overdue": 1, "today": 1, "upcoming": 1, "no_due": 1, "open_count": 4}


def test_activity_requires_matching_lead_and_opportunity(conn):
    opportunity = opportunities.create(conn, 1, {"title": "Church P2.5"})
    with pytest.raises(activities.ActivityValidation, match="不一致"):
        activities.create(conn, 2, {
            "title": "Wrong buyer"}, opportunity_id=opportunity["id"])
    with pytest.raises(activities.ActivityValidation, match="YYYY-MM-DD"):
        activities.create(conn, 1, {"title": "Bad date", "due_at": "tomorrow"})


def test_opportunity_next_action_upserts_and_cancels_one_task(conn):
    opportunity = opportunities.create(conn, 1, {
        "title": "Rental P3.9",
        "next_action": "Confirm power system",
        "next_action_date": "2026-08-10",
    })
    rows = activities.list_all(conn, lead_no=1)
    assert len(rows) == 1 and rows[0]["source"] == "opportunity"

    opportunities.update(conn, opportunity["id"], {
        "next_action": "Send revised quote", "next_action_date": "2026-08-12"})
    rows = activities.list_all(conn, lead_no=1)
    assert len(rows) == 1 and rows[0]["title"] == "Send revised quote"

    opportunities.update(conn, opportunity["id"], {
        "stage": "lost", "loss_reason": "Budget cancelled"})
    assert activities.list_all(conn, lead_no=1) == []
    assert activities.list_all(conn, status="cancelled", lead_no=1)[0]["source"] == "opportunity"


def test_existing_next_action_and_pending_reply_migrate_once(conn):
    conn.execute(
        "UPDATE leads SET next_action='Call buyer', follow_up_date='2026-08-09' WHERE no=1")
    cur = conn.execute(
        "INSERT INTO inbox_messages(lead_no, channel, kind, from_addr, subject, body, received_at)"
        " VALUES (2, 'email', 'reply', 'buyer@beta.com', 'Re: LED', 'Price?', '2026-08-04')")
    conn.commit()

    first = activities.migrate_existing(conn)
    second = activities.migrate_existing(conn)
    assert first["created"] == 2 and second["created"] == 0
    assert conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0] == 2
    reply = conn.execute(
        "SELECT * FROM activities WHERE source_ref=?", (f"inbox:{cur.lastrowid}",)).fetchone()
    assert reply["priority"] == "high" and reply["status"] == "open"


def test_reply_task_is_idempotent_and_completes_with_inbox(conn):
    cur = conn.execute(
        "INSERT INTO inbox_messages(lead_no, channel, kind, from_addr, subject, body, received_at)"
        " VALUES (1, 'whatsapp', 'reply', '+1555', '', 'Please quote P2.6', '2026-08-04')")
    conn.commit()
    assert activities.create_reply_task(conn, cur.lastrowid)
    assert not activities.create_reply_task(conn, cur.lastrowid)
    activities.complete_reply_task(conn, cur.lastrowid)
    row = conn.execute("SELECT status FROM activities").fetchone()
    assert row["status"] == "done"


def test_lead_with_a_sales_task_is_never_bulk_cleanable(conn):
    from app import health
    conn.execute(
        "UPDATE leads SET website=NULL, instagram=NULL, email=NULL, phone=NULL, facebook=NULL WHERE no=2")
    conn.commit()
    assert 2 in {lead["no"] for lead in health.cleanable(conn)}
    activities.create(conn, 2, {"title": "Research purchasing contact"})
    assert 2 not in {lead["no"] for lead in health.cleanable(conn)}
