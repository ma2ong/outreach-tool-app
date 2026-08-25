import datetime as dt

from app import activities, contacts, sequences
from app.db import connect, init_schema
from app import fix_historical_auto_replies as repair


def _conn(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    init_schema(conn)
    contacts.ensure_schema(conn)
    activities.ensure_schema(conn)
    return conn


def _eidim_shape(conn):
    conn.execute(
        "INSERT INTO leads(no,company_en,country,email,phone,stage)"
        " VALUES (1,'Eidim','USA','hello@eidim.com','877-773-4346','replied')")
    conn.execute(
        "INSERT INTO outreach(lead_no,channel,status,touch_count,message_sent_date,reply_received)"
        " VALUES (1,'email','replied',2,'2026-08-13',0)")
    sid = sequences.create_sequence(conn, "Korean follow-up", "email", [
        {"day_offset": 0, "subject": "hello", "body": "hello"},
        {"day_offset": 3, "subject": "follow up", "body": "follow up"},
    ])
    conn.execute(
        "INSERT INTO sequence_enrollments(lead_no,sequence_id,current_step,status,enrolled_at,next_due_date)"
        " VALUES (1,?,1,'replied','2026-08-10','2026-08-16')", (sid,))
    now = "2026-08-25T01:15:20+00:00"
    sender = "hello+noreply@eidim.com"
    subject = "Re: 한국 LED 디스플레이 납품 사례"
    body = "This message is auto-reply. Please DO NOT reply to this email."
    cur = conn.execute(
        "INSERT INTO inbox_messages(lead_no,channel,kind,from_addr,subject,body,received_at)"
        " VALUES (1,'email','reply',?,?,?,?,?)", (sender, subject, body, now))
    reply_id = cur.lastrowid
    conn.execute(
        "INSERT INTO inbox_messages(lead_no,channel,kind,from_addr,subject,body,received_at)"
        " VALUES (1,'email','auto',?,?,?,?,?)", (sender, subject, body, now))
    stamp = "2026-08-25T01:16:00+00:00"
    conn.execute(
        "INSERT INTO contacts(lead_no,name,email,role,is_primary,source,created_at,updated_at)"
        " VALUES (1,'Hello - Website Queries',?,'other',0,'reply',?,?)",
        (sender, stamp, stamp))
    conn.execute(
        "INSERT INTO contacts(lead_no,email,role,is_primary,source,created_at,updated_at)"
        " VALUES (1,'hello@eidim.com','other',1,'legacy',?,?)", (stamp, stamp))
    conn.execute(
        "INSERT INTO activities(lead_no,type,title,due_at,priority,status,source,source_ref,created_at,updated_at)"
        " VALUES (1,'email','Reply customer','2026-08-25','high','open','reply',? ,?,?)",
        (f"inbox:{reply_id}", stamp, stamp))
    conn.commit()
    return reply_id, sid


def test_preview_is_read_only_and_eidim_is_strong_candidate(tmp_path):
    conn = _conn(tmp_path)
    reply_id, _ = _eidim_shape(conn)
    before = conn.total_changes
    result = repair.run(conn, apply=False, today=dt.date(2026, 8, 25))
    assert result["candidates"] == 1
    assert result["strong"] == 1
    assert result["manual_review"] == 0
    assert result["items"][0]["inbox_id"] == reply_id
    assert result["items"][0]["duplicate_auto_id"] is not None
    assert conn.total_changes == before
    assert conn.execute("SELECT kind FROM inbox_messages WHERE id=?", (reply_id,)).fetchone()[0] == "reply"


def test_apply_repairs_duplicate_auto_state_without_guessing_stage(tmp_path):
    conn = _conn(tmp_path)
    reply_id, sid = _eidim_shape(conn)
    result = repair.run(conn, apply=True, today=dt.date(2026, 8, 25))
    assert result["applied"] == 1
    assert conn.execute("SELECT COUNT(*) FROM inbox_messages WHERE lead_no=1 AND kind='reply'").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM inbox_messages WHERE lead_no=1 AND kind='auto'").fetchone()[0] == 1
    assert conn.execute("SELECT kind FROM inbox_messages WHERE id=?", (reply_id,)).fetchone()[0] == "auto"
    outreach = conn.execute(
        "SELECT status,touch_count,reply_received FROM outreach WHERE lead_no=1 AND channel='email'"
    ).fetchone()
    assert tuple(outreach) == ("messaged", 2, 0)
    activity = conn.execute(
        "SELECT status FROM activities WHERE source='reply' AND source_ref=?", (f"inbox:{reply_id}",)
    ).fetchone()
    assert activity["status"] == "cancelled"
    assert conn.execute(
        "SELECT COUNT(*) FROM contacts WHERE email='hello+noreply@eidim.com'"
    ).fetchone()[0] == 0
    assert conn.execute(
        "SELECT COUNT(*) FROM contacts WHERE email='hello@eidim.com' AND is_primary=1"
    ).fetchone()[0] == 1
    enrollment = conn.execute(
        "SELECT status,next_due_date FROM sequence_enrollments WHERE lead_no=1 AND sequence_id=?", (sid,)
    ).fetchone()
    assert tuple(enrollment) == ("active", "2026-08-26")
    assert conn.execute("SELECT stage FROM leads WHERE no=1").fetchone()[0] == "replied"
    assert "历史自动回复" in conn.execute(
        "SELECT text FROM notes WHERE lead_no=1 ORDER BY id DESC LIMIT 1"
    ).fetchone()[0]


def test_other_human_reply_prevents_outreach_and_sequence_rollback(tmp_path):
    conn = _conn(tmp_path)
    reply_id, sid = _eidim_shape(conn)
    conn.execute(
        "INSERT INTO inbox_messages(lead_no,channel,kind,from_addr,subject,body,received_at)"
        " VALUES (1,'email','reply','john@eidim.com','Re: LED','Please send pricing','2026-08-25T02:00:00+00:00')")
    conn.commit()
    result = repair.run(conn, apply=True, today=dt.date(2026, 8, 25))
    assert result["applied"] == 1
    assert conn.execute("SELECT kind FROM inbox_messages WHERE id=?", (reply_id,)).fetchone()[0] == "auto"
    assert conn.execute(
        "SELECT status FROM outreach WHERE lead_no=1 AND channel='email'"
    ).fetchone()[0] == "replied"
    assert conn.execute(
        "SELECT status FROM sequence_enrollments WHERE lead_no=1 AND sequence_id=?", (sid,)
    ).fetchone()[0] == "replied"


def test_text_only_autoresponder_is_reported_but_not_auto_applied(tmp_path):
    conn = _conn(tmp_path)
    conn.execute(
        "INSERT INTO leads(no,company_en,country,email,stage) VALUES (1,'Alpha AV','USA','info@alpha.com','replied')")
    conn.execute(
        "INSERT INTO outreach(lead_no,channel,status,touch_count,reply_received)"
        " VALUES (1,'email','replied',1,0)")
    cur = conn.execute(
        "INSERT INTO inbox_messages(lead_no,channel,kind,from_addr,subject,body,received_at)"
        " VALUES (1,'email','reply','info@alpha.com','Re: LED',"
        " 'Thank you for reaching out. We have received your message and will get back shortly.',"
        " '2026-08-25T02:00:00+00:00')")
    conn.commit()
    result = repair.run(conn, apply=True, today=dt.date(2026, 8, 25))
    assert result["candidates"] == 1
    assert result["strong"] == 0
    assert result["manual_review"] == 1
    assert result["applied"] == 0
    assert conn.execute("SELECT kind FROM inbox_messages WHERE id=?", (cur.lastrowid,)).fetchone()[0] == "reply"
    assert conn.execute("SELECT status FROM outreach WHERE lead_no=1 AND channel='email'").fetchone()[0] == "replied"
