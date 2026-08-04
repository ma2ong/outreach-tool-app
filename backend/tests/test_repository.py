from app import repository as repo


def test_list_leads_all(conn):
    leads = repo.list_leads(conn)
    assert len(leads) == 3


def test_list_leads_filter_country(conn):
    leads = repo.list_leads(conn, country="USA")
    assert {l.no for l in leads} == {1, 2}


def test_list_leads_filter_channel_status(conn):
    leads = repo.list_leads(conn, channel="email", status="messaged")
    assert [l.no for l in leads] == [1]


def test_list_leads_search(conn):
    leads = repo.list_leads(conn, search="gamma")
    assert [l.no for l in leads] == [3]


def test_list_leads_sort_and_paginate(conn):
    # sort by company_en asc: Alpha, Beta, Gamma
    got = repo.list_leads(conn, sort="company_en", order="asc")
    assert [l.company_en for l in got] == ["Alpha AV", "Beta Screens", "Gamma LED"]
    desc = repo.list_leads(conn, sort="company_en", order="desc")
    assert [l.company_en for l in desc] == ["Gamma LED", "Beta Screens", "Alpha AV"]
    page = repo.list_leads(conn, sort="no", limit=1, offset=1)
    assert [l.no for l in page] == [2]


def test_list_leads_sort_by_fit(conn):
    # target_fit stores "label (score)"; "fit" sorts by that score, unscored sinks.
    conn.execute("UPDATE leads SET target_fit = ? WHERE no = 1", ("AV集成商 (85)",))
    conn.execute("UPDATE leads SET target_fit = ? WHERE no = 2", ("租赁公司 (90)",))
    conn.execute("UPDATE leads SET target_fit = ? WHERE no = 3", ("quick-add",))  # no score -> 0
    conn.commit()
    desc = repo.list_leads(conn, sort="fit", order="desc")
    assert [l.no for l in desc] == [2, 1, 3]  # 90, 85, then unscored


def test_list_leads_sort_rejects_bad_column(conn):
    # unknown sort column falls back to 'no' (no SQL injection / error)
    got = repo.list_leads(conn, sort="company_en; DROP TABLE leads")
    assert [l.no for l in got] == [1, 2, 3]


def test_count_leads_matches_filter(conn):
    assert repo.count_leads(conn) == 3
    assert repo.count_leads(conn, country="USA") == 2
    # count ignores pagination
    assert repo.count_leads(conn, country="USA") == len(repo.list_leads(conn, country="USA"))


def test_list_leads_untouched_for_channel(conn):
    # lead2 email row is 'prospect' (never messaged), lead3 has no email row
    assert {l.no for l in repo.list_leads(conn, channel="email", status="untouched")} == {2, 3}
    assert {l.no for l in repo.list_leads(conn, channel="whatsapp", status="untouched")} == {1, 2}


def test_list_leads_untouched_any_channel(conn):
    assert [l.no for l in repo.list_leads(conn, status="untouched")] == [2]


def test_list_leads_untouched_excludes_replied(conn):
    repo.mark_replied(conn, 2, "email")
    assert [l.no for l in repo.list_leads(conn, channel="email", status="untouched")] == [3]


def test_list_leads_follow_up_due(conn):
    # lead1 email messaged 10d ago -> due; lead2 messaged 2d ago -> not due
    conn.execute("UPDATE outreach SET message_sent_date=date('now','-10 days') WHERE lead_no=1 AND channel='email'")
    conn.execute("UPDATE outreach SET message_sent_date=date('now','-10 days') WHERE lead_no=1 AND channel='instagram'")
    conn.execute("UPDATE outreach SET status='messaged', message_sent_date=date('now','-2 days') WHERE lead_no=2 AND channel='email'")
    conn.commit()
    due = {l.no for l in repo.list_leads(conn, follow_up="due")}
    assert 1 in due
    assert 2 not in due


def test_follow_up_due_drops_after_reply(conn):
    conn.execute("UPDATE outreach SET message_sent_date=date('now','-10 days') WHERE lead_no=1")
    conn.commit()
    assert 1 in {l.no for l in repo.list_leads(conn, follow_up="due")}
    repo.mark_replied(conn, 1, "email")
    assert 1 not in {l.no for l in repo.list_leads(conn, follow_up="due")}


def test_follow_up_due_excludes_won_lost(conn):
    conn.execute("UPDATE outreach SET message_sent_date=date('now','-10 days') WHERE lead_no=1 AND channel='email'")
    conn.commit()
    repo.update_lead(conn, 1, {"stage": "won"})
    assert 1 not in {l.no for l in repo.list_leads(conn, follow_up="due")}


def test_follow_up_due_manual_date(conn):
    # lead2 never messaged, but has a manual follow-up date in the past
    repo.update_lead(conn, 2, {"follow_up_date": "2020-01-01"})
    assert 2 in {l.no for l in repo.list_leads(conn, follow_up="due")}


def test_stats_follow_up_due_count(conn):
    conn.execute("UPDATE outreach SET message_sent_date=date('now','-10 days') WHERE lead_no=1 AND channel='email'")
    conn.commit()
    assert repo.stats(conn).funnel["follow_up_due"] >= 1


def test_list_leads_has_contact(conn):
    conn.execute("UPDATE leads SET phone='+123456789', email='a@b.com' WHERE no=1")
    conn.execute("UPDATE leads SET email='' WHERE no=2")
    conn.commit()
    assert [l.no for l in repo.list_leads(conn, has="phone")] == [1]
    assert {l.no for l in repo.list_leads(conn, has="instagram")} == {1, 3}
    assert [l.no for l in repo.list_leads(conn, has="email")] == [1]


def test_get_lead_includes_outreach(conn):
    lead = repo.get_lead(conn, 1)
    assert lead.company_en == "Alpha AV"
    channels = {o.channel for o in lead.outreach}
    assert channels == {"email", "instagram"}


def test_update_lead_edits_fields(conn):
    repo.update_lead(conn, 1, {"phone": "+56 9 111", "stage": "negotiating",
                               "tags": "hot,distributor", "email": "x@y.com"})
    lead = repo.get_lead(conn, 1)
    assert lead.phone == "+56 9 111"
    assert lead.stage == "negotiating"
    assert lead.tags == "hot,distributor"
    assert lead.email == "x@y.com"


def test_update_lead_ignores_unknown_and_protected_fields(conn):
    repo.update_lead(conn, 1, {"no": 999, "bogus": "x", "stage": "won"})
    lead = repo.get_lead(conn, 1)
    assert lead.no == 1  # 'no' not overwritten
    assert lead.stage == "won"


def test_update_lead_missing_returns_false(conn):
    assert repo.update_lead(conn, 999, {"stage": "won"}) is False
    assert repo.update_lead(conn, 1, {"stage": "won"}) is True


def test_delete_lead_takes_its_history_with_it(conn):
    """An orphaned outreach/inbox row would keep a deleted company in the funnel counts
    and in the inbox, which is the whole reason the row was deleted."""
    repo.add_note(conn, 1, "同行，不是客户")
    conn.execute("INSERT INTO inbox_messages(lead_no, channel, kind, body) VALUES (1,'email','reply','hi')")
    conn.commit()
    assert repo.delete_lead(conn, 1) is True
    assert repo.get_lead(conn, 1) is None
    for table in ("outreach", "notes", "inbox_messages"):
        assert conn.execute(f"SELECT COUNT(*) FROM {table} WHERE lead_no=1").fetchone()[0] == 0
    assert {l.no for l in repo.list_leads(conn)} == {2, 3}


def test_delete_lead_missing_returns_false(conn):
    assert repo.delete_lead(conn, 999) is False


def test_notes_add_and_list(conn):
    repo.add_note(conn, 1, "打了电话，要 P2.5 报价")
    repo.add_note(conn, 1, "已发报价单")
    lead = repo.get_lead(conn, 1)
    texts = [n.text for n in lead.notes]
    assert "打了电话，要 P2.5 报价" in texts
    assert "已发报价单" in texts
    assert len(lead.notes) == 2
    # newest first
    assert lead.notes[0].text == "已发报价单"


def test_default_stage_is_new(conn):
    assert repo.get_lead(conn, 2).stage == "new"


def test_find_duplicate_by_website(conn):
    assert repo.find_duplicate(conn, website="alpha.com", instagram=None, company_en="X") == 1
    assert repo.find_duplicate(conn, website="new.com", instagram=None, company_en="New") is None


def test_stats(conn):
    s = repo.stats(conn)
    assert s.total == 3
    assert s.by_country == {"USA": 2, "Brazil": 1}
    assert s.by_channel_status["email"]["messaged"] == 1
    assert s.by_channel_status["email"]["prospect"] == 1
    assert s.by_channel_status["instagram"]["messaged"] == 1


def test_stats_reach_and_funnel(conn):
    # lead1: email+phone+ig(alphaig); lead2: email only; lead3: ig(gammaig) only
    conn.execute("UPDATE leads SET email='a@a.com', phone='+111' WHERE no=1")
    conn.execute("UPDATE leads SET email='b@b.com' WHERE no=2")
    conn.commit()
    s = repo.stats(conn)
    # email: have {1,2}=2, messaged {1}=1 (lead2 is 'prospect'), untouched {2}=1
    assert s.reach["email"] == {"have": 2, "messaged": 1, "replied": 0, "untouched": 1}
    # whatsapp: have {1}=1 (only lead1 has phone), messaged {3}=1 (outreach row), untouched {1}=1
    assert s.reach["whatsapp"] == {"have": 1, "messaged": 1, "replied": 0, "untouched": 1}
    # instagram: have {1,3}=2, messaged {1}=1, untouched {3}=1
    assert s.reach["instagram"] == {"have": 2, "messaged": 1, "replied": 0, "untouched": 1}
    # funnel: total 3, with_contact 3, touched {1,3}=2, replied 0
    assert s.funnel["total"] == 3
    assert s.funnel["with_contact"] == 3
    assert s.funnel["touched"] == 2
    assert s.funnel["replied"] == 0


def test_stats_reach_counts_replied(conn):
    conn.execute("UPDATE leads SET email='a@a.com' WHERE no=1")
    conn.commit()
    repo.mark_replied(conn, 1, "email")
    s = repo.stats(conn)
    assert s.reach["email"]["replied"] == 1
    assert s.reach["email"]["messaged"] == 1  # replied still counts as touched
    assert s.funnel["replied"] == 1


def test_stage_advances_on_reply(conn):
    from app import repository as repo
    repo.mark_replied(conn, 1, "email")
    assert repo.get_lead(conn, 1).stage == "replied"


def test_stage_advances_on_send(conn):
    from app import outreach, repository as repo
    outreach._mark_messaged(conn, 2, "2026-07-14")
    assert repo.get_lead(conn, 2).stage == "contacted"


def test_stage_never_moves_backwards(conn):
    from app import outreach, repository as repo
    repo.mark_replied(conn, 1, "email")
    outreach._mark_messaged(conn, 1, "2026-07-14")  # a follow-up touch after a reply
    assert repo.get_lead(conn, 1).stage == "replied"  # not demoted to contacted


def test_manual_stage_is_not_overruled(conn):
    from app import outreach, repository as repo
    repo.update_lead(conn, 3, {"stage": "negotiating"})
    outreach._mark_messaged(conn, 3, "2026-07-14")
    assert repo.get_lead(conn, 3).stage == "negotiating"
