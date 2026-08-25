import datetime as dt

from app import case_library, contacts, sales_intelligence
from app.agent import send_decision


def _ready(conn, lead_no=2):
    tomorrow = (dt.date.today() + dt.timedelta(days=30)).isoformat()
    conn.execute(
        "UPDATE leads SET target_fit='AV integrator (90)', email=?, email_status='valid',"
        " brief='Professional AV integrator serving commercial projects',"
        " hook='Saw your commercial AV integration work.', recheck_due=? WHERE no=?",
        (f"buyer{lead_no}@example.com", tomorrow, lead_no),
    )
    conn.commit()
    contacts.create(conn, lead_no, {
        "name": "Dana Buyer", "title": "Purchasing Director",
        "email": f"buyer{lead_no}@example.com", "email_status": "valid",
        "role": "decision_maker",
    }, is_primary=True, source="test")
    sales_intelligence.create_signal(conn, lead_no, {
        "signal_type": "project",
        "headline": "New commercial AV project activity",
        "evidence": "Company project page shows a current commercial AV rollout.",
        "source_url": "https://example.com/projects",
        "occurred_at": dt.date.today().isoformat(),
        "confidence": 80,
        "suggested_angle": "Ask whether LED is part of the current AV rollout.",
    })
    return lead_no


def test_strong_evidenced_account_is_ready_for_a_factual_template(conn):
    no = _ready(conn)
    d = send_decision.evaluate(
        conn, no,
        subject="Question for {company}",
        body="Hi {contact},\n\n{hook}\nAre LED displays part of any current project at {company}?",
    )
    assert d["ready"] is True
    assert d["score"] >= send_decision.MIN_AUTONOMOUS_SCORE
    assert d["message_guard"]["blocked"] is False
    assert any("采购信号" in x for x in d["positives"])


def test_missing_decision_maker_blocks_autonomous_first_touch(conn):
    no = _ready(conn)
    conn.execute("DELETE FROM contacts WHERE lead_no=?", (no,))
    conn.commit()
    d = send_decision.evaluate_account(conn, no)
    assert d["ready_for_template_check"] is False
    assert any("决策联系人" in x for x in d["blockers"])


def test_unverified_primary_email_blocks_autonomous_first_touch(conn):
    no = _ready(conn)
    conn.execute("UPDATE leads SET email_status=NULL WHERE no=?", (no,))
    conn.commit()
    d = send_decision.evaluate_account(conn, no)
    assert d["ready_for_template_check"] is False
    assert any("尚未验证" in x for x in d["blockers"])


def test_due_internal_task_owns_the_next_action(conn):
    no = _ready(conn)
    from app import activities
    activities.create(conn, no, {
        "title": "先确认采购负责人是否仍在职",
        "type": "task", "due_at": dt.date.today().isoformat(), "priority": "high",
    })
    d = send_decision.evaluate_account(conn, no)
    assert d["ready_for_template_check"] is False
    assert any("销售任务负责" in x for x in d["blockers"])


def test_open_opportunity_blocks_cold_first_touch(conn):
    no = _ready(conn)
    from app import opportunities
    opportunities.create(conn, no, {"title": "Lobby LED", "stage": "qualified"})
    d = send_decision.evaluate_account(conn, no)
    assert any("开放商机" in x for x in d["blockers"])


def test_template_case_and_product_claims_need_explicit_approved_evidence(conn):
    no = _ready(conn)
    subject = "Recent LED projects for {company}"
    body = "Hi {contact}, we delivered P2.5 indoor LED projects recently. {hook}"
    blocked = send_decision.evaluate(conn, no, subject=subject, body=body)
    assert blocked["ready"] is False
    assert any("可公开" in x for x in blocked["blockers"])
    assert any("Agent-approved" in x for x in blocked["blockers"])

    case_library.create(conn, {
        "internal_name": "Approved reference",
        "public_label": "Commercial indoor LED reference",
        "public_summary": "Indoor LED display project completed for a commercial venue.",
        "shareable": True,
    })
    conn.execute(
        "INSERT INTO products(model,pixel_pitch,agent_approved) VALUES ('P2.5 Indoor','P2.5',1)"
    )
    conn.commit()
    ready = send_decision.evaluate(conn, no, subject=subject, body=body)
    assert ready["ready"] is True
    assert ready["template_evidence"]["shareable_case_available"] is True
    assert ready["template_evidence"]["approved_product_available"] is True


def test_rendered_guard_still_has_final_say(conn):
    no = _ready(conn)
    d = send_decision.evaluate(conn, no, subject="LED display", body="Hello, we sell LED displays.")
    assert d["ready"] is False
    assert d["message_guard"]["blocked"] is True
    assert any("最终文本 Guard" in x for x in d["blockers"])


def test_batch_keeps_only_accounts_that_are_worth_sending_now(conn):
    ready = _ready(conn, 2)
    conn.execute(
        "UPDATE leads SET email='weak@example.com', email_status='valid', target_fit='AV (40)'"
        " WHERE no=3"
    )
    conn.commit()
    result = send_decision.evaluate_batch(
        conn, [ready, 3],
        subject="Question for {company}",
        body="Hi {contact}, {hook} Are you working on an LED display project at {company}?",
    )
    assert result["accepted"] == [2]
    assert result["rejected"][0]["lead_no"] == 3
