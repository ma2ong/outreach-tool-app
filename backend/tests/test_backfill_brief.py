import io

from app import backfill_brief


def _enrich(domain):
    return {"brief": f"The site mentions \"rental\". ({domain})",
            "hook": "Saw P3.9 panels listed on your site."}


def test_backfill_writes_briefs_and_reports_what_is_left(conn):
    out = io.StringIO()
    summary = backfill_brief.run(conn, limit=2, delay=0, enrich_fn=_enrich, out=out)

    assert summary["checked"] == 2 and summary["written"] == 2
    assert summary["remaining"] == 1  # three leads have websites in the fixture
    assert conn.execute("SELECT hook FROM leads WHERE no=1").fetchone()[0] == \
        "Saw P3.9 panels listed on your site."


def test_backfill_is_resumable_and_never_redoes_a_lead(conn):
    out = io.StringIO()
    backfill_brief.run(conn, limit=2, delay=0, enrich_fn=_enrich, out=out)
    second = backfill_brief.run(conn, limit=10, delay=0, enrich_fn=_enrich, out=out)

    assert second["checked"] == 1 and second["remaining"] == 0
    assert backfill_brief.run(conn, limit=10, delay=0, enrich_fn=_enrich, out=out)["checked"] == 0


def test_a_site_that_yields_nothing_is_not_retried_next_batch(conn):
    """Otherwise every run would spend its whole budget on the same silent sites."""
    out = io.StringIO()
    backfill_brief.run(conn, limit=10, delay=0, enrich_fn=lambda d: {}, out=out)
    assert backfill_brief.run(conn, limit=10, delay=0, enrich_fn=_enrich, out=out)["checked"] == 0


def test_do_not_contact_leads_are_left_out(conn):
    conn.execute("UPDATE leads SET do_not_contact=1 WHERE no=1")
    conn.commit()
    assert [l["no"] for l in backfill_brief.pending(conn, 10)] == [2, 3]


def test_backfill_files_no_tasks(conn):
    """Everything a first read finds is new by definition. Raising "the website changed"
    on all 715 would bury the handful of real ones."""
    from app import activities
    activities.ensure_schema(conn)
    out = io.StringIO()
    backfill_brief.run(conn, limit=10, delay=0, enrich_fn=_enrich, out=out)

    assert conn.execute(
        "SELECT COUNT(*) FROM activities WHERE source='recheck'").fetchone()[0] == 0
    # The findings still land on the lead's own timeline as provenance.
    note = conn.execute("SELECT text FROM notes WHERE lead_no=1").fetchone()[0]
    assert note.startswith("首次读取官网：")


def test_a_later_real_recheck_still_files_a_task(conn):
    from app import activities, recheck
    activities.ensure_schema(conn)
    recheck.run(conn, 1, enrich_fn=_enrich)
    assert conn.execute(
        "SELECT COUNT(*) FROM activities WHERE source='recheck'").fetchone()[0] == 1
