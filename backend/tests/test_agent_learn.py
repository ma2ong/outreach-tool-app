import datetime as dt

from app.agent import draft, learn, llm, proposals


def _draft_proposal(conn, body="agent version", lead_no=1):
    return proposals.create(conn, "reply_draft", lead_no=lead_no, title="Reply",
                            payload={"channel": "email", "to": "b@x.com",
                                     "subject": "Re: LED", "body": body},
                            dedupe_key=f"d{body}")


def _approve_edited(conn, monkeypatch, p, new_body):
    monkeypatch.setattr("app.agent.executors.email_adapter.send_via", lambda *a, **k: None)
    conn.execute("INSERT OR IGNORE INTO mailboxes(email, smtp_host, port, username,"
                 " password, daily_cap, active) VALUES ('a@mc.com','s',465,'u','p',40,1)")
    conn.commit()
    return proposals.approve(conn, p["id"], {**p["payload"], "body": new_body})


# ---------------------------------------------------------------- the signal survives

def test_allens_edit_keeps_the_agents_original_version(conn, monkeypatch):
    p = _draft_proposal(conn, "We are pleased to inform you of our premier offering.")
    _approve_edited(conn, monkeypatch, p, "Sending specs today. What size?")
    stored = proposals.get(conn, p["id"])
    assert stored["status"] == "executed"
    assert stored["payload"]["body"] == "Sending specs today. What size?"
    assert stored["original_payload"]["body"].startswith("We are pleased")


def test_approving_unchanged_records_no_edit(conn, monkeypatch):
    monkeypatch.setattr("app.agent.executors.email_adapter.send_via", lambda *a, **k: None)
    conn.execute("INSERT INTO mailboxes(email, smtp_host, port, username, password,"
                 " daily_cap, active) VALUES ('a@mc.com','s',465,'u','p',40,1)")
    conn.commit()
    p = _draft_proposal(conn, "good enough")
    proposals.approve(conn, p["id"])
    assert proposals.get(conn, p["id"])["original_payload"] is None
    assert learn.edited_drafts(conn) == []


def test_an_edited_pair_is_readable_as_before_and_after(conn, monkeypatch):
    p = _draft_proposal(conn, "机器写的")
    _approve_edited(conn, monkeypatch, p, "Allen 改的")
    pair = learn.edited_drafts(conn)[0]
    assert pair["agent"] == "机器写的" and pair["allen"] == "Allen 改的"
    assert pair["company"] == "Alpha AV"


# ---------------------------------------------------------------- applied only when real

def test_guidance_stays_silent_until_there_are_enough_examples(conn, monkeypatch):
    for i in range(learn.MIN_EXAMPLES - 1):
        p = _draft_proposal(conn, f"agent {i}")
        _approve_edited(conn, monkeypatch, p, f"allen {i}")
    assert learn.draft_guidance(conn) == ""
    assert learn.summary(conn)["guidance_active"] is False
    assert learn.summary(conn)["examples_needed"] == 1


def test_guidance_turns_on_once_the_sample_is_big_enough(conn, monkeypatch):
    for i in range(learn.MIN_EXAMPLES):
        p = _draft_proposal(conn, f"agent {i}")
        _approve_edited(conn, monkeypatch, p, f"allen {i}")
    guidance = learn.draft_guidance(conn)
    assert "HOW ALLEN REWRITES YOUR DRAFTS" in guidance
    assert "agent 0" in guidance and "allen 0" in guidance
    assert learn.summary(conn)["guidance_active"] is True


def test_the_drafting_prompt_carries_the_guidance_once_active(conn, monkeypatch):
    for i in range(learn.MIN_EXAMPLES):
        p = _draft_proposal(conn, f"agent {i}")
        _approve_edited(conn, monkeypatch, p, f"allen {i}")
    seen = {}
    monkeypatch.setattr(llm, "complete_json",
                        lambda c, task, system, user, **k: seen.update(system=system) or {
                            "subject": "s", "body": "b", "language": "en",
                            "evidence": [], "open_questions": ""})
    conn.execute("INSERT INTO inbox_messages(lead_no, channel, kind, body, received_at)"
                 " VALUES (1,'email','reply','hi','2026-08-19')")
    conn.commit()
    msg = dict(conn.execute("SELECT * FROM inbox_messages ORDER BY id DESC LIMIT 1").fetchone())
    draft.build(conn, msg)
    assert "HOW ALLEN REWRITES YOUR DRAFTS" in seen["system"]
    assert "NEVER state a price" in seen["system"]   # the rules survive the addition


# ---------------------------------------------------------------- rejections and accuracy

def test_rejection_reasons_are_counted_by_kind(conn):
    for i in range(3):
        p = proposals.create(conn, "create_task", lead_no=1, title=f"t{i}",
                             payload={}, dedupe_key=f"t{i}")
        proposals.reject(conn, p["id"], "wrong_timing")
    p = proposals.create(conn, "create_task", lead_no=2, title="x", payload={})
    proposals.reject(conn, p["id"], "not_worth_it")
    rows = learn.rejections(conn)
    assert rows[0] == {"kind": "create_task", "reason": "wrong_timing",
                       "label": "时机不对", "count": 3}


def test_accuracy_reports_how_often_a_proposal_survives(conn, monkeypatch):
    p = _draft_proposal(conn, "kept")
    _approve_edited(conn, monkeypatch, p, "changed")
    rejected = proposals.create(conn, "create_task", lead_no=1, title="no", payload={})
    proposals.reject(conn, rejected["id"], "not_worth_it")
    acc = learn.accuracy(conn)
    assert acc["executed"] == 1 and acc["rejected"] == 1
    assert acc["accept_rate_pct"] == 50.0
    assert acc["edited"] == 1 and acc["edit_rate_pct"] == 100.0


# ---------------------------------------------------------------- what stopped working

def test_a_campaign_needs_volume_before_it_can_be_called_dead(conn):
    for i in range(5):
        conn.execute("INSERT INTO send_log(lead_no, channel, campaign, sent_at)"
                     " VALUES (1,'email','tiny test',date('now'))")
    conn.commit()
    assert learn.weak_campaigns(conn) == []


def test_a_campaign_with_volume_and_no_replies_is_reported(conn):
    for no in range(100, 100 + learn.MIN_CAMPAIGN_SENDS + 2):
        conn.execute("INSERT INTO leads(no, company_en) VALUES (?,?)", (no, f"Co {no}"))
        conn.execute("INSERT INTO send_log(lead_no, channel, campaign, sent_at)"
                     " VALUES (?,'email','跑不动的话术',date('now'))", (no,))
    conn.commit()
    weak = learn.weak_campaigns(conn)
    assert weak[0]["campaign"] == "跑不动的话术" and weak[0]["replied"] == 0
    assert weak[0]["leads"] >= learn.MIN_CAMPAIGN_SENDS


def test_a_campaign_that_got_a_reply_is_not_called_dead(conn):
    for no in range(200, 200 + learn.MIN_CAMPAIGN_SENDS + 2):
        conn.execute("INSERT INTO leads(no, company_en) VALUES (?,?)", (no, f"Co {no}"))
        conn.execute("INSERT INTO send_log(lead_no, channel, campaign, sent_at)"
                     " VALUES (?,'email','有效话术',date('now'))", (no,))
    conn.execute("INSERT INTO outreach(lead_no, channel, status) VALUES (200,'email','replied')")
    conn.commit()
    assert [w["campaign"] for w in learn.weak_campaigns(conn)] == []


def test_the_planner_is_shown_what_stopped_working(conn):
    from app.agent import world
    for no in range(300, 300 + learn.MIN_CAMPAIGN_SENDS + 2):
        conn.execute("INSERT INTO leads(no, company_en) VALUES (?,?)", (no, f"Co {no}"))
        conn.execute("INSERT INTO send_log(lead_no, channel, campaign, sent_at)"
                     " VALUES (?,'email','跑不动的话术',date('now'))", (no,))
    conn.commit()
    assert world.build(conn)["weak_campaigns"][0]["campaign"] == "跑不动的话术"


def test_an_empty_history_teaches_nothing_without_crashing(conn):
    s = learn.summary(conn)
    assert s["guidance_active"] is False
    assert s["accuracy"]["decided"] == 0 and s["accuracy"]["accept_rate_pct"] == 0.0
    assert s["rejections"] == [] and s["weak_campaigns"] == []
    assert s["examples_needed"] == learn.MIN_EXAMPLES
