import datetime as dt

import pytest

from app import contacts, sales_intelligence
from app.agent import executors, plan, proposals, world


def _strong(conn, lead_no=2):
    conn.execute(
        "UPDATE leads SET target_fit='AV integrator (90)', email=?, email_status='valid',"
        " brief='Commercial AV integration company',"
        " hook='Saw your commercial AV project work.', recheck_due=? WHERE no=?",
        (f"buyer{lead_no}@example.com",
         (dt.date.today() + dt.timedelta(days=30)).isoformat(), lead_no),
    )
    conn.commit()
    contacts.create(conn, lead_no, {
        "name": "Dana Buyer", "title": "Purchasing Director",
        "email": f"buyer{lead_no}@example.com", "email_status": "valid",
        "role": "decision_maker",
    }, is_primary=True, source="test")
    sales_intelligence.create_signal(conn, lead_no, {
        "signal_type": "project", "headline": "Current AV rollout",
        "evidence": "Source-backed current project activity.",
        "source_url": "https://example.com/project",
        "occurred_at": dt.date.today().isoformat(), "confidence": 80,
    })
    return lead_no


def _template_and_mailbox(conn):
    conn.execute(
        "INSERT INTO templates(id,name,channel,subject,body) VALUES"
        " (90,'Evidence intro','email','Question for {company}',"
        " 'Hi {contact}, {hook} Is LED part of a current project at {company}?')"
    )
    conn.execute(
        "INSERT INTO mailboxes(email,smtp_host,port,username,password,daily_cap,active)"
        " VALUES ('sender@example.com','smtp.example.com',465,'sender@example.com','pw',40,1)"
    )
    conn.commit()


def test_auto_plan_keeps_only_ready_accounts_and_records_why(conn):
    _template_and_mailbox(conn)
    _strong(conn, 2)
    conn.execute("UPDATE leads SET email=NULL WHERE no=3")
    conn.commit()
    proposals.set_autonomy(conn, "send_outreach", "auto")

    clean = plan._validate(conn, {
        "kind": "send_outreach", "title": "发给值得联系的客户",
        "payload": {"template_id": 90, "lead_nos": [2, 3]},
    })
    assert clean["payload"]["lead_nos"] == [2]
    audit = clean["payload"]["autonomous_decision"]
    assert audit["accepted"][0]["lead_no"] == 2
    assert audit["rejected"][0]["lead_no"] == 3
    assert audit["rejected"][0]["blockers"]


def test_auto_plan_rejects_batch_when_nobody_is_worth_sending(conn):
    _template_and_mailbox(conn)
    conn.execute("UPDATE leads SET email=NULL WHERE no=2")
    conn.commit()
    proposals.set_autonomy(conn, "send_outreach", "auto")
    with pytest.raises(plan.Rejected, match="自主发送质量门槛"):
        plan._validate(conn, {
            "kind": "send_outreach", "title": "不要硬发",
            "payload": {"template_id": 90, "lead_nos": [2]},
        })


def test_propose_mode_preserves_human_review_even_for_unready_account(conn):
    _template_and_mailbox(conn)
    conn.execute("UPDATE leads SET email='weak@example.com', email_status=NULL WHERE no=2")
    conn.commit()
    proposals.set_autonomy(conn, "send_outreach", "propose")
    clean = plan._validate(conn, {
        "kind": "send_outreach", "title": "给人工判断",
        "payload": {"template_id": 90, "lead_nos": [2]},
    })
    assert clean["payload"]["lead_nos"] == [2]
    assert "autonomous_decision" not in clean["payload"]


def test_planner_world_exposes_readiness_instead_of_asking_model_to_guess(conn, monkeypatch):
    _strong(conn, 2)
    monkeypatch.setattr("app.channels.email_adapter.get_password", lambda: "pw")
    top = world.build(conn)["untouched"]["top"]
    row = next(r for r in top if r["lead_no"] == 2)
    assert row["autonomous_send"]["ready_for_template_check"] is True
    assert row["autonomous_send"]["positives"]


def test_auto_execution_rechecks_current_state_and_stops_after_new_task(conn, monkeypatch):
    _template_and_mailbox(conn)
    _strong(conn, 2)
    p = proposals.create(
        conn, "send_outreach", title="准备自动首触",
        payload={"template_id": 90, "channel": "email", "lead_nos": [2]},
    )
    from app import activities
    activities.create(conn, 2, {
        "title": "先核实采购负责人", "type": "task",
        "due_at": dt.date.today().isoformat(), "priority": "high",
    })
    sent = []
    monkeypatch.setattr("app.api.send.pick_sender",
                        lambda c: lambda *args: sent.append(args[0]))

    with pytest.raises(executors.ExecutionRefused, match="执行前复检停止发送"):
        executors.send_outreach(conn, {**p, "execution_mode": "auto"})
    assert sent == []
    refreshed = proposals.get(conn, p["id"])
    assert refreshed["payload"]["execution_recheck"]["rejected"][0]["lead_no"] == 2


def test_human_approved_execution_is_not_rescored_for_worth_it(conn, monkeypatch):
    _template_and_mailbox(conn)
    conn.execute("UPDATE leads SET email='manual@example.com', email_status=NULL WHERE no=2")
    conn.commit()
    p = proposals.create(
        conn, "send_outreach", title="人工决定仍要联系",
        payload={"template_id": 90, "channel": "email", "lead_nos": [2]},
    )
    sent = []
    monkeypatch.setattr("app.api.send.pick_sender",
                        lambda c: lambda to, s, b, a: sent.append(to))
    result = executors.send_outreach(conn, {**p, "execution_mode": "approved"})
    assert "已发 1 封" in result
    assert sent == ["manual@example.com"]
