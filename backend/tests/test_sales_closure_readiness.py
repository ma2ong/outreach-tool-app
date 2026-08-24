import datetime as dt

from fastapi.testclient import TestClient

import app.main as main
from app import activities, opportunities, sales_documents
from app.agent import opportunity_coach, proposals, quote_readiness, solution_engineer, task_reconciler
from app.db import connect, init_schema


def _product(conn, *, pitch="P2.5", cabinet_w=500, cabinet_h=500,
             px_w=200, px_h=200, max_power=200, avg_power=80):
    cur = conn.execute(
        "INSERT INTO products(model,pixel_pitch,brightness,use_case,indoor_outdoor,"
        " refresh_rate_hz,maintenance_access,cabinet_size,agent_approved,"
        " cabinet_width_mm,cabinet_height_mm,cabinet_resolution_w,cabinet_resolution_h,"
        " module_width_mm,module_height_mm,max_power_w_cabinet,avg_power_w_cabinet)"
        " VALUES (?,?,?,?,?,?,?,?,1,?,?,?,?,?,?,?,?)",
        ("P2.5 engineering", pitch, "800-1000 nits", "Fixed Installation", "Indoor",
         3840, "front", "500x500mm", cabinet_w, cabinet_h, px_w, px_h,
         250, 250, max_power, avg_power),
    )
    conn.commit()
    return cur.lastrowid


def _opportunity(conn, **overrides):
    data = {
        "title": "Lobby display",
        "stage": "requirements",
        "use_case": "Fixed Installation",
        "indoor_outdoor": "Indoor",
        "width_m": 3.1,
        "height_m": 2.1,
        "quantity": 2,
        "pixel_pitch": "P2.5",
        "brightness_nits": 800,
        "refresh_rate_hz": 3840,
        "maintenance_access": "front",
        "input_voltage_v": 220,
        "controller_capacity_px": 2_300_000,
        "controller_output_ports": 10,
        "max_pixels_per_port": 650_000,
        "spare_pct": 3,
        "next_action": "Confirm configuration",
        "next_action_date": "2026-08-28",
    }
    data.update(overrides)
    return opportunities.create(conn, 1, data)


def test_inconsistent_effective_pitch_blocks_solution(conn):
    pid = _product(conn, pitch="P2.5", px_w=250, px_h=250)  # 500 / 250 = P2.0
    opp = _opportunity(conn)

    result = solution_engineer.advise(conn, opp, product_id=pid)

    assert result["ready"] is False
    assert result["status"] == "invalid_product_engineering_facts"
    assert result["engineering_integrity"]["valid"] is False
    assert any("P2.000" in error and "P2.5" in error for error in result["engineering_errors"])
    assert "selected_layout" not in result


def test_average_power_above_maximum_blocks_solution(conn):
    pid = _product(conn, max_power=180, avg_power=220)
    opp = _opportunity(conn)

    result = solution_engineer.advise(conn, opp, product_id=pid)

    assert result["ready"] is False
    assert any("平均功耗" in error and "最大功耗" in error for error in result["engineering_errors"])


def test_quote_readiness_prepares_technical_line_but_never_price(conn):
    pid = _product(conn)
    opp = _opportunity(conn)

    packet = quote_readiness.assess(conn, opp, product_id=pid)

    assert packet["technical_ready"] is True
    assert packet["ready_for_human_pricing"] is True
    starter = packet["quote_starter"]
    assert starter["model"] == "P2.5 engineering"
    assert starter["width_m"] == 3.0
    assert starter["height_m"] == 2.0
    assert starter["total_cabinets"] == 48
    assert starter["screen_width_px"] == 1200
    assert starter["screen_height_px"] == 800
    assert starter["unit_price"] is None
    assert all(item["owner"] == "human" for item in packet["human_decisions"])
    assert not any(key in starter for key in ("total", "discount", "payment_terms", "lead_time", "warranty"))


def test_quote_readiness_reports_existing_sent_quote_without_recommending_duplicate(conn):
    pid = _product(conn)
    opp = _opportunity(conn)
    sales_documents.ensure_schema(conn)
    now = dt.datetime.now(dt.UTC).isoformat()
    conn.execute(
        "INSERT INTO quotes(quote_no,lead_no,opportunity_id,title,status,currency,subtotal,shipping,discount,total,created_at,updated_at,sent_at)"
        " VALUES ('MCV-TEST-0001',1,?,'Lobby quote','sent','USD',1000,0,0,1000,?,?,?)",
        (opp["id"], now, now, now),
    )
    conn.commit()

    packet = quote_readiness.assess(conn, opp, product_id=pid)

    assert packet["latest_quote"]["quote_no"] == "MCV-TEST-0001"
    assert packet["latest_quote"]["status"] == "sent"
    assert any("避免重复" in warning for warning in packet["warnings"])
    assert packet["quote_starter"]["unit_price"] is None


def _auto_agent_task(conn, *, completion_rule: dict, opportunity_id=None):
    proposals.set_autonomy(conn, "create_task", "auto")
    p = proposals.create(
        conn, "create_task", lead_no=1, opportunity_id=opportunity_id,
        title="Traceable Agent task",
        payload={
            "title": "Traceable Agent task",
            "type": "task",
            "due_at": dt.date.today().isoformat(),
            "priority": "normal",
            "completion_rule": completion_rule,
        },
        risk="low", dedupe_key=f"test-{dt.datetime.now(dt.UTC).timestamp()}",
    )
    assert p and p["status"] == "executed"
    row = conn.execute(
        "SELECT * FROM activities WHERE source='agent' AND source_ref=?",
        (f"proposal:{p['id']}",),
    ).fetchone()
    assert row is not None
    return dict(row)


def test_agent_icp_task_auto_resolves_when_fact_is_completed(conn):
    conn.execute("UPDATE leads SET target_fit=NULL WHERE no=1")
    conn.commit()
    task = _auto_agent_task(conn, completion_rule={
        "type": "account_brain", "next_action_key": "refresh_icp",
        "baseline_last_touch": "2026-07-01",
    })

    before = task_reconciler.reconcile(conn)
    assert before["resolved"] == 0
    assert activities.get(conn, task["id"])["status"] == "open"

    conn.execute("UPDATE leads SET target_fit='AV Integrator (85)' WHERE no=1")
    conn.commit()
    after = task_reconciler.reconcile(conn)

    assert after["resolved"] == 1
    updated = activities.get(conn, task["id"])
    assert updated["status"] == "done"
    assert "Agent 自动回收" in (updated["note"] or "")


def test_reconciler_never_touches_manual_task(conn):
    manual = activities.create(conn, 1, {
        "title": "先重新读取官网并完成 ICP 分级",
        "type": "task", "due_at": dt.date.today().isoformat(),
    })
    conn.execute("UPDATE leads SET target_fit='AV Integrator (90)' WHERE no=1")
    conn.commit()

    result = task_reconciler.reconcile(conn)

    assert result["checked"] == 0
    assert activities.get(conn, manual["id"])["status"] == "open"


def test_opportunity_agent_task_is_superseded_when_issue_digest_changes(conn):
    _product(conn)
    opp = _opportunity(conn)
    task = _auto_agent_task(conn, opportunity_id=opp["id"], completion_rule={
        "type": "opportunity_coach", "issue_digest": "definitely-old-digest",
    })

    result = task_reconciler.reconcile(conn)

    assert result["superseded"] == 1
    assert activities.get(conn, task["id"])["status"] == "cancelled"


def test_quoted_stage_without_sent_quote_is_not_treated_as_progress(conn):
    _product(conn)
    opp = _opportunity(
        conn, stage="quoted", amount=12000,
        next_action="Follow up quote", next_action_date="2026-08-28",
    )

    coached = opportunity_coach.coach_opportunity(conn, opp, today=dt.date(2026, 8, 24))

    assert coached["quote_evidence"] is None
    assert any("没有已发送报价证据" in risk for risk in coached["risks"])
    assert "阶段标签" in coached["next_best_action"]


def test_quote_readiness_api_returns_safe_packet(tmp_path):
    db = str(tmp_path / "quote-readiness.db")
    conn = connect(db)
    init_schema(conn)
    conn.execute("INSERT INTO leads(no,company_en,country) VALUES (1,'API Buyer','USA')")
    conn.commit()
    pid = _product(conn)
    opp = _opportunity(conn)
    conn.close()

    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    client = TestClient(main.app)
    try:
        r = client.get(f"/api/opportunities/{opp['id']}/quote-readiness?product_id={pid}")
        assert r.status_code == 200
        body = r.json()
        assert body["ready_for_human_pricing"] is True
        assert body["quote_starter"]["unit_price"] is None
        assert body["commercial_authority"] == "human_required"
    finally:
        main.app.dependency_overrides.pop(main.get_conn, None)
