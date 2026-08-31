"""Email send-limit tests use valid personalized copy so they test quotas, not guard holds."""
import pytest

from app import outreach, sequences, sequence_send
from app.db import connect, init_schema


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    rows = ", ".join(f"({i}, 'Co{i}', 'USA', 'c{i}@x.com')" for i in range(1, 61))
    c.executescript(f"INSERT INTO leads(no, company_en, country, email) VALUES {rows};")
    c.commit()
    return c


def _sender(sent):
    return lambda to, subject, body, attachment: sent.append(to)


def test_blast_respects_batch_cap(conn):
    sent = []
    res = outreach.send_campaign(conn, list(range(1, 61)), "{company}", "Hello {company}", None,
                                 sender=_sender(sent), delay_range=(0, 0),
                                 max_send=outreach.remaining_today(conn))
    assert len(sent) == min(outreach.DAILY_CAP, outreach.MAX_BATCH)
    assert res["sent"] == min(outreach.DAILY_CAP, outreach.MAX_BATCH)
    assert res["deferred"] == 60 - min(outreach.DAILY_CAP, outreach.MAX_BATCH)


def test_daily_cap_across_runs(conn):
    sent = []
    total = 0
    for _ in range(4):
        res = outreach.send_campaign(conn, list(range(1, 61)), "{company}", "Hello {company}", None,
                                     sender=_sender(sent), delay_range=(0, 0),
                                     max_send=outreach.remaining_today(conn))
        total += res["sent"]
    assert total == outreach.DAILY_CAP
    assert outreach.remaining_today(conn) == 0


def test_remaining_counts_only_today(conn):
    conn.execute("INSERT INTO outreach(lead_no, channel, status, message_sent_date)"
                 " VALUES (1, 'email', 'messaged', '2020-01-01')")
    conn.commit()
    assert outreach.remaining_today(conn) == outreach.DAILY_CAP


def test_mailbox_rotation_raises_the_ceiling(conn):
    conn.execute("INSERT INTO mailboxes(email, smtp_host, port, username, password, daily_cap, active)"
                 " VALUES ('a@x.com','smtp',465,'a','p',50,1), ('b@x.com','smtp',465,'b','p',50,1)")
    conn.commit()
    from app import mailboxes
    assert mailboxes.total_remaining(conn) == 100 > outreach.DAILY_CAP


def test_sequence_send_is_capped_too(conn):
    sid = sequences.create_sequence(conn, "S", "email", [{"day_offset": 0, "body": "hi {name}"}])
    sequences.enroll_leads(conn, sid, list(range(1, 61)))
    due = sequences.due_queue(conn)
    sent = []
    res = sequence_send.send_due(conn, [d["enrollment_id"] for d in due],
                                 sender=_sender(sent), email_delay=(0, 0))
    assert len(sent) == min(outreach.DAILY_CAP, outreach.MAX_BATCH)
    assert res["deferred"] == 60 - min(outreach.DAILY_CAP, outreach.MAX_BATCH)
    still = {d["lead_no"] for d in sequences.due_queue(conn)}
    assert len(still) == 60 - min(outreach.DAILY_CAP, outreach.MAX_BATCH)


def test_sequence_api_send_rotates_mailboxes(tmp_path, monkeypatch):
    import app.api.sequences as seq_api
    from app.api import send as send_api
    from app import jobs

    db = str(tmp_path / "t.db")
    c = connect(db)
    init_schema(c)
    rows = ", ".join(f"({i}, 'Co{i}', 'c{i}@x.com')" for i in range(1, 5))
    c.executescript(
        f"INSERT INTO leads(no, company_en, email) VALUES {rows};"
        "INSERT INTO mailboxes(email, smtp_host, port, username, password, daily_cap, active)"
        " VALUES ('a@x.com','smtp',465,'a','p',5,1), ('b@x.com','smtp',465,'b','p',5,1);")
    sid = sequences.create_sequence(c, "S", "email", [{"day_offset": 0, "body": "hi {name}"}])
    sequences.enroll_leads(c, sid, [1, 2, 3, 4])
    due_ids = [d["enrollment_id"] for d in sequences.due_queue(c)]
    c.close()

    used: list[str] = []
    monkeypatch.setattr("app.channels.email_adapter.send_via",
                        lambda mbx, to, subject, body, attachment: used.append(mbx["email"]))
    monkeypatch.setattr(send_api, "SENDER",
                        lambda *a, **k: pytest.fail("sequence send fell back to the single Gmail"))
    monkeypatch.setattr(seq_api, "DB_PATH", db)
    monkeypatch.setattr(sequence_send, "time", type("T", (), {"sleep": staticmethod(lambda s: None)}))

    job = jobs.create(total=len(due_ids))
    seq_api._run_send(job, due_ids, None)

    assert jobs.get(job)["result"]["sent"] == 4
    assert sorted(used) == ["a@x.com", "a@x.com", "b@x.com", "b@x.com"]
    c = connect(db)
    counts = {r["mailbox_id"]: r["count"] for r in c.execute("SELECT mailbox_id, count FROM mailbox_sends")}
    assert sorted(counts.values()) == [2, 2]
