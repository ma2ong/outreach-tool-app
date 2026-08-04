import pytest

from app import health
from app.db import connect, init_schema


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, website, email, phone, stage) VALUES
            (1, 'Ara System', 'South Korea', 'arasystem.kr', 'i@arasystem.kr', '+827048950794', 'new'),
            (2, 'GLD LED', 'South Korea', 'gldled.com', NULL, '+8613809866355', 'new'),
            (3, 'Alibaba', 'China', 'alibaba.com', NULL, NULL, 'new'),
            (4, 'Ghost Co', 'USA', 'ghost.com', NULL, NULL, 'new'),
            (5, 'Contact', 'USA', 'real.com', 'a@real.com', NULL, 'new'),
            (6, 'Messaged Co', 'USA', 'msg.com', 'b@msg.com', NULL, 'new');
        INSERT INTO outreach(lead_no, channel, status, message_sent_date) VALUES
            (6, 'email', 'messaged', '2026-07-01');
    """)
    c.commit()
    return c


def test_scan_finds_each_issue(conn):
    r = health.scan(conn)
    assert [x["no"] for x in r["peer"]] == [2]
    assert [x["no"] for x in r["directory"]] == [3]
    assert [x["no"] for x in r["no_contact"]] == [4]
    assert [x["no"] for x in r["junk_name"]] == [5]
    assert [x["no"] for x in r["stale_stage"]] == [6]
    # a real buyer shows up in nothing
    assert not any(1 in [x["no"] for x in v] for v in r.values())


def test_fix_suppresses_peers_and_directories(conn):
    done = health.fix(conn, ["peer", "directory"])
    assert done == {"peer": 1, "directory": 1}
    dnc = {r["no"] for r in conn.execute("SELECT no FROM leads WHERE do_not_contact=1")}
    assert dnc == {2, 3}
    # and leaves a trail explaining why
    note = conn.execute("SELECT text FROM notes WHERE lead_no=2").fetchone()
    assert "体检" in note["text"]


def test_suppressed_peer_excluded_from_sending(conn):
    from app import outreach
    conn.execute("UPDATE leads SET email='x@gldled.com' WHERE no=2")
    conn.commit()
    assert [l["no"] for l in outreach.eligible_leads(conn, [1, 2], "email")] == [1, 2]
    health.fix(conn, ["peer"])
    assert [l["no"] for l in outreach.eligible_leads(conn, [1, 2], "email")] == [1]


def test_fix_stale_stage(conn):
    assert health.fix(conn, ["stale_stage"]) == {"stale_stage": 1}
    assert conn.execute("SELECT stage FROM leads WHERE no=6").fetchone()["stage"] == "contacted"


def test_fix_never_deletes(conn):
    health.fix(conn, ["peer", "directory", "no_contact", "junk_name"])
    assert conn.execute("SELECT COUNT(*) c FROM leads").fetchone()["c"] == 6


def test_scan_is_idempotent_after_fix(conn):
    health.fix(conn, ["peer", "directory", "stale_stage"])
    r = health.scan(conn)
    assert "peer" not in r and "directory" not in r and "stale_stage" not in r
    assert "no_contact" in r  # reported only, not auto-fixed


def test_cleanable_is_only_dead_weight(conn):
    """#4 has no contact and no history — safe. #3 (Alibaba) also has no contact, and is
    equally safe by this rule; #5 and #6 have contacts or history and must never be in
    the automatic set."""
    nos = [l["no"] for l in health.cleanable(conn)]
    assert 4 in nos
    assert 5 not in nos and 6 not in nos and 1 not in nos


def test_cleanable_spares_anything_with_history(conn):
    from app import repository
    # strip #4's contacts stay empty but give it a note: someone has looked at it
    repository.add_note(conn, 4, "老板说这家要留着")
    assert 4 not in [l["no"] for l in health.cleanable(conn)]


def test_cleanable_spares_a_lead_already_messaged(conn):
    conn.execute("UPDATE leads SET email=NULL WHERE no=6")
    conn.commit()
    assert 6 not in [l["no"] for l in health.cleanable(conn)]
