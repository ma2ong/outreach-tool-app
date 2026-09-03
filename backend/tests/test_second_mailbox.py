# -*- coding: utf-8 -*-
"""同一家公司的第二个信箱，抄送在同一封信里（docs/95）。"""
from app import contacts, personalize, sequence_send, sequences
from app.channels import email_adapter


def _seq(conn):
    return sequences.create_sequence(conn, "S", "email", [
        {"day_offset": 0, "subject": "Hi", "body": "First to {name}"}])


def _with_second_mailbox(conn):
    conn.execute("UPDATE leads SET email='info@alpha.com', hook='Saw it.' WHERE no=1")
    contacts.ensure_schema(conn)
    conn.execute("INSERT INTO contacts(lead_no, name, email, is_primary, created_at, updated_at)"
                 " VALUES (1,'Michael Wiener','michael@alpha.com',0,'2026-09-03','2026-09-03')")
    conn.commit()


def test_the_second_mailbox_is_copied_on_the_same_letter(conn):
    """一封信、两个信箱、一个额度 —— 不是同一家公司收到两封几乎一样的冷邮件。"""
    _with_second_mailbox(conn)
    sid = _seq(conn)
    sequences.enroll_leads(conn, sid, [1])
    eid = sequences.due_queue(conn)[0]["enrollment_id"]
    seen = []
    def sender(to, subject, body, image, cc=None):
        seen.append({"to": to, "cc": cc})
    sequence_send.send_due(conn, [eid], sender=sender, email_delay=(0, 0))
    assert seen == [{"to": "info@alpha.com", "cc": ["michael@alpha.com"]}]
    # 一次触达 = 一条发信记录，日限额和退信抑制的算法不变
    assert conn.execute("SELECT COUNT(*) FROM send_log WHERE lead_no=1").fetchone()[0] == 1


def test_the_info_address_is_not_replaced(conn):
    """Allen 09-03：不知道哪个信箱后面真的坐着人，原来的地址一个字都不动。"""
    _with_second_mailbox(conn)
    assert contacts.also_reach(conn, 1, "info@alpha.com") == ["michael@alpha.com"]
    assert conn.execute("SELECT email FROM leads WHERE no=1").fetchone()["email"] \
        == "info@alpha.com"


def test_a_lead_with_one_mailbox_still_calls_the_old_four_argument_sender(conn):
    conn.execute("UPDATE leads SET email='info@beta.com', hook='Saw it.' WHERE no=2")
    conn.commit()
    sid = _seq(conn)
    sequences.enroll_leads(conn, sid, [2])
    eid = sequences.due_queue(conn)[0]["enrollment_id"]
    calls = []
    sequence_send.send_due(conn, [eid], sender=lambda *a: calls.append(a), email_delay=(0, 0))
    assert calls and len(calls[0]) == 4


def test_the_envelope_carries_both_addresses(conn):
    msg = email_adapter.build_message("me@x.com", "info@alpha.com", "S", "B", None,
                                      ["michael@alpha.com"])
    assert msg["To"] == "info@alpha.com"
    assert msg["Cc"] == "michael@alpha.com"


# Allen 09-03：「只有当确定对方的名称时才称呼，不确定的情况下情愿不发。」
def test_a_scraped_label_never_becomes_a_greeting(conn):
    for junk in ("Nationwide Delivery", "Outside Sales", "Markdown Content", "The Team"):
        assert not personalize.looks_like_a_person(junk)
        rendered = personalize.render("Hi {contact},", {"no": 1, "contact_name": junk})
        assert junk.split()[0] not in rendered


def test_a_real_name_is_still_used(conn):
    for name in ("Michael Wiener", "TOM WILSON", "Bart McCollum", "윤주영"):
        assert personalize.looks_like_a_person(name)
    assert personalize.render("Hi {contact},", {"no": 1, "contact_name": "Michael Wiener"}) \
        == "Hi Michael,"
