import datetime as dt

import pytest

from app.agent import executors, llm, plan, proposals, report, run, world


@pytest.fixture
def planned(conn):
    """A world with something worth planning: templates, a sequence, untouched leads."""
    conn.executescript("""
        INSERT INTO templates(id, name, channel, subject, body)
            VALUES (1, 'Cold intro', 'email', 'LED panels', 'Hi {name}');
        INSERT INTO sequences(id, name, channel) VALUES (1, 'Cold 3-touch', 'email');
        INSERT INTO sequence_steps(sequence_id, step_order, day_offset, subject, body)
            VALUES (1, 1, 0, 'Step one', 'Body one');
        INSERT INTO mailboxes(email, smtp_host, port, username, password, daily_cap, active)
            VALUES ('allen@mc.com', 'smtp.mc.com', 465, 'allen@mc.com', 'pw', 40, 1);
        UPDATE leads SET email='a@alpha.com' WHERE no=1;
        UPDATE leads SET email='b@beta.com' WHERE no=2;
    """)
    conn.commit()
    return conn


def _plan(monkeypatch, actions, summary="今天先处理回复"):
    monkeypatch.setattr(llm, "complete_json",
                        lambda *a, **k: {"summary": summary, "plan": actions})


# ---------------------------------------------------------------- world state

def test_the_world_is_small_enough_to_reason_about(planned):
    state = world.build(planned)
    assert state["today"] == dt.date.today().isoformat()
    assert {"pending_replies", "tasks", "stalled_opportunities",
            "untouched", "capacity", "reply_rate",
            "templates", "sequences", "already_pending"} <= set(state)
    assert state["templates"][0]["name"] == "Cold intro"
    assert len(state["pending_replies"]) <= world.MAX_ROWS
    assert len(state["untouched"]["top"]) <= world.MAX_ROWS


def test_the_untouched_pool_is_counted_even_when_none_score_highly(planned):
    """A short shortlist once made the planner announce an empty pool while three
    contactable companies sat just under the score threshold."""
    untouched = world.build(planned)["untouched"]
    assert untouched["top"] == []                 # nothing scores 55+ in this fixture
    assert untouched["emailable_untouched"] == 1  # but lead 2 is contactable


def test_the_planner_is_told_what_is_already_waiting(planned):
    proposals.create(planned, "create_task", lead_no=1, title="已经排过了", payload={})
    assert world.build(planned)["already_pending"][0]["title"] == "已经排过了"


def test_capacity_reflects_what_the_mailboxes_already_sent_today(planned):
    before = world.build(planned)["capacity"]["email_remaining_today"]
    from app import mailboxes
    box = mailboxes.list_mailboxes(planned)[0]
    mailboxes.record_send(planned, box["id"])
    assert world.build(planned)["capacity"]["email_remaining_today"] == before - 1


def test_with_no_mailbox_and_no_fallback_the_planner_knows_it_cannot_send(conn,
                                                                          monkeypatch):
    # the real machine may well have a fallback Gmail password on disk
    monkeypatch.setattr("app.channels.email_adapter.get_password", lambda: "")
    assert world.build(conn)["capacity"]["email_sendable"] is False


def test_the_fallback_gmail_alone_still_counts_as_sendable(conn, monkeypatch):
    monkeypatch.setattr("app.channels.email_adapter.get_password", lambda: "app-pw")
    assert world.build(conn)["capacity"]["email_sendable"] is True


# ---------------------------------------------------------------- validation

def test_a_plan_becomes_proposals_not_actions(planned, monkeypatch):
    _plan(monkeypatch, [{
        "kind": "create_task", "lead_no": 1, "title": "打电话确认采购负责人",
        "why": "该客户 A 级但缺决策人", "risk": "low",
        "payload": {"title": "打电话确认采购负责人", "type": "call",
                    "due_at": dt.date.today().isoformat(), "priority": "high"},
    }])
    result = plan.build_plan(planned)
    assert result["proposed"] == 1 and result["rejected"] == []
    p = proposals.list_proposals(planned)[0]
    assert p["kind"] == "create_task" and p["status"] == "pending"
    # nothing happened to the business yet
    assert planned.execute("SELECT COUNT(*) c FROM activities").fetchone()["c"] == 0


def test_an_unknown_action_kind_is_dropped_with_a_reason(planned, monkeypatch):
    _plan(monkeypatch, [{"kind": "call_the_customer", "lead_no": 1, "title": "x",
                         "payload": {}}])
    result = plan.build_plan(planned)
    assert result["proposed"] == 0
    assert "未知动作类型" in result["rejected"][0]


def test_a_lead_that_does_not_exist_is_dropped(planned, monkeypatch):
    _plan(monkeypatch, [{"kind": "create_task", "lead_no": 9999, "title": "x",
                         "payload": {"title": "x"}}])
    result = plan.build_plan(planned)
    assert result["proposed"] == 0 and "不在库里" in result["rejected"][0]


def test_a_made_up_template_or_sequence_is_dropped(planned, monkeypatch):
    _plan(monkeypatch, [
        {"kind": "send_outreach", "title": "群发", "payload":
            {"template_id": 77, "lead_nos": [1, 2]}},
        {"kind": "enroll_sequence", "title": "入组", "payload":
            {"sequence_id": 88, "lead_nos": [1]}},
    ])
    result = plan.build_plan(planned)
    assert result["proposed"] == 0 and len(result["rejected"]) == 2


def test_a_batch_is_trimmed_to_the_capacity_that_actually_exists(planned, monkeypatch):
    for no in range(10, 60):
        planned.execute("INSERT INTO leads(no, company_en, email) VALUES (?,?,?)",
                        (no, f"Co {no}", f"c{no}@x.com"))
    planned.commit()
    _plan(monkeypatch, [{"kind": "send_outreach", "title": "给 50 家发第一封",
                         "payload": {"template_id": 1,
                                     "lead_nos": list(range(10, 60))}}])
    plan.build_plan(planned)
    payload = proposals.list_proposals(planned)[0]["payload"]
    assert len(payload["lead_nos"]) <= plan.MAX_BATCH_LEADS


def test_a_do_not_contact_lead_never_enters_a_batch(planned, monkeypatch):
    planned.execute("UPDATE leads SET do_not_contact=1 WHERE no=2")
    planned.commit()
    _plan(monkeypatch, [{"kind": "send_outreach", "title": "群发",
                         "payload": {"template_id": 1, "lead_nos": [1, 2]}}])
    plan.build_plan(planned)
    assert proposals.list_proposals(planned)[0]["payload"]["lead_nos"] == [1]


def test_outreach_is_refused_outright_when_the_day_is_spent(planned, monkeypatch):
    monkeypatch.setattr(world, "_channel_capacity", lambda conn: {
        "email_remaining_today": 0, "email_sendable": True,
        "whatsapp_remaining_today": 0, "instagram_remaining_today": 0,
        "max_per_batch": 20})
    _plan(monkeypatch, [{"kind": "send_outreach", "title": "群发",
                         "payload": {"template_id": 1, "lead_nos": [1, 2]}}])
    result = plan.build_plan(planned)
    assert result["proposed"] == 0 and "额度已用完" in result["rejected"][0]


def test_a_nonsense_date_is_rejected_rather_than_stored(planned, monkeypatch):
    _plan(monkeypatch, [{"kind": "create_task", "lead_no": 1, "title": "x",
                         "payload": {"title": "x", "due_at": "next tuesday"}}])
    result = plan.build_plan(planned)
    assert result["proposed"] == 0 and "不是合法日期" in result["rejected"][0]


def test_one_bad_action_does_not_sink_the_whole_plan(planned, monkeypatch):
    _plan(monkeypatch, [
        {"kind": "nonsense", "title": "x", "payload": {}},
        {"kind": "create_task", "lead_no": 1, "title": "好的那条",
         "payload": {"title": "好的那条"}},
    ])
    result = plan.build_plan(planned)
    assert result["proposed"] == 1 and len(result["rejected"]) == 1


def test_the_plan_is_capped_so_a_runaway_model_cannot_flood_the_queue(planned, monkeypatch):
    _plan(monkeypatch, [{"kind": "create_task", "lead_no": 1, "title": f"任务 {i}",
                         "payload": {"title": f"任务 {i}"}} for i in range(40)])
    result = plan.build_plan(planned)
    assert result["considered"] == plan.MAX_ACTIONS
    assert any("计划超长" in r for r in result["rejected"])


# ---------------------------------------------------------------- executing a plan

def test_an_approved_outreach_goes_through_the_normal_send_path(planned, monkeypatch):
    sent = []
    monkeypatch.setattr("app.api.send.pick_sender",
                        lambda conn: lambda to, s, b, a: sent.append(to))
    p = proposals.create(planned, "send_outreach", lead_no=None, title="给两家发第一封",
                         payload={"template_id": 1, "channel": "email",
                                  "lead_nos": [1, 2]})
    done = proposals.approve(planned, p["id"])
    assert done["status"] == "executed"
    # lead 1 was already messaged in the fixture, so only the untouched one goes out
    assert sent == ["b@beta.com"]
    assert "已发 1 封" in done["execution_result"]


def test_an_approved_enrollment_puts_the_leads_in_the_sequence(planned):
    p = proposals.create(planned, "enroll_sequence", title="加入 Cold 3-touch",
                         payload={"sequence_id": 1, "lead_nos": [2]})
    done = proposals.approve(planned, p["id"])
    assert done["status"] == "executed"
    assert planned.execute(
        "SELECT COUNT(*) c FROM sequence_enrollments WHERE status='active'"
    ).fetchone()["c"] == 1


def test_discovery_finds_candidates_but_never_imports_them(planned, monkeypatch):
    before = planned.execute("SELECT COUNT(*) c FROM leads").fetchone()["c"]
    monkeypatch.setattr("app.discovery.run_discovery",
                        lambda conn, q, limit=10: [{"company_en": "New Co"}])
    p = proposals.create(planned, "discover_run", title="找巴西经销商",
                         payload={"queries": ["LED distributor"], "country": "Brazil"})
    done = proposals.approve(planned, p["id"])
    assert done["status"] == "executed" and "不自动入库" in done["execution_result"]
    assert planned.execute("SELECT COUNT(*) c FROM leads").fetchone()["c"] == before


# ---------------------------------------------------------------- scheduling

def test_planning_is_on_by_default_and_can_be_switched_off(conn):
    """A plan only ever produces proposals, so the cost of running it is a queue Allen
    ignores — the cost of not running it is a day nobody planned."""
    morning = dt.datetime(2026, 8, 20, 9, 0)
    assert run.plan_due(conn, morning) is True
    run.set_plan_enabled(conn, False)
    assert run.plan_due(conn, morning) is False
    run.set_plan_enabled(conn, True)
    assert run.plan_due(conn, morning) is True


def test_the_plan_runs_once_in_the_morning_and_not_again(conn, monkeypatch):
    monkeypatch.setattr(llm, "complete_json", lambda *a, **k: {"summary": "s", "plan": []})
    morning = dt.datetime(2026, 8, 20, 9, 0)
    assert run.plan_due(conn, morning)
    run.make_plan(conn, morning)
    assert run.plan_due(conn, dt.datetime(2026, 8, 20, 11, 0)) is False
    assert run.plan_due(conn, dt.datetime(2026, 8, 21, 9, 0)) is True


def test_an_afternoon_wake_up_does_not_plan_a_stale_day(conn):
    assert run.plan_due(conn, dt.datetime(2026, 8, 20, 15, 0)) is False


def test_a_failing_planner_marks_the_day_done_instead_of_retrying_all_morning(conn,
                                                                             monkeypatch):
    def boom(*a, **k):
        raise llm.LLMError("网络不可达")
    monkeypatch.setattr(llm, "complete_json", boom)
    morning = dt.datetime(2026, 8, 20, 9, 0)
    result = run.make_plan(conn, morning)
    assert result["proposed"] == 0 and "网络不可达" in result["error"]
    assert run.plan_due(conn, dt.datetime(2026, 8, 20, 9, 5)) is False
    assert "计划失败" in run.status(conn)["plan"]["last_result"]


# ---------------------------------------------------------------- the daily note

def test_the_report_says_what_happened_and_what_is_waiting(conn):
    proposals.create(conn, "create_task", lead_no=1, title="等你确认的事", payload={})
    text = report.compose(conn)
    assert "客户开发日报" in text and "1 条等你确认" in text


def _no_routes(monkeypatch):
    for fn in ("webhook_url", "wecom_url", "whatsapp_number"):
        monkeypatch.setattr(report, fn, lambda: "")


def test_without_any_route_the_report_still_exists_and_says_how_to_get_it(conn,
                                                                         monkeypatch):
    _no_routes(monkeypatch)
    result = report.send_daily(conn)
    assert result["sent"] is False
    assert "report_whatsapp.txt" in result["reason"] and result["text"]


def test_whatsapp_is_preferred_because_the_session_already_exists(conn, monkeypatch):
    sent = {}
    monkeypatch.setattr(report, "whatsapp_number", lambda: "8613800138000")
    monkeypatch.setattr(report, "webhook_url", lambda: "https://open.feishu.cn/hook/x")
    monkeypatch.setattr(report, "wecom_url", lambda: "")
    monkeypatch.setattr(report, "_post", lambda *a: pytest.fail("WhatsApp 应该先成功"))
    monkeypatch.setattr(report, "_push_whatsapp", lambda text: sent.update(text=text) or "")
    assert report.push("今日日报") == ""
    assert sent["text"] == "今日日报"


def test_a_dead_route_falls_through_to_the_next_one(conn, monkeypatch):
    monkeypatch.setattr(report, "whatsapp_number", lambda: "8613800138000")
    monkeypatch.setattr(report, "webhook_url", lambda: "https://open.feishu.cn/hook/x")
    monkeypatch.setattr(report, "wecom_url", lambda: "")
    monkeypatch.setattr(report, "_push_whatsapp", lambda text: "WhatsApp 登录已过期")
    monkeypatch.setattr(report, "_post", lambda url, payload, name: "")
    assert report.push("今日日报") == ""


def test_when_every_route_fails_the_reasons_are_all_reported(conn, monkeypatch):
    monkeypatch.setattr(report, "whatsapp_number", lambda: "8613800138000")
    monkeypatch.setattr(report, "wecom_url", lambda: "https://qyapi.weixin.qq.com/x")
    monkeypatch.setattr(report, "webhook_url", lambda: "")
    monkeypatch.setattr(report, "_push_whatsapp", lambda text: "登录过期")
    monkeypatch.setattr(report, "_post", lambda url, payload, name: "网络不可达")
    problem = report.push("今日日报")
    assert "WhatsApp" in problem and "企业微信" in problem


def test_a_number_is_read_past_whatever_formatting_allen_pasted(monkeypatch):
    monkeypatch.setattr(report, "_read", lambda name: "+86 138-0013-8000")
    assert report.whatsapp_number() == "8613800138000"


def test_configured_routes_are_listed_for_the_ui(monkeypatch):
    monkeypatch.setattr(report, "whatsapp_number", lambda: "8613800138000")
    monkeypatch.setattr(report, "webhook_url", lambda: "")
    monkeypatch.setattr(report, "wecom_url", lambda: "https://qyapi.weixin.qq.com/x")
    assert report.targets() == ["whatsapp", "wecom"]


def test_the_report_goes_out_once_a_day(conn, monkeypatch):
    monkeypatch.setattr(report, "push", lambda text: "")
    assert report.send_daily(conn)["sent"] is True
    assert report.send_daily(conn) == {"sent": False, "reason": "今天已经发过日报"}


def test_the_evening_report_only_auto_pushes_when_a_webhook_exists(conn, monkeypatch):
    pushed = []
    monkeypatch.setattr(report, "push", lambda text: pushed.append(text) or "")
    monkeypatch.setattr(report, "targets", lambda: [])
    run._maybe_report(conn, dt.datetime(2026, 8, 20, 20, 0))
    assert pushed == []          # no route: the day is not marked reported either
    monkeypatch.setattr(report, "targets", lambda: ["feishu"])
    run._maybe_report(conn, dt.datetime(2026, 8, 20, 20, 0))
    assert len(pushed) == 1


def test_no_report_before_the_day_is_over(conn, monkeypatch):
    pushed = []
    monkeypatch.setattr(report, "push", lambda text: pushed.append(text) or "")
    monkeypatch.setattr(report, "targets", lambda: ["feishu"])
    run._maybe_report(conn, dt.datetime(2026, 8, 20, 14, 0))
    assert pushed == []


def test_the_report_names_who_is_waiting_on_a_price(conn):
    proposals.create(conn, "create_task", lead_no=1,
                     title="Alpha AV 要报价——你来定价（200sqm P4）", payload={})
    assert "1 家在等你报价" in report.compose(conn)


def test_the_planner_is_told_pricing_is_not_its_job():
    assert "You do NOT price anything" in plan.SYSTEM
