import datetime as dt

import pytest

from app.agent import classify, conversation, draft, executors, llm, proposals, run, social


def _reply(conn, lead_no=1, body="Please send price for 200sqm P2.5 indoor.",
           channel="email", intent=None, from_addr="buyer@alpha.com", subject="Re: LED"):
    cur = conn.execute(
        "INSERT INTO inbox_messages(lead_no, channel, kind, from_addr, subject, body,"
        " received_at, intent, mailbox_email)"
        " VALUES (?,?,'reply',?,?,?,?,?,'allen@mc.com')",
        (lead_no, channel, from_addr, subject, body,
         dt.datetime.now(dt.UTC).isoformat(), intent))
    conn.commit()
    return cur.lastrowid


# ---------------------------------------------------------------- autonomy dial

def test_kinds_default_to_propose_so_nothing_acts_on_its_own(conn):
    for kind in proposals.KINDS:
        assert proposals.autonomy(conn, kind) == "propose"


def test_off_produces_no_proposal_at_all(conn):
    proposals.set_autonomy(conn, "create_task", "off")
    assert proposals.create(conn, "create_task", lead_no=1, title="x", payload={}) is None
    assert proposals.list_proposals(conn) == []


def test_auto_executes_immediately_but_still_leaves_a_record(conn):
    proposals.set_autonomy(conn, "create_task", "auto")
    p = proposals.create(conn, "create_task", lead_no=1, title="Call them",
                         payload={"title": "Call them", "due_at": "2026-09-01"})
    assert p["status"] == "executed"
    assert "已建销售任务" in p["execution_result"]
    assert conn.execute("SELECT COUNT(*) c FROM activities").fetchone()["c"] == 1


def test_the_dial_is_per_kind_not_a_master_switch(conn):
    proposals.set_autonomy(conn, "create_task", "auto")
    assert proposals.autonomy(conn, "reply_draft") == "propose"
    assert proposals.autonomy(conn, "mark_do_not_contact") == "propose"


def test_unknown_kind_or_level_is_refused(conn):
    with pytest.raises(proposals.ProposalError):
        proposals.set_autonomy(conn, "take_over_the_world", "auto")
    with pytest.raises(proposals.ProposalError):
        proposals.set_autonomy(conn, "create_task", "yolo")


# ---------------------------------------------------------------- queue hygiene

def test_the_same_proposal_is_not_made_twice(conn):
    mid = _reply(conn)
    first = proposals.create(conn, "reply_draft", lead_no=1, inbox_message_id=mid,
                             title="Reply", payload={"body": "hi"}, dedupe_key="draft")
    second = proposals.create(conn, "reply_draft", lead_no=1, inbox_message_id=mid,
                              title="Reply", payload={"body": "hi again"},
                              dedupe_key="draft")
    assert first is not None and second is None


def test_a_week_old_draft_is_retired_rather_than_left_to_be_approved(conn):
    p = proposals.create(conn, "reply_draft", lead_no=1, title="Old", payload={})
    conn.execute("UPDATE agent_proposals SET created_at=? WHERE id=?",
                 ((dt.datetime.now(dt.UTC) - dt.timedelta(days=9)).isoformat(), p["id"]))
    conn.commit()
    assert proposals.expire_stale(conn) == 1
    assert proposals.get(conn, p["id"])["status"] == "expired"


def test_high_risk_proposals_sort_above_routine_ones(conn):
    proposals.create(conn, "create_task", lead_no=1, title="routine",
                     payload={}, risk="low", dedupe_key="a")
    proposals.create(conn, "mark_do_not_contact", lead_no=2, title="stop",
                     payload={}, risk="high", dedupe_key="b")
    assert [p["risk"] for p in proposals.list_proposals(conn)] == ["high", "low"]


# ---------------------------------------------------------------- deciding

def test_rejecting_requires_a_reason_from_the_fixed_list(conn):
    p = proposals.create(conn, "create_task", lead_no=1, title="x", payload={})
    with pytest.raises(proposals.ProposalError):
        proposals.reject(conn, p["id"], "because")
    done = proposals.reject(conn, p["id"], "wrong_timing", "下个月再说")
    assert done["status"] == "rejected" and done["reject_reason"] == "wrong_timing"


def test_editing_before_approval_is_recorded_as_edited(conn, monkeypatch):
    sent = {}
    monkeypatch.setattr(executors.email_adapter, "send_via",
                        lambda box, to, s, b, a=None: sent.update(to=to, subject=s, body=b))
    conn.execute("INSERT INTO mailboxes(email, smtp_host, port, username, password,"
                 " daily_cap, active) VALUES ('allen@mc.com','smtp.mc.com',465,"
                 "'allen@mc.com','pw',40,1)")
    conn.commit()
    mid = _reply(conn)
    p = proposals.create(conn, "reply_draft", lead_no=1, inbox_message_id=mid,
                         title="Reply", payload={"to": "buyer@alpha.com",
                                                 "subject": "Re: LED", "body": "draft text",
                                                 "mailbox_email": "allen@mc.com"})
    result = proposals.approve(conn, p["id"], {**p["payload"], "body": "Allen's own words"})
    assert result["status"] == "executed"
    assert sent["body"] == "Allen's own words"
    assert proposals.get(conn, p["id"])["payload"]["body"] == "Allen's own words"


def test_an_approved_proposal_cannot_be_approved_again(conn):
    proposals.set_autonomy(conn, "create_task", "propose")
    p = proposals.create(conn, "create_task", lead_no=1, title="x",
                         payload={"title": "x", "due_at": "2026-09-01"})
    proposals.approve(conn, p["id"])
    with pytest.raises(proposals.ProposalError):
        proposals.approve(conn, p["id"])


def test_a_kind_without_an_executor_fails_loudly_instead_of_doing_nothing(conn,
                                                                          monkeypatch):
    monkeypatch.setitem(executors.HANDLERS, "create_task", None)
    monkeypatch.delitem(executors.HANDLERS, "create_task")
    p = proposals.create(conn, "create_task", lead_no=1, title="x", payload={})
    done = proposals.approve(conn, p["id"])
    assert done["status"] == "failed" and "没有执行器" in done["execution_result"]


# ---------------------------------------------------------------- executor guards

def test_a_reply_to_a_do_not_contact_customer_is_refused(conn, monkeypatch):
    monkeypatch.setattr(executors.email_adapter, "send_via",
                        lambda *a, **k: pytest.fail("must not send"))
    conn.execute("UPDATE leads SET do_not_contact=1 WHERE no=1")
    conn.commit()
    p = proposals.create(conn, "reply_draft", lead_no=1, title="Reply",
                         payload={"to": "buyer@alpha.com", "body": "hi"})
    done = proposals.approve(conn, p["id"])
    assert done["status"] == "failed" and "不再联系" in done["execution_result"]


def test_a_sent_reply_marks_the_message_handled_and_leaves_a_note(conn, monkeypatch):
    monkeypatch.setattr(executors.email_adapter, "send_via", lambda *a, **k: None)
    conn.execute("INSERT INTO mailboxes(email, smtp_host, port, username, password,"
                 " daily_cap, active) VALUES ('allen@mc.com','smtp.mc.com',465,"
                 "'allen@mc.com','pw',40,1)")
    conn.commit()
    mid = _reply(conn)
    p = proposals.create(conn, "reply_draft", lead_no=1, inbox_message_id=mid,
                         title="Reply", payload={"to": "buyer@alpha.com", "body": "ok",
                                                 "mailbox_email": "allen@mc.com"})
    proposals.approve(conn, p["id"])
    msg = conn.execute("SELECT handled_at, is_read FROM inbox_messages WHERE id=?",
                       (mid,)).fetchone()
    assert msg["handled_at"] and msg["is_read"] == 1
    assert conn.execute("SELECT COUNT(*) c FROM notes WHERE lead_no=1").fetchone()["c"] == 1


def test_the_reply_goes_out_from_the_address_the_customer_wrote_to(conn, monkeypatch):
    used = {}
    monkeypatch.setattr(executors.email_adapter, "send_via",
                        lambda box, *a, **k: used.update(box))
    conn.executescript(
        "INSERT INTO mailboxes(email, smtp_host, port, username, password, daily_cap, active)"
        " VALUES ('other@mc.com','smtp.mc.com',465,'other@mc.com','pw',40,1),"
        "        ('allen@mc.com','smtp.mc.com',465,'allen@mc.com','pw',40,1);")
    conn.commit()
    p = proposals.create(conn, "reply_draft", lead_no=1, title="Reply",
                         payload={"to": "buyer@alpha.com", "body": "ok",
                                  "mailbox_email": "allen@mc.com"})
    proposals.approve(conn, p["id"])
    assert used["email"] == "allen@mc.com"


# ---------------------------------------------------------------- classification

def test_redaction_strips_what_identifies_the_customer():
    out = classify.redact(
        "Contact me at bob@alphaav.com or +1 (415) 555-0199, see https://alpha.com — Alpha AV",
        "Alpha AV")
    assert "bob@alphaav.com" not in out
    assert "555-0199" not in out
    assert "alpha.com" not in out
    assert "Alpha AV" not in out


def test_short_company_names_are_not_redacted_into_nonsense():
    assert "LED" in classify.redact("we need LED panels", "LED")


def test_classification_stores_intent_and_confidence(conn, monkeypatch):
    mid = _reply(conn)
    monkeypatch.setattr(llm, "complete_json", lambda *a, **k: {
        "results": [{"id": mid, "intent": "quote", "confidence": 88}]})
    result = classify.run(conn)
    assert result["classified"] == 1
    row = conn.execute("SELECT intent, intent_confidence FROM inbox_messages WHERE id=?",
                       (mid,)).fetchone()
    assert row["intent"] == "quote" and row["intent_confidence"] == 88


def test_a_made_up_intent_is_dropped_rather_than_stored(conn, monkeypatch):
    mid = _reply(conn)
    monkeypatch.setattr(llm, "complete_json", lambda *a, **k: {
        "results": [{"id": mid, "intent": "very_interested", "confidence": 99}]})
    assert classify.run(conn)["classified"] == 0
    assert conn.execute("SELECT intent FROM inbox_messages WHERE id=?",
                        (mid,)).fetchone()["intent"] is None


def test_an_unconfigured_backend_is_reported_not_raised(conn, monkeypatch):
    _reply(conn)
    def boom(*a, **k):
        raise llm.LLMUnavailable("缺少 backend/deepseek_key.txt")
    monkeypatch.setattr(llm, "complete_json", boom)
    result = classify.run(conn)
    assert result["unavailable"] and result["classified"] == 0


def test_bounces_and_auto_replies_are_never_sent_for_classification(conn):
    conn.execute("INSERT INTO inbox_messages(lead_no, channel, kind, body, received_at)"
                 " VALUES (1,'email','bounce','undeliverable','2026-08-01')")
    conn.execute("INSERT INTO inbox_messages(lead_no, channel, kind, body, received_at)"
                 " VALUES (1,'email','auto','out of office','2026-08-01')")
    conn.commit()
    assert classify.pending(conn) == []


# ---------------------------------------------------------------- draft guardrails

def test_an_unsourced_price_or_lead_time_is_flagged():
    ctx = {"quotes": [], "opportunities": []}
    warnings = draft.check_claims(
        "We can offer USD 320 per sqm and ship in 15 days.", ctx)
    assert any("价格" in w for w in warnings)
    assert any("交期" in w for w in warnings)


def test_a_number_that_came_from_our_own_quote_is_not_flagged():
    ctx = {"quotes": [{"total": 320, "lead_time": "15 days"}], "opportunities": []}
    assert draft.check_claims("As quoted, USD 320 per sqm, 15 days.", ctx) == []


def test_a_draft_that_promises_nothing_numeric_passes_clean():
    ctx = {"quotes": [], "opportunities": []}
    assert draft.check_claims(
        "I will confirm the price and lead time and come back to you tomorrow.", ctx) == []


# ---------------------------------------------------------------- the pipeline

def test_an_email_asking_for_specs_gets_a_draft(conn, monkeypatch):
    mid = _reply(conn, intent="spec")
    monkeypatch.setattr(draft, "build", lambda c, m: {
        "subject": "Re: LED", "body": "Sending specs today.", "language": "en",
        "evidence": [{"claim": "they asked for 200sqm", "source": "their reply"}],
        "open_questions": "", "warnings": [],
        "context": {"lead": {"no": 1}, "quotes": [], "opportunities": [], "history": [],
                    "message": {}},
    })
    monkeypatch.setattr("app.agent.memory.update", lambda c, ctx: "")
    result = run.act_on_replies(conn)
    assert result["draft"] == 1
    p = proposals.list_proposals(conn)[0]
    assert p["kind"] == "reply_draft" and p["inbox_message_id"] == mid
    assert p["payload"]["to"] == "buyer@alpha.com"
    assert p["payload"]["mailbox_email"] == "allen@mc.com"


def test_a_draft_with_an_unsourced_number_is_raised_to_high_risk(conn, monkeypatch):
    _reply(conn, intent="spec")
    monkeypatch.setattr(draft, "build", lambda c, m: {
        "subject": "Re", "body": "USD 300/sqm, 10 days.", "language": "en",
        "evidence": [], "open_questions": "",
        "warnings": ["价格：草稿里出现「USD 300」，上下文里查不到这个值"],
        "context": {"lead": {"no": 1}, "quotes": [], "opportunities": [], "history": [],
                    "message": {}},
    })
    monkeypatch.setattr("app.agent.memory.update", lambda c, ctx: "")
    run.act_on_replies(conn)
    p = proposals.list_proposals(conn)[0]
    assert p["risk"] == "high" and "⚠" in p["reasoning"]


def test_a_whatsapp_reply_is_drafted_from_the_opened_conversation(conn, monkeypatch):
    conn.execute("UPDATE leads SET phone='+1 415 555 0199' WHERE no=1")
    conn.commit()
    _reply(conn, channel="whatsapp", intent="spec", body="what pitch do you have?")
    monkeypatch.setattr(social, "fetch_thread", lambda c, m, engine=None: [
        {"text": "Hi, saw your message", "outgoing": False},
        {"text": "We build P0.7-P10 panels", "outgoing": True},
        {"text": "how much for 100sqm indoor P2.5?", "outgoing": False},
    ])
    seen = {}
    monkeypatch.setattr(draft, "build", lambda c, m: seen.update(msg=m) or {
        "subject": "", "body": "Indoor P2.5, 100sqm — is it a fixed install?",
        "language": "en", "evidence": [], "open_questions": "", "warnings": [],
        "context": {"lead": {"no": 1}, "quotes": [], "opportunities": [], "history": [],
                    "message": {}},
    })
    monkeypatch.setattr("app.agent.memory.update", lambda c, ctx: "")
    result = run.act_on_replies(conn)
    assert result["draft"] == 1 and result["nudge"] == 0
    p = proposals.list_proposals(conn)[0]
    assert p["kind"] == "reply_draft" and p["payload"]["channel"] == "whatsapp"
    assert p["payload"]["subject"] == ""      # chat messages have no subject line
    # the draft saw the real conversation, not the one-line preview
    assert "100sqm indoor P2.5" in seen["msg"]["thread_json"]


def test_a_dm_falls_back_to_a_nudge_when_the_chat_cannot_be_read(conn, monkeypatch):
    conn.execute("UPDATE leads SET phone='+1 415 555 0199' WHERE no=1")
    conn.commit()
    _reply(conn, channel="whatsapp", intent="spec", body="what pitch?")
    def boom(c, m, engine=None):
        raise RuntimeError("WhatsApp 登录已过期")
    monkeypatch.setattr(social, "fetch_thread", boom)
    monkeypatch.setattr(draft, "build",
                        lambda c, m: pytest.fail("must not draft from a preview"))
    result = run.act_on_replies(conn)
    assert result["nudge"] == 1 and result["draft"] == 0
    p = proposals.list_proposals(conn)[0]
    assert p["kind"] == "create_task" and "登录已过期" in p["reasoning"]


def test_a_dm_with_no_handle_to_write_back_to_becomes_a_nudge(conn, monkeypatch):
    _reply(conn, channel="whatsapp", intent="spec")   # lead 1 has no phone
    monkeypatch.setattr(draft, "build",
                        lambda c, m: pytest.fail("nowhere to send it"))
    assert run.act_on_replies(conn)["nudge"] == 1


def test_the_customers_last_turn_groups_consecutive_messages():
    thread = [
        {"text": "hello", "outgoing": False},
        {"text": "we quoted P4", "outgoing": True},
        {"text": "what about P2.5", "outgoing": False},
        {"text": "for 100sqm", "outgoing": False},
    ]
    assert social.last_inbound(thread) == "what about P2.5\nfor 100sqm"
    assert social.transcript(thread).startswith("THEM: hello\nUS: we quoted P4")


def test_a_thread_ending_with_our_own_message_has_no_inbound_turn():
    assert social.last_inbound([{"text": "any update?", "outgoing": True}]) == ""


def test_the_thread_is_read_once_and_then_reused(conn):
    mid = _reply(conn, channel="whatsapp", intent="spec")
    conn.execute("UPDATE leads SET phone='+14155550199' WHERE no=1")
    conn.commit()
    calls = []

    class Engine:
        def read_thread(self, channel, target, limit):
            calls.append((channel, target))
            return [{"text": "how much?", "outgoing": False}]

    msg = dict(conn.execute("SELECT * FROM inbox_messages WHERE id=?", (mid,)).fetchone())
    assert social.fetch_thread(conn, msg, Engine())[0]["text"] == "how much?"
    stored = dict(conn.execute("SELECT * FROM inbox_messages WHERE id=?", (mid,)).fetchone())
    social.fetch_thread(conn, stored, Engine())
    assert calls == [("whatsapp", "14155550199")]   # second call served from the DB


def test_a_dm_reply_goes_through_the_chat_engine_without_an_image(conn, monkeypatch):
    conn.execute("UPDATE leads SET instagram='visionproav' WHERE no=1")
    conn.commit()
    sent = {}
    from app.api import channels as channels_api
    monkeypatch.setattr(channels_api.ENGINE, "send_message",
                        lambda ch, target, body, image: sent.update(
                            ch=ch, target=target, body=body, image=image))
    mid = _reply(conn, channel="instagram", intent="spec")
    p = proposals.create(conn, "reply_draft", lead_no=1, inbox_message_id=mid,
                         title="Reply", payload={"channel": "instagram",
                                                 "body": "P2.5 indoor, what size?"})
    done = proposals.approve(conn, p["id"])
    assert done["status"] == "executed"
    assert sent == {"ch": "instagram", "target": "visionproav",
                    "body": "P2.5 indoor, what size?", "image": None}
    assert conn.execute("SELECT handled_at FROM inbox_messages WHERE id=?",
                        (mid,)).fetchone()["handled_at"]


def test_a_dm_reply_still_respects_do_not_contact(conn, monkeypatch):
    from app.api import channels as channels_api
    monkeypatch.setattr(channels_api.ENGINE, "send_message",
                        lambda *a, **k: pytest.fail("must not send"))
    conn.execute("UPDATE leads SET do_not_contact=1, instagram='x' WHERE no=1")
    conn.commit()
    p = proposals.create(conn, "reply_draft", lead_no=1, title="Reply",
                         payload={"channel": "instagram", "body": "hi"})
    assert proposals.approve(conn, p["id"])["status"] == "failed"


def test_a_dm_is_written_in_chat_voice_not_email_voice():
    assert draft.system_for("whatsapp") is draft.SYSTEM_DM
    assert draft.system_for("instagram") is draft.SYSTEM_DM
    assert draft.system_for("email") is draft.SYSTEM
    # the refusal to invent numbers survives the change of register
    assert "NEVER state a price" in draft.SYSTEM_DM
    assert "no sign-off" in draft.SYSTEM_DM


def test_a_rejection_proposes_stopping_all_contact(conn):
    _reply(conn, intent="reject", body="Not interested, remove me.")
    assert run.act_on_replies(conn)["reject"] == 1
    p = proposals.list_proposals(conn)[0]
    assert p["kind"] == "mark_do_not_contact" and p["risk"] == "high"
    # still only a proposal — the customer is not silenced until Allen says so
    assert conn.execute("SELECT do_not_contact FROM leads WHERE no=1").fetchone()[0] == 0


def test_an_unclear_reply_produces_nothing_rather_than_a_guess(conn):
    _reply(conn, intent="unclear", body="?")
    assert run.act_on_replies(conn) == {"draft": 0, "nudge": 0, "reject": 0,
                                        "quote": 0, "errors": []}


def test_a_missing_backend_stops_the_batch_instead_of_burning_it(conn, monkeypatch):
    for i in range(3):
        _reply(conn, intent="spec", from_addr=f"b{i}@alpha.com")
    def boom(c, m):
        raise llm.LLMUnavailable("今日 Claude Code 调用已达上限")
    monkeypatch.setattr(draft, "build", boom)
    result = run.act_on_replies(conn)
    assert result["draft"] == 0 and len(result["errors"]) == 1


def test_a_handled_message_is_not_proposed_on_again(conn, monkeypatch):
    mid = _reply(conn, intent="spec")
    conn.execute("UPDATE inbox_messages SET handled_at='2026-08-01' WHERE id=?", (mid,))
    conn.commit()
    monkeypatch.setattr(draft, "build", lambda c, m: pytest.fail("already handled"))
    assert run.act_on_replies(conn)["draft"] == 0


def test_a_stale_reply_becomes_a_human_task_instead_of_an_automatic_reply(conn,
                                                                           monkeypatch):
    mid = _reply(conn, intent="spec", body="Please send the catalogue.")
    stale = (dt.datetime.now(dt.UTC) - dt.timedelta(days=8)).isoformat()
    conn.execute("UPDATE inbox_messages SET received_at=? WHERE id=?", (stale, mid))
    conn.commit()
    monkeypatch.setattr(draft, "build", lambda *a: pytest.fail("stale reply must not draft"))

    result = run.act_on_replies(conn)

    assert result["nudge"] == 1 and result["draft"] == 0
    p = proposals.list_proposals(conn)[0]
    assert p["kind"] == "create_task" and "历史回复" in p["title"]
    assert conversation.get(conn, 1, "email")["owner"] == "allen"


# ---------------------------------------------------------------- model plumbing

def test_json_survives_fences_and_chatter():
    assert llm.extract_json('```json\n{"intent":"quote"}\n```') == {"intent": "quote"}
    assert llm.extract_json('Sure!\n{"intent":"spec"}\nHope that helps') == {"intent": "spec"}
    with pytest.raises(llm.LLMError):
        llm.extract_json("no json at all")


def test_each_task_routes_to_its_own_backend(conn):
    assert llm.backend_for(conn, "classify") == "deepseek"
    assert llm.backend_for(conn, "draft") == "cli"
    llm.set_backend(conn, "classify", "cli")
    assert llm.backend_for(conn, "classify") == "cli"
    assert llm.backend_for(conn, "draft") == "cli"


def test_the_cli_daily_limit_falls_back_without_making_a_cli_call(conn, monkeypatch):
    monkeypatch.setattr(llm, "_call_cli",
                        lambda *a, **k: pytest.fail("limit should have blocked this"))
    monkeypatch.setattr(llm, "available", lambda backend: backend == "deepseek")
    monkeypatch.setattr(llm, "_call_deepseek", lambda *a, **k: '{"ok": true}')
    from app import settings
    settings.set_value(conn, "agent_daily_call_limit", "2")
    settings.set_value(conn, "agent_call_stats",
                       f'{{"date": "{dt.date.today().isoformat()}", "cli": 2}}')
    result = llm.complete_json(conn, "draft", "sys", "user")
    assert result["ok"] is True
    assert result["_llm_backend"] == "deepseek"
    assert result["_llm_fallback_from"] == "cli"


def test_a_cli_session_limit_falls_back_to_the_available_draft_backend(conn, monkeypatch):
    monkeypatch.setattr(llm, "_call_cli",
                        lambda *a, **k: (_ for _ in ()).throw(
                            llm.LLMError("You've hit your session limit")))
    monkeypatch.setattr(llm, "available", lambda backend: backend == "deepseek")
    monkeypatch.setattr(llm, "_call_deepseek", lambda *a, **k: '{"body": "Hello"}')
    result = llm.complete_json(conn, "draft", "sys", "user")
    assert result["body"] == "Hello" and result["_llm_backend"] == "deepseek"


# ---------------------------------------------------------------- pricing is Allen's

def test_a_quote_request_is_reported_and_never_drafted(conn, monkeypatch):
    monkeypatch.setattr(draft, "build",
                        lambda c, m: pytest.fail("报价必须由 Allen 亲自做"))
    mid = _reply(conn, intent="quote",
                 body="Please quote 200sqm outdoor P4 for delivery in Q4.")
    conn.execute("UPDATE inbox_messages SET intent_needs=? WHERE id=?",
                 ("200sqm outdoor P4, Q4 delivery", mid))
    conn.commit()
    result = run.act_on_replies(conn)
    assert result["quote"] == 1 and result["draft"] == 0
    p = proposals.list_proposals(conn)[0]
    assert p["kind"] == "create_task"
    assert "你来定价" in p["title"] and "200sqm outdoor P4" in p["title"]
    assert p["payload"]["type"] == "quote" and p["payload"]["priority"] == "high"
    # the customer's own words travel with it, so Allen prices without re-reading
    assert "200sqm outdoor P4" in p["payload"]["note"]


def test_haggling_over_an_existing_quote_is_also_his(conn, monkeypatch):
    monkeypatch.setattr(draft, "build", lambda c, m: pytest.fail("砍价也是 Allen 的事"))
    _reply(conn, intent="negotiation", body="Can you do better than that price?")
    assert run.act_on_replies(conn)["quote"] == 1
    assert "在谈价格" in proposals.list_proposals(conn)[0]["title"]


def test_a_quote_request_on_whatsapp_is_reported_without_opening_the_chat(conn,
                                                                         monkeypatch):
    monkeypatch.setattr(social, "fetch_thread",
                        lambda c, m, engine=None: pytest.fail("不必为报价去开对话"))
    _reply(conn, channel="whatsapp", intent="quote", body="price for 50sqm?")
    assert run.act_on_replies(conn)["quote"] == 1


def test_the_quote_intents_cannot_be_switched_back_on(conn):
    classify.set_draftable(conn, ["inquiry", "spec", "sample", "quote", "negotiation"])
    allowed = classify.draftable(conn)
    assert "quote" not in allowed and "negotiation" not in allowed
    assert set(allowed) == {"inquiry", "spec", "sample"}


def test_which_simple_replies_get_drafted_is_configurable(conn):
    assert set(classify.draftable(conn)) == {"inquiry", "spec", "sample"}
    classify.set_draftable(conn, ["spec"])
    assert classify.draftable(conn) == ("spec",)


# ------------------------------------------------- one open task per customer

def test_agent_does_not_stack_a_second_task_on_the_same_customer(conn):
    """The plan dedupes within a day, so the same unfinished job came back as a new
    task every morning — 89 open items, the same sentence three times over. An agent
    waking up on its own has nothing new to say until the last thing it asked for is
    done."""
    first = executors.create_task(conn, {
        "id": 11, "lead_no": 1, "title": "跟进 Alpha AV：先找到决策联系人", "payload": {}})
    assert "已建销售任务" in first
    second = executors.create_task(conn, {
        "id": 12, "lead_no": 1, "title": "跟进 Alpha AV：先重新读取官网", "payload": {}})
    assert "已有未完成任务" in second
    open_tasks = conn.execute(
        "SELECT COUNT(*) c FROM activities WHERE lead_no=1 AND status='open'").fetchone()["c"]
    assert open_tasks == 1


def test_a_finished_task_frees_the_customer_for_the_next_one(conn):
    from app import activities

    executors.create_task(conn, {"id": 21, "lead_no": 1, "title": "找决策人", "payload": {}})
    task_id = conn.execute(
        "SELECT id FROM activities WHERE lead_no=1 AND status='open'").fetchone()["id"]
    activities.complete(conn, task_id)
    assert "已建销售任务" in executors.create_task(
        conn, {"id": 22, "lead_no": 1, "title": "下一步：确认尺寸", "payload": {}})


def test_a_task_allen_created_himself_does_not_silence_the_agent(conn):
    """His own task is not the agent's report on this customer, so it must not stand in
    for one — only an open agent task means "you already asked for this"."""
    from app import activities

    activities.create(conn, 1, {"title": "我自己记的：周五打电话"})
    assert "已建销售任务" in executors.create_task(
        conn, {"id": 31, "lead_no": 1, "title": "跟进 Alpha AV：先找到决策联系人", "payload": {}})


# ------------------------------------------- the day's report lives on the screen

def test_the_report_is_not_pushed_unless_it_was_asked_for(conn):
    """Allen reads the day on the dashboard now. A daily WhatsApp to himself was one
    more thing arriving on a phone he is already looking away from."""
    from app.agent import report

    assert report.push_enabled(conn) is False


def test_push_can_still_be_turned_back_on(conn):
    from app.agent import report

    report.set_push(conn, True)
    assert report.push_enabled(conn) is True


def test_the_evening_hook_stays_quiet_while_push_is_off(conn, monkeypatch):
    import datetime as dt

    from app.agent import report, run as agent_run

    monkeypatch.setattr(report, "targets", lambda: ["whatsapp"])
    monkeypatch.setattr(report, "send_daily",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("关掉了还推送")))
    agent_run._maybe_report(conn, dt.datetime(2026, 8, 26, 19, 0))


def test_the_evening_hook_still_pushes_once_turned_on(conn, monkeypatch):
    import datetime as dt

    from app.agent import report, run as agent_run

    report.set_push(conn, True)
    monkeypatch.setattr(report, "targets", lambda: ["whatsapp"])
    pushed = []
    monkeypatch.setattr(report, "send_daily", lambda c, d: pushed.append(d))
    agent_run._maybe_report(conn, dt.datetime(2026, 8, 26, 19, 0))
    assert pushed
