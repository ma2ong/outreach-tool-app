"""The memory grows from what happened, not from one rare moment (docs/87)."""
import json

import pytest

from app import relationship_events
from app.agent import memory, memory_events


def _reply(conn, lead_no=1, intent="quote_request", body="Send me a price for P2.6.",
           at="2026-09-02T10:15:00+00:00", kind="reply"):
    cur = conn.execute(
        "INSERT INTO inbox_messages(lead_no, channel, kind, from_addr, subject, body,"
        " received_at, intent) VALUES (?, 'email', ?, 'a@b.com', 's', ?, ?, ?)",
        (lead_no, kind, body, at, intent))
    conn.commit()
    return cur.lastrowid


def test_a_bank_payment_becomes_something_the_next_letter_knows(conn):
    """22 of these sat in relationship_events while lead_memory held zero rows."""
    relationship_events.record(conn, 1, "fact",
                               summary="银行到账 USD 22,860（2026-08-26）", source="import")
    got = memory.items(conn, 1)
    assert len(got) == 1
    assert "22,860" in got[0]["content"]
    assert got[0]["kind"] == "profile" and got[0]["origin"] == "event"


def test_a_reply_is_remembered_when_it_arrives(conn):
    _reply(conn, body="I already buy from Maxcolor. My guy is Tony.")
    memory_events.remember(conn, 1)
    got = memory.items(conn, 1)
    assert len(got) == 1
    assert "Tony" in got[0]["content"] and got[0]["kind"] == "log"
    assert got[0]["content"].startswith("2026-09-02 回复")


def test_our_own_quoted_signature_is_not_remembered_as_theirs(conn):
    _reply(conn, body="No thanks.\n\n> On Sep 1, allen@maxcolorvisual.com wrote:\n"
                      "> Allen Ma · Shenzhen Maxcolor Visual\n> WhatsApp +86 135-7087-1001")
    memory_events.remember(conn, 1)
    content = memory.items(conn, 1)[0]["content"]
    assert "135-7087-1001" not in content and "Maxcolor Visual" not in content


def test_a_bounce_is_remembered_as_a_durable_fact(conn):
    _reply(conn, kind="bounce", intent=None, body="Undelivered")
    memory_events.remember(conn, 1)
    got = memory.items(conn, 1)
    assert got[0]["kind"] == "profile" and "退过信" in got[0]["content"]


def test_running_twice_writes_nothing_twice(conn):
    relationship_events.record(conn, 1, "fact", summary="银行到账 USD 1,483", source="import")
    _reply(conn)
    assert memory_events.remember(conn, 1) >= 1
    assert memory_events.remember(conn, 1) == 0
    assert len(memory.items(conn, 1)) == 2


def test_every_item_can_name_where_it_came_from(conn):
    """docs/45. An unsourced memory is one nobody can check, and the synthesis prompt
    already refuses to make one."""
    relationship_events.record(conn, 1, "fact", summary="货代代付，真正的买家另有其人",
                               source="import")
    _reply(conn)
    for item in memory.items(conn, 1):
        refs = json.loads(item["evidence"])
        assert refs and all(r.split(":")[0] in ("event", "inbox") for r in refs)


def test_a_send_is_not_a_memory(conn):
    """'We sent letter 2' is already on the outreach row. A memory that repeats the
    activity log is a memory nobody reads."""
    relationship_events.record(conn, 1, "sent", channel="email",
                               summary="发出第 2 封", source="agent")
    assert memory_events.remember(conn, 1) == 0
    assert memory.items(conn, 1) == []


def test_catch_up_covers_the_book_and_is_safe_to_repeat(conn):
    relationship_events.record(conn, 1, "fact", summary="银行到账 USD 900", source="import")
    _reply(conn, lead_no=2)
    first = memory_events.catch_up(conn)
    assert first["written"] >= 1
    assert memory_events.catch_up(conn)["written"] == 0


def test_the_crawler_talking_about_itself_is_not_a_memory(conn):
    """15 of the 22 fact rows read 「社媒动态：活动」 and two 「主页看不了」. That is the
    pipeline describing its own run; nobody carries it into a conversation, and it would
    bury the one that says they paid us."""
    for summary in ("社媒动态：活动", "社媒主页上补到：website",
                    "facebook 主页看不了：页面是空的"):
        relationship_events.record(conn, 1, "fact", summary=summary, source="discovery")
    assert memory_events.remember(conn, 1) == 0
    assert memory.items(conn, 1) == []


def test_the_same_sentence_twice_is_one_memory(conn):
    for _ in range(3):
        relationship_events.record(conn, 1, "fact", summary="客户只买 COB", source="agent")
    memory_events.remember(conn, 1)
    assert len(memory.items(conn, 1)) == 1
