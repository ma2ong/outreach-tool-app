import datetime as dt

from app import recheck


def _fit(conn, no, fit):
    conn.execute("UPDATE leads SET target_fit=? WHERE no=?", (fit, no))
    conn.commit()


def test_interval_follows_the_fit_score_and_backs_off_when_nothing_changes():
    assert recheck.interval_days("租赁公司 (90)") == 30
    assert recheck.interval_days("经销商 (80)") == 90
    assert recheck.interval_days("终端用户 (50)") == 180
    assert recheck.interval_days(None) == 180
    # Two quiet checks in a row push the next one out; never past a year.
    assert recheck.interval_days("租赁公司 (90)", 1) == 60
    assert recheck.interval_days("终端用户 (50)", 3) == 365


def test_schedule_after_send_dates_the_first_reread_and_never_moves_it(conn):
    _fit(conn, 1, "租赁公司 (90)")
    due = recheck.schedule_after_send(conn, 1)
    assert due == (dt.date.today() + dt.timedelta(days=30)).isoformat()
    # A second touch does not make the website any newer.
    assert recheck.schedule_after_send(conn, 1) is None
    assert conn.execute("SELECT recheck_due FROM leads WHERE no=1").fetchone()[0] == due


def test_schedule_after_send_skips_leads_with_no_website(conn):
    conn.execute("UPDATE leads SET website='' WHERE no=2")
    conn.commit()
    assert recheck.schedule_after_send(conn, 2) is None


def test_recheck_fills_empty_fields_and_raises_a_task(conn):
    info = {"email": "ventas@beta.com", "phone": "+5511999999", "email_source": "site.contact-page",
            "brief": 'Beta Screens is an event rental company. It lists P3.9 panels.',
            "hook": "Saw P3.9 panels listed on your site."}
    result = recheck.run(conn, 2, enrich_fn=lambda d: info)

    assert result["changed"] is True
    lead = conn.execute("SELECT * FROM leads WHERE no=2").fetchone()
    assert lead["email"] == "ventas@beta.com"
    assert lead["email_source"] == "site.contact-page"
    assert lead["hook"] == "Saw P3.9 panels listed on your site."
    task = conn.execute(
        "SELECT * FROM activities WHERE source='recheck' AND lead_no=2").fetchone()
    assert task["status"] == "open" and "可以再触达" in task["title"]
    note = conn.execute("SELECT text FROM notes WHERE lead_no=2").fetchone()
    assert "新增邮箱：ventas@beta.com" in note["text"]


def test_a_conflicting_value_is_reported_not_written(conn):
    """Replacing a working address with whatever a redesigned footer says is the one
    outcome worse than not checking, so a disagreement stays a sentence in the note."""
    conn.execute("UPDATE leads SET email='old@beta.com' WHERE no=2")
    conn.commit()
    result = recheck.run(conn, 2, enrich_fn=lambda d: {"email": "new@beta.com"})

    assert conn.execute("SELECT email FROM leads WHERE no=2").fetchone()[0] == "old@beta.com"
    assert any("未自动改" in n for n in result["notes"])


def test_a_check_that_found_nothing_leaves_no_trace(conn):
    from app import activities
    activities.ensure_schema(conn)
    conn.execute("UPDATE leads SET email='a@alpha.com', target_fit='租赁公司 (90)' WHERE no=1")
    conn.commit()
    result = recheck.run(conn, 1, enrich_fn=lambda d: {"email": "a@alpha.com"})

    assert result["changed"] is False
    assert conn.execute("SELECT COUNT(*) FROM notes WHERE lead_no=1").fetchone()[0] == 0
    assert conn.execute(
        "SELECT COUNT(*) FROM activities WHERE lead_no=1").fetchone()[0] == 0
    lead = conn.execute("SELECT recheck_count, recheck_due FROM leads WHERE no=1").fetchone()
    assert lead["recheck_count"] == 1
    assert lead["recheck_due"] == (dt.date.today() + dt.timedelta(days=60)).isoformat()


def test_an_unreachable_site_reschedules_instead_of_retrying_every_sweep(conn):
    def boom(domain):
        raise RuntimeError("timeout")

    result = recheck.run(conn, 1, enrich_fn=boom)
    assert result["ok"] is False
    assert conn.execute("SELECT recheck_due FROM leads WHERE no=1").fetchone()[0] == \
        (dt.date.today() + dt.timedelta(days=180)).isoformat()


def test_sweep_takes_due_leads_only_and_skips_anyone_who_replied(conn):
    today = dt.date.today().isoformat()
    later = (dt.date.today() + dt.timedelta(days=5)).isoformat()
    conn.execute("UPDATE leads SET recheck_due=? WHERE no IN (1, 2)", (today,))
    conn.execute("UPDATE leads SET recheck_due=? WHERE no=3", (later,))
    conn.execute("UPDATE outreach SET status='replied' WHERE lead_no=1 AND channel='email'")
    conn.commit()

    seen = []

    def fake(domain):
        seen.append(domain)
        return {}

    assert recheck.sweep(conn, limit=10, enrich_fn=fake) == \
        {"checked": 1, "changed": 0, "failed": 0}
    assert seen == ["beta.com"]


def test_messaging_a_lead_puts_its_first_reread_on_the_calendar(conn):
    """The trigger is the send itself — a lead we never contacted has nothing to revisit."""
    from app import channel_outreach, outreach

    _fit(conn, 2, "经销商 (80)")
    outreach._mark_messaged(conn, 2, dt.date.today().isoformat())
    assert conn.execute("SELECT recheck_due FROM leads WHERE no=2").fetchone()[0] == \
        (dt.date.today() + dt.timedelta(days=90)).isoformat()

    _fit(conn, 3, "租赁公司 (90)")
    channel_outreach._mark_messaged(conn, 3, "whatsapp", dt.date.today().isoformat())
    assert conn.execute("SELECT recheck_due FROM leads WHERE no=3").fetchone()[0] == \
        (dt.date.today() + dt.timedelta(days=30)).isoformat()


def test_sweep_respects_its_daily_cap(conn):
    conn.execute("UPDATE leads SET recheck_due=date('now')")
    conn.commit()
    assert recheck.sweep(conn, limit=2, enrich_fn=lambda d: {})["checked"] == 2


def test_a_site_that_returned_no_pages_at_all_is_a_failure_not_a_finding(conn):
    """enrich swallows per-page fetch errors so one dead URL cannot lose the others.
    Without this check an unreachable site is written off as "says nothing" and never
    read again."""
    result = recheck.run(conn, 1, enrich_fn=lambda d: {"pages": 0})
    assert result["ok"] is False
    assert conn.execute("SELECT recheck_count FROM leads WHERE no=1").fetchone()[0] == 0


def test_a_site_that_answered_with_nothing_quotable_is_a_real_finding(conn):
    result = recheck.run(conn, 1, enrich_fn=lambda d: {"pages": 3})
    assert result["ok"] is True and result["changed"] is False
    assert conn.execute("SELECT recheck_count FROM leads WHERE no=1").fetchone()[0] == 1


def test_a_hook_is_stored_even_when_the_site_earned_no_brief(conn):
    """The single-keyword case: app.brief gates the two separately because they answer
    to different readers, so storing the hook only alongside a brief threw away every
    Korean site that matched one term."""
    result = recheck.run(conn, 1, enrich_fn=lambda d: {
        "pages": 2, "brief": "", "hook": "Saw the LED signage work on your site."})

    assert result["changed"] is True
    lead = conn.execute("SELECT brief, hook FROM leads WHERE no=1").fetchone()
    assert lead["brief"] is None or lead["brief"] == ""
    assert lead["hook"] == "Saw the LED signage work on your site."


def test_an_unchanged_hook_is_not_rewritten(conn):
    info = {"pages": 2, "hook": "Saw the rental work on your site."}
    recheck.run(conn, 1, enrich_fn=lambda d: info)
    second = recheck.run(conn, 1, enrich_fn=lambda d: info)
    assert second["changed"] is False
