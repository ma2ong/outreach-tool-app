import datetime as dt

import pytest

from app import contacts, recheck, sales_intelligence


def _signal(confidence=90):
    return {
        "signal_type": "project",
        "headline": "New stadium LED scoreboard project",
        "evidence": "Project page requests a new outdoor LED scoreboard.",
        "source_url": "https://alpha.com/projects/stadium",
        "occurred_at": dt.date.today().isoformat(),
        "confidence": confidence,
        "use_case": "Sports",
        "product_fit": "Outdoor P6/P8 display",
        "suggested_angle": "Ask about scoreboard dimensions, viewing distance and installation date.",
    }


def test_explainable_score_combines_fit_contact_signal_and_reply(conn):
    sales_intelligence.ensure_schema(conn)
    conn.execute(
        "UPDATE leads SET target_fit='租赁公司 (90)', brief='Lists rental LED panels',"
        " email='buyer@alpha.com', email_status='valid', recheck_due=? WHERE no=1",
        ((dt.date.today() + dt.timedelta(days=20)).isoformat(),),
    )
    conn.commit()
    contacts.create(conn, 1, {
        "name": "Ana", "title": "Purchasing Director", "email": "ana@alpha.com",
        "email_status": "valid", "role": "decision_maker",
    }, is_primary=True)
    sales_intelligence.create_signal(conn, 1, _signal())
    conn.execute(
        "UPDATE outreach SET status='replied', reply_received=1 WHERE lead_no=1 AND channel='email'"
    )
    conn.commit()

    score = sales_intelligence.score_lead(conn, 1)

    assert score["score"] >= 80 and score["grade"] == "A"
    assert [c["key"] for c in score["components"]] == [
        "fit", "contact", "intent", "engagement", "freshness"]
    assert sum(c["score"] for c in score["components"]) == score["score"]
    assert "立即处理客户回复" in score["next_action"]
    assert any("采购信号" in reason for reason in score["components"][2]["reasons"])


def test_signal_requires_evidence_and_source_and_is_idempotent(conn):
    with pytest.raises(sales_intelligence.SalesIntelligenceValidation, match="证据不能为空"):
        sales_intelligence.create_signal(conn, 1, _signal() | {"evidence": ""})
    with pytest.raises(sales_intelligence.SalesIntelligenceValidation, match="来源 URL"):
        sales_intelligence.create_signal(conn, 1, _signal() | {"source_url": "alpha.com/project"})

    first = sales_intelligence.create_signal(conn, 1, _signal())
    duplicate = sales_intelligence.create_signal(conn, 1, _signal())
    assert duplicate["id"] == first["id"]
    assert conn.execute("SELECT COUNT(*) FROM buying_signals").fetchone()[0] == 1


def test_signal_actions_are_manual_linked_and_idempotent(conn):
    signal = sales_intelligence.create_signal(conn, 2, _signal(confidence=35))
    assert conn.execute("SELECT COUNT(*) FROM activities WHERE lead_no=2").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM opportunities WHERE lead_no=2").fetchone()[0] == 0

    task = sales_intelligence.create_task_from_signal(conn, signal["id"])
    again = sales_intelligence.create_task_from_signal(conn, signal["id"])
    assert task["id"] == again["id"] and task["source"] == "signal"
    assert signal["source_url"] in task["note"]

    opportunity = sales_intelligence.create_opportunity_from_signal(conn, signal["id"])
    same = sales_intelligence.create_opportunity_from_signal(conn, signal["id"])
    assert same["id"] == opportunity["id"]
    assert opportunity["use_case"] == "Sports"
    stored = sales_intelligence.get_signal(conn, signal["id"])
    assert stored["status"] == "actioned" and stored["opportunity_id"] == opportunity["id"]


def test_recheck_change_creates_source_backed_signal_but_first_read_does_not(conn):
    sales_intelligence.ensure_schema(conn)
    result = recheck.run(conn, 1, enrich_fn=lambda _domain: {
        "pages": 2, "phone": "+1 555 0100", "hook": "Saw your LED rental work."
    })
    assert result["changed"] is True
    signal = conn.execute("SELECT * FROM buying_signals WHERE lead_no=1").fetchone()
    assert signal["signal_type"] == "site_change"
    assert signal["source_url"] == "https://alpha.com"
    assert "+1 555 0100" in signal["evidence"]

    recheck.run(conn, 2, first_read=True, enrich_fn=lambda _domain: {
        "pages": 2, "phone": "+1 555 0101"
    })
    assert conn.execute(
        "SELECT COUNT(*) FROM buying_signals WHERE lead_no=2").fetchone()[0] == 0


def test_bad_company_name_is_penalized_and_unclassified_lead_gets_the_right_action(conn):
    sales_intelligence.ensure_schema(conn)
    conn.execute("UPDATE leads SET company_en='Contact', target_fit='租赁公司 (90)' WHERE no=1")
    conn.execute("UPDATE leads SET target_fit=NULL WHERE no=2")
    conn.commit()

    bad_name = sales_intelligence.score_lead(conn, 1)
    unclassified = sales_intelligence.score_lead(conn, 2)

    assert any("页面标题" in warning for warning in bad_name["warnings"])
    assert "核实正确公司名" in bad_name["next_action"]
    assert bad_name["data_incomplete"] is True
    assert "完成 ICP 分级" in unclassified["next_action"]
    assert unclassified["data_incomplete"] is True


def test_delete_merge_and_health_keep_signal_relations_safe(conn):
    from app import dedupe, health, repository

    signal = sales_intelligence.create_signal(conn, 2, _signal())
    existing = sales_intelligence.create_signal(conn, 1, _signal())
    conn.execute("UPDATE leads SET website='alpha.com', company_en='Alpha AV' WHERE no=2")
    conn.commit()
    dedupe.merge_leads(conn, 1, [2])
    assert sales_intelligence.get_signal(conn, signal["id"]) is None
    assert sales_intelligence.get_signal(conn, existing["id"])["lead_no"] == 1
    assert conn.execute(
        "SELECT COUNT(*) FROM buying_signals WHERE lead_no=1").fetchone()[0] == 1

    signal3 = sales_intelligence.create_signal(conn, 3, _signal() | {
        "source_url": "https://gamma.com/project"})
    conn.execute("UPDATE leads SET email='', phone='', instagram='', facebook='' WHERE no=3")
    conn.commit()
    assert 3 not in [row["no"] for row in health.cleanable(conn)]
    assert repository.delete_lead(conn, 3) is True
    assert sales_intelligence.get_signal(conn, signal3["id"]) is None


def test_portfolio_summary_does_not_issue_one_query_bundle_per_customer(conn):
    conn.executemany(
        "INSERT INTO leads(no,company_en,country,target_fit,email,email_status)"
        " VALUES (?,?,?,?,?,?)",
        [(no, f"Company {no}", "USA", "AV integrator (75)",
          f"buyer{no}@example.com", "valid") for no in range(10, 100)],
    )
    conn.commit()
    statements = []
    conn.set_trace_callback(statements.append)
    summary = sales_intelligence.summary(conn)
    conn.set_trace_callback(None)

    selects = [sql for sql in statements if sql.lstrip().upper().startswith(("SELECT", "WITH"))]
    assert summary["ranked_accounts"] >= 90
    assert len(selects) < 80
