import datetime as dt

from app import activities, contacts, sales_documents, sequences
from app.agent import sales_truth
from app.db import connect, init_schema


def _conn(tmp_path):
    conn = connect(str(tmp_path / "truth.db"))
    init_schema(conn)
    contacts.ensure_schema(conn)
    activities.ensure_schema(conn)
    sales_documents.ensure_schema(conn)
    return conn


def _lead(conn, no=1, stage="new"):
    conn.execute(
        "INSERT INTO leads(no,company_en,country,email,stage) VALUES (?,?,?,?,?)",
        (no, f"Lead {no}", "USA", f"hello{no}@example.com", stage),
    )
    conn.commit()


def test_stage_replied_is_not_treated_as_human_reply(tmp_path):
    conn = _conn(tmp_path)
    _lead(conn, stage="replied")
    conn.execute(
        "INSERT INTO outreach(lead_no,channel,status,touch_count,message_sent_date,reply_received)"
        " VALUES (1,'email','messaged',2,'2026-08-20',0)"
    )
    conn.execute(
        "INSERT INTO inbox_messages(lead_no,channel,kind,from_addr,subject,body,received_at)"
        " VALUES (1,'email','auto','hello+noreply@example.com','Auto','received','2026-08-20T00:00:00+00:00')"
    )
    conn.commit()

    truth = sales_truth.assess(conn, 1)
    assert truth["crm_stage"] == "replied"
    assert truth["factual_state"] == "contacted"
    assert truth["verified_human_reply"] is False
    assert {a["code"] for a in truth["anomalies"]} == {"stage_replied_without_human_reply"}


def test_human_reply_beats_early_crm_stage(tmp_path):
    conn = _conn(tmp_path)
    _lead(conn, stage="new")
    conn.execute(
        "INSERT INTO inbox_messages(lead_no,channel,kind,from_addr,subject,body,received_at)"
        " VALUES (1,'email','reply','john@example.com','Re: LED','Please send details','2026-08-20T00:00:00+00:00')"
    )
    conn.commit()

    truth = sales_truth.assess(conn, 1)
    assert truth["factual_state"] == "human_replied"
    assert truth["verified_human_reply"] is True
    assert "human_reply_but_stage_behind" in {a["code"] for a in truth["anomalies"]}


def test_accepted_quote_and_order_are_evidence_backed_states(tmp_path):
    conn = _conn(tmp_path)
    _lead(conn, stage="contacted")
    stamp = "2026-08-20T00:00:00+00:00"
    conn.execute(
        "INSERT INTO quotes(quote_no,lead_no,title,status,currency,subtotal,shipping,discount,total,created_at,updated_at)"
        " VALUES ('Q-1',1,'LED project','accepted','USD',100,0,0,100,?,?)",
        (stamp, stamp),
    )
    conn.commit()
    truth = sales_truth.assess(conn, 1)
    assert truth["factual_state"] == "quote_accepted"
    assert "accepted_quote_without_order" in {a["code"] for a in truth["anomalies"]}

    quote_id = conn.execute("SELECT id FROM quotes WHERE quote_no='Q-1'").fetchone()[0]
    conn.execute(
        "INSERT INTO orders(order_no,quote_id,lead_no,status,currency,total,deposit_amount,paid_amount,balance,created_at,updated_at)"
        " VALUES ('O-1',?,1,'confirmed','USD',100,0,0,100,?,?)",
        (quote_id, stamp, stamp),
    )
    conn.commit()
    truth = sales_truth.assess(conn, 1)
    assert truth["factual_state"] == "ordered"
    codes = {a["code"] for a in truth["anomalies"]}
    assert "accepted_quote_without_order" not in codes
    assert "order_but_stage_behind" in codes


def test_self_heal_only_repairs_machine_owned_state(tmp_path):
    conn = _conn(tmp_path)
    _lead(conn, stage="contacted")
    sid = sequences.create_sequence(conn, "English", "email", [
        {"day_offset": 0, "subject": "Hello", "body": "Hello"},
        {"day_offset": 3, "subject": "Follow up", "body": "Follow up"},
    ])
    conn.execute(
        "INSERT INTO sequence_enrollments(lead_no,sequence_id,current_step,status,enrolled_at,next_due_date)"
        " VALUES (1,?,1,'active','2026-08-18','2026-08-21')",
        (sid,),
    )
    cur = conn.execute(
        "INSERT INTO inbox_messages(lead_no,channel,kind,from_addr,subject,body,received_at)"
        " VALUES (1,'email','reply','john@example.com','Re: LED','Interested','2026-08-20T00:00:00+00:00')"
    )
    real_reply_id = cur.lastrowid
    auto = conn.execute(
        "INSERT INTO inbox_messages(lead_no,channel,kind,from_addr,subject,body,received_at)"
        " VALUES (1,'email','auto','noreply@example.com','Auto','Received','2026-08-20T00:01:00+00:00')"
    )
    auto_id = auto.lastrowid
    stamp = "2026-08-20T00:02:00+00:00"
    conn.execute(
        "INSERT INTO activities(lead_no,type,title,due_at,priority,status,source,source_ref,created_at,updated_at)"
        " VALUES (1,'email','Reply real','2026-08-20','high','open','reply',?,?,?)",
        (f"inbox:{real_reply_id}", stamp, stamp),
    )
    conn.execute(
        "INSERT INTO activities(lead_no,type,title,due_at,priority,status,source,source_ref,created_at,updated_at)"
        " VALUES (1,'email','Reply machine','2026-08-20','high','open','reply',?,?,?)",
        (f"inbox:{auto_id}", stamp, stamp),
    )
    conn.commit()

    result = sales_truth.self_heal(conn)
    assert result["sequences_stopped"] == 1
    assert result["reply_tasks_cancelled"] == 1
    assert conn.execute(
        "SELECT status FROM sequence_enrollments WHERE lead_no=1 AND sequence_id=?", (sid,)
    ).fetchone()[0] == "replied"
    assert conn.execute(
        "SELECT status FROM activities WHERE source_ref=?", (f"inbox:{real_reply_id}",)
    ).fetchone()[0] == "open"
    assert conn.execute(
        "SELECT status FROM activities WHERE source_ref=?", (f"inbox:{auto_id}",)
    ).fetchone()[0] == "cancelled"
    # Human CRM judgement is never silently rewritten by self-healing.
    assert conn.execute("SELECT stage FROM leads WHERE no=1").fetchone()[0] == "contacted"


def test_portfolio_aggregates_anomaly_codes(tmp_path):
    conn = _conn(tmp_path)
    _lead(conn, 1, "replied")
    _lead(conn, 2, "new")
    conn.execute(
        "INSERT INTO inbox_messages(lead_no,channel,kind,from_addr,subject,body,received_at)"
        " VALUES (2,'email','reply','buyer@example.com','Re','Hi','2026-08-20T00:00:00+00:00')"
    )
    conn.commit()
    health = sales_truth.portfolio(conn)
    assert health["anomalous_accounts"] == 2
    assert health["by_code"]["stage_replied_without_human_reply"] == 1
    assert health["by_code"]["human_reply_but_stage_behind"] == 1
