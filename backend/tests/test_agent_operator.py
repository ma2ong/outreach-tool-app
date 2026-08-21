import datetime as dt

from app import sequences
from app.agent import llm, mission, plan, proposals, run, world


def _candidate(domain: str, *, country="USA", fit=85, email=None, hook="Saw your AV work.",
               brief="The site describes AV integration projects.", excluded=False,
               duplicate_of=None):
    return {
        "domain": domain,
        "title": domain.split(".")[0].title(),
        "email": email or f"sales@{domain}",
        "country": country,
        "icp_type": "integrator",
        "fit_score": fit,
        "brief": brief,
        "hook": hook,
        "email_source": "site.contact-page",
        "excluded": excluded,
        "exclude_reason": "同行" if excluded else None,
        "duplicate_of": duplicate_of,
    }


def test_mission_has_safe_sales_defaults_and_normalizes_updates(conn):
    current = mission.get(conn)
    assert current["target_markets"] == ["USA", "South Korea"]
    assert current["daily_qualified_leads"] == 5
    assert current["minimum_fit_score"] == 75
    assert current["auto_enroll"] is True

    changed = mission.set_mission(conn, {
        "target_markets": ["  Brazil ", "", "Brazil", "UK"],
        "daily_qualified_leads": 500,
        "minimum_fit_score": 20,
        "auto_enroll": False,
    })
    assert changed == {
        "target_markets": ["Brazil", "UK"],
        "daily_qualified_leads": 20,
        "minimum_fit_score": 75,
        "auto_enroll": False,
    }


def test_world_state_carries_the_mission_and_today_progress(conn):
    state = world.build(conn)
    assert state["mission"]["minimum_fit_score"] == 75
    assert state["mission_progress"]["qualified_leads_imported_today"] == 0


def test_mission_progress_counts_only_contactable_leads_above_the_quality_bar(conn):
    today = dt.datetime.now(dt.UTC).isoformat()
    conn.executemany(
        "INSERT INTO leads(no,company_en,email,email_status,target_fit,created_at)"
        " VALUES (?,?,?,?,?,?)",
        [
            (20, "Qualified", "q@example.com", "valid", "AV集成商 (85)", today),
            (21, "Low fit", "l@example.com", "valid", "终端用户 (50)", today),
            (22, "Dead email", "d@example.com", "invalid", "租赁公司 (90)", today),
        ],
    )
    conn.commit()
    assert mission.progress(conn)["qualified_leads_imported_today"] == 1


def test_an_empty_model_plan_falls_back_to_the_sales_mission(conn, monkeypatch):
    monkeypatch.setattr(llm, "complete_json",
                        lambda *a, **k: {"summary": "线索池需要补充", "plan": []})
    result = plan.build_plan(conn)
    assert result["proposed"] == 1
    proposal = proposals.list_proposals(conn)[0]
    assert proposal["kind"] == "discover_run"
    assert proposal["payload"]["country"] in mission.get(conn)["target_markets"]
    assert proposal["payload"]["queries"]
    assert "任务书兜底" in proposal["reasoning"]


def test_fallback_stays_quiet_after_the_daily_target_is_met(conn, monkeypatch):
    today = dt.datetime.now(dt.UTC).isoformat()
    for no in range(10, 15):
        conn.execute(
            "INSERT INTO leads(no,company_en,country,email,target_fit,created_at)"
            " VALUES (?,?,?,?,?,?)",
            (no, f"Imported {no}", "USA", f"x{no}@example.com", "AV集成商 (85)", today),
        )
    conn.commit()
    monkeypatch.setattr(llm, "complete_json",
                        lambda *a, **k: {"summary": "今天目标已完成", "plan": []})
    assert plan.build_plan(conn)["proposed"] == 0


def test_autonomous_discovery_imports_only_evidence_backed_contactable_buyers(
        conn, monkeypatch):
    candidates = [
        _candidate("good-av.com", fit=85),
        _candidate("good-sign.com", fit=75),
        _candidate("low-fit.com", fit=50),
        _candidate("no-email.com", email="not-an-email"),
        _candidate("no-proof.com", hook="", brief=""),
        _candidate("wrong-market.com", country="India"),
        _candidate("peer-led.com", excluded=True),
        _candidate("duplicate.com", duplicate_of=1),
    ]
    monkeypatch.setattr("app.discovery.run_discovery",
                        lambda c, q, limit=10, **kwargs: candidates)
    from app import verify
    syntax_only = verify.classify_email
    monkeypatch.setattr(
        verify, "classify_email",
        lambda addr, resolve_domain=None: syntax_only(addr, resolve_domain=lambda _: True))

    def verified(c, lead_nos):
        ph = ",".join("?" * len(lead_nos))
        c.execute(f"UPDATE leads SET email_status='valid' WHERE no IN ({ph})", lead_nos)
        c.commit()
        return {"checked": len(lead_nos), "valid": len(lead_nos)}

    monkeypatch.setattr("app.verify.verify_leads", verified)
    sequences.create_sequence(conn, "Cold English", "email", [
        {"day_offset": 0, "subject": "Hello", "body": "Hello {name}"},
    ])
    proposals.set_autonomy(conn, "discover_run", "auto")
    p = proposals.create(conn, "discover_run", title="自动找客户",
                         payload={"queries": ["AV integrator"], "country": "USA"})

    assert p["status"] == "executed"
    assert "自动导入 2 家" in p["execution_result"]
    assert p["payload"]["auto_import"]["accepted"] == 2
    reasons = {r["domain"]: r["reason"] for r in p["payload"]["auto_import"]["rejected"]}
    assert "ICP" in reasons["low-fit.com"]
    assert "邮箱" in reasons["no-email.com"]
    assert "个性化依据" in reasons["no-proof.com"]
    assert "目标市场" in reasons["wrong-market.com"]
    assert "排除" in reasons["peer-led.com"]
    assert "重复" in reasons["duplicate.com"]
    imported = conn.execute(
        "SELECT no,website,email_status FROM leads WHERE website IN ('good-av.com','good-sign.com')"
        " ORDER BY website").fetchall()
    assert len(imported) == 2 and {r["email_status"] for r in imported} == {"valid"}
    assert conn.execute(
        "SELECT COUNT(*) FROM sequence_enrollments WHERE status='active'"
    ).fetchone()[0] == 2


def test_autonomous_import_uses_korean_sequence_for_korean_leads(conn, monkeypatch):
    english = sequences.create_sequence(conn, "Cold English", "email", [
        {"day_offset": 0, "subject": "Hello", "body": "Hello"},
    ])
    korean = sequences.create_sequence(conn, "Cold Korean", "email", [
        {"day_offset": 0, "subject": "안녕하세요", "body": "안녕하세요"},
    ])
    monkeypatch.setattr("app.discovery.run_discovery", lambda c, q, limit=10, **kwargs: [
        _candidate("seoul-av.kr", country="South Korea", fit=85),
    ])
    from app import verify
    syntax_only = verify.classify_email
    monkeypatch.setattr(
        verify, "classify_email",
        lambda addr, resolve_domain=None: syntax_only(addr, resolve_domain=lambda _: True))
    monkeypatch.setattr("app.verify.verify_leads", lambda c, nos: {"checked": len(nos)})
    proposals.set_autonomy(conn, "discover_run", "auto")
    proposals.create(conn, "discover_run", title="找韩国客户",
                     payload={"queries": ["LED integrator"], "country": "South Korea"})
    enrolled = conn.execute(
        "SELECT sequence_id FROM sequence_enrollments ORDER BY id DESC LIMIT 1").fetchone()
    assert enrolled["sequence_id"] == korean
    assert enrolled["sequence_id"] != english


def test_autonomous_discovery_rejects_a_domain_that_cannot_receive_email_before_import(
        conn, monkeypatch):
    monkeypatch.setattr("app.discovery.run_discovery", lambda c, q, limit=10, **kwargs: [
        _candidate("dead-mail.com", fit=85),
    ])

    def dns_sensitive(addr, resolve_domain=None):
        # A syntax-only caller supplies its own resolver and would incorrectly accept it.
        return ("valid", "ok") if resolve_domain is not None else ("invalid", "no-mx")

    monkeypatch.setattr("app.verify.classify_email", dns_sensitive)
    proposals.set_autonomy(conn, "discover_run", "auto")
    done = proposals.create(conn, "discover_run", title="找客户",
                            payload={"queries": ["AV integrator"], "country": "USA"})
    assert done["payload"]["auto_import"]["imported"] == 0
    assert "邮箱" in done["payload"]["auto_import"]["rejected"][0]["reason"]
    assert conn.execute(
        "SELECT COUNT(*) FROM leads WHERE website='dead-mail.com'").fetchone()[0] == 0


def test_manually_approved_discovery_still_waits_for_human_candidate_review(conn,
                                                                            monkeypatch):
    monkeypatch.setattr("app.discovery.run_discovery",
                        lambda c, q, limit=10, **kwargs: [_candidate("review-me.com")])
    p = proposals.create(conn, "discover_run", title="人工审核搜索",
                         payload={"queries": ["x"], "country": "USA"})
    done = proposals.approve(conn, p["id"])
    assert "展开勾选导入" in done["execution_result"]
    assert conn.execute(
        "SELECT COUNT(*) FROM leads WHERE website='review-me.com'").fetchone()[0] == 0


def test_failed_morning_plan_retries_after_cooldown_but_stops_after_three(conn,
                                                                         monkeypatch):
    mission.set_mission(conn, {"daily_qualified_leads": 0})
    monkeypatch.setattr(llm, "complete_json",
                        lambda *a, **k: (_ for _ in ()).throw(llm.LLMError("暂时不可达")))
    # Today's 9am, not a fixed date: `status()` counts attempts against dt.date.today(),
    # so a hard-coded day made this test pass only on that one day.
    first = dt.datetime.combine(dt.date.today(), dt.time(9, 0))
    assert run.plan_due(conn, first)
    run.make_plan(conn, first)
    assert run.plan_due(conn, first + dt.timedelta(minutes=15)) is False
    assert run.plan_due(conn, first + dt.timedelta(minutes=30)) is True
    run.make_plan(conn, first + dt.timedelta(minutes=30))
    run.make_plan(conn, first + dt.timedelta(minutes=60))
    assert run.plan_due(conn, first + dt.timedelta(minutes=90)) is False
    status = run.status(conn)["plan"]
    assert status["attempts"] == 3 and "计划失败" in status["last_result"]


def test_model_outage_still_runs_the_deterministic_sales_mission(conn, monkeypatch):
    monkeypatch.setattr(llm, "complete_json",
                        lambda *a, **k: (_ for _ in ()).throw(llm.LLMError("暂时不可达")))
    result = run.make_plan(conn, dt.datetime(2026, 8, 20, 9, 0))

    assert result["proposed"] == 1 and result["degraded"] is True
    assert "暂时不可达" in result["error"]
    proposal = proposals.list_proposals(conn)[0]
    assert proposal["kind"] == "discover_run" and "任务书兜底" in proposal["reasoning"]
    assert run.plan_due(conn, dt.datetime(2026, 8, 20, 9, 30)) is False
    assert "降级执行" in run.status(conn)["plan"]["last_result"]
