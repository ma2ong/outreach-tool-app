"""docs/114：一个人两个信箱，不是两个人。"""
import pytest

from app import contacts, inbound, replies, sales_documents


def test_extra_email_is_returned_with_the_contact(conn):
    javier = contacts.create(conn, 1, {"name": "Javier Carlos", "email": "javier@alpha.com"})
    contacts.add_channel(conn, javier["id"], "email", "Info@Alpha.com")
    row = contacts.get(conn, javier["id"])
    assert row["email"] == "javier@alpha.com"
    assert [(c["kind"], c["value"]) for c in row["channels"]] == [("email", "info@alpha.com")]
    # 附加地址不是一个人：联系人计数不变。
    assert contacts.stats(conn)["total_contacts"] == 1
    assert len(contacts.list_all(conn, 1)) == 1


def test_extra_email_does_not_touch_the_lead_row(conn):
    javier = contacts.create(conn, 1, {"name": "Javier", "email": "javier@alpha.com"})
    contacts.add_channel(conn, javier["id"], "email", "info@alpha.com")
    assert conn.execute("SELECT email FROM leads WHERE no=1").fetchone()[0] == "javier@alpha.com"


def test_reply_from_the_extra_mailbox_is_attributed_to_the_person(conn):
    javier = contacts.create(conn, 1, {"name": "Javier", "email": "javier@alpha.com"})
    contacts.add_channel(conn, javier["id"], "email", "info@alpha.com")
    result = replies.process_messages(conn, [{
        "from_addr": "info@alpha.com", "subject": "Re: quote",
        "body": "Please resend", "received_at": "2026-09-09T10:00:00",
    }])
    assert result["replies"] == 1
    inbox = conn.execute("SELECT lead_no, contact_id FROM inbox_messages").fetchone()
    assert inbox["lead_no"] == 1 and inbox["contact_id"] == javier["id"]


def test_whatsapp_from_the_extra_number_is_attributed_to_the_person(conn):
    javier = contacts.create(conn, 1, {"name": "Javier", "phone": "+1 623 256 7887"})
    contacts.add_channel(conn, javier["id"], "phone", "+1 623 256 7888")
    result = inbound.process_threads(conn, "whatsapp", [{
        "sender": "+1 623-256-7888", "name": "Javier",
        "preview": "Need a quote", "outgoing": False, "unread": True,
    }])
    assert result["lead_nos"] == [1]
    assert conn.execute("SELECT contact_id FROM inbox_messages").fetchone()[0] == javier["id"]


def test_extra_mailbox_is_still_copied_on_the_letter(conn):
    """docs/95：折叠之前 info@ 在抄送名单里，折叠之后必须还在。"""
    javier = contacts.create(conn, 1, {"name": "Javier", "email": "javier@alpha.com"})
    contacts.add_channel(conn, javier["id"], "email", "info@alpha.com")
    assert contacts.also_reach(conn, 1, "javier@alpha.com") == ["info@alpha.com"]


def test_invalid_extra_mailbox_is_not_copied(conn):
    javier = contacts.create(conn, 1, {"name": "Javier", "email": "javier@alpha.com"})
    channel = contacts.add_channel(conn, javier["id"], "email", "info@alpha.com")
    conn.execute("UPDATE contact_channels SET status='invalid' WHERE id=?", (channel["id"],))
    conn.commit()
    assert contacts.also_reach(conn, 1, "javier@alpha.com") == []


def test_an_address_already_used_in_the_company_is_reported_not_silently_taken(conn):
    javier = contacts.create(conn, 1, {"name": "Javier", "email": "javier@alpha.com"})
    other = contacts.create(conn, 1, {"email": "info@alpha.com"})
    with pytest.raises(contacts.ContactConflict) as exc:
        contacts.add_channel(conn, javier["id"], "email", "info@alpha.com")
    assert exc.value.contact_id == other["id"]
    # 没有确认就什么都不做。
    assert contacts.get(conn, javier["id"])["channels"] == []
    assert contacts.get(conn, other["id"]) is not None


def test_the_same_address_twice_on_one_person_is_refused(conn):
    javier = contacts.create(conn, 1, {"name": "Javier", "email": "javier@alpha.com"})
    contacts.add_channel(conn, javier["id"], "email", "info@alpha.com")
    with pytest.raises(contacts.ContactValidation):
        contacts.add_channel(conn, javier["id"], "email", "INFO@alpha.com")
    with pytest.raises(contacts.ContactValidation):
        contacts.add_channel(conn, javier["id"], "email", "javier@alpha.com")


def test_folding_a_contact_keeps_its_addresses_and_its_history(conn):
    javier = contacts.create(conn, 1, {"name": "Javier Carlos", "email": "javier@alpha.com"})
    info = contacts.create(conn, 1, {
        "email": "info@alpha.com", "phone": "+1 623 256 7899", "title": "Front desk"})
    contacts.add_channel(conn, info["id"], "email", "sales@alpha.com")
    conn.execute(
        "INSERT INTO inbox_messages(lead_no, channel, body, received_at, contact_id)"
        " VALUES (1, 'email', 'hello', '2026-09-01T09:00:00', ?)",
        (info["id"],))
    conn.commit()

    contacts.fold_into(conn, javier["id"], info["id"])

    row = contacts.get(conn, javier["id"])
    assert {(c["kind"], c["value"]) for c in row["channels"]} == {
        ("email", "info@alpha.com"), ("email", "sales@alpha.com"),
        ("phone", "+1 623 256 7899")}
    # 空缺才填：名字不动，职位补上。
    assert row["name"] == "Javier Carlos" and row["title"] == "Front desk"
    assert contacts.get(conn, info["id"]) is None
    assert conn.execute("SELECT contact_id FROM inbox_messages").fetchone()[0] == javier["id"]


def test_folding_moves_agent_proposals_too(conn):
    from app.agent import proposals
    proposals.ensure_schema(conn)
    javier = contacts.create(conn, 1, {"name": "Javier", "email": "javier@alpha.com"})
    info = contacts.create(conn, 1, {"email": "info@alpha.com"})
    conn.execute(
        "INSERT INTO agent_proposals(kind, lead_no, contact_id, title, fingerprint,"
        " created_at, updated_at) VALUES ('followup', 1, ?, 'Follow up', 'fp-1',"
        " '2026-09-01T09:00:00', '2026-09-01T09:00:00')", (info["id"],))
    conn.commit()
    contacts.fold_into(conn, javier["id"], info["id"])
    assert conn.execute("SELECT contact_id FROM agent_proposals").fetchone()[0] == javier["id"]


def test_folding_moves_quotes_and_orders(conn):
    sales_documents.ensure_schema(conn)
    javier = contacts.create(conn, 1, {"name": "Javier", "email": "javier@alpha.com"})
    info = contacts.create(conn, 1, {"email": "info@alpha.com"})
    conn.execute(
        "INSERT INTO quotes(quote_no, lead_no, contact_id, title, created_at, updated_at)"
        " VALUES ('Q1', 1, ?, 'P3.9 panels', '2026-09-01', '2026-09-01')", (info["id"],))
    conn.commit()
    contacts.fold_into(conn, javier["id"], info["id"])
    assert conn.execute("SELECT contact_id FROM quotes").fetchone()[0] == javier["id"]


def test_the_primary_contact_cannot_be_folded_away(conn):
    javier = contacts.create(conn, 1, {"name": "Javier", "email": "javier@alpha.com"})
    other = contacts.create(conn, 1, {"email": "info@alpha.com"})
    with pytest.raises(contacts.ContactValidation):
        contacts.fold_into(conn, other["id"], javier["id"])


def test_promoting_an_extra_address_swaps_it_with_the_default(conn):
    javier = contacts.create(conn, 1, {"name": "Javier", "email": "javier@alpha.com"})
    channel = contacts.add_channel(conn, javier["id"], "email", "info@alpha.com")
    contacts.promote_channel(conn, channel["id"])
    row = contacts.get(conn, javier["id"])
    assert row["email"] == "info@alpha.com"
    assert [(c["kind"], c["value"]) for c in row["channels"]] == [("email", "javier@alpha.com")]
    # 主要联系人的默认地址就是群发地址，换了要写回客户行。
    assert conn.execute("SELECT email FROM leads WHERE no=1").fetchone()[0] == "info@alpha.com"


def test_an_extra_address_can_be_edited_in_place(conn):
    javier = contacts.create(conn, 1, {"name": "Javier", "email": "javier@alpha.com"})
    channel = contacts.add_channel(conn, javier["id"], "email", "inf@alpha.com")
    contacts.update_channel(conn, channel["id"], "Info@Alpha.com")
    assert contacts.get(conn, javier["id"])["channels"][0]["value"] == "info@alpha.com"
    # 改成默认地址、或改成别人的地址，都不成立。
    with pytest.raises(contacts.ContactValidation):
        contacts.update_channel(conn, channel["id"], "javier@alpha.com")
    contacts.create(conn, 1, {"email": "sales@alpha.com"})
    with pytest.raises(contacts.ContactConflict):
        contacts.update_channel(conn, channel["id"], "sales@alpha.com")
    assert contacts.get(conn, javier["id"])["channels"][0]["value"] == "info@alpha.com"


def test_deleting_an_extra_address_leaves_the_person(conn):
    javier = contacts.create(conn, 1, {"name": "Javier", "email": "javier@alpha.com"})
    channel = contacts.add_channel(conn, javier["id"], "email", "info@alpha.com")
    assert contacts.delete_channel(conn, channel["id"]) is True
    assert contacts.get(conn, javier["id"])["channels"] == []
    assert contacts.also_reach(conn, 1, "javier@alpha.com") == []


def test_deleting_a_contact_takes_its_extra_addresses_with_it(conn):
    contacts.create(conn, 1, {"name": "Main", "email": "main@alpha.com"})
    second = contacts.create(conn, 1, {"name": "Javier", "email": "javier@alpha.com"})
    contacts.add_channel(conn, second["id"], "email", "info@alpha.com")
    contacts.delete(conn, second["id"])
    assert conn.execute("SELECT COUNT(*) FROM contact_channels").fetchone()[0] == 0
    assert contacts.email_leads(conn).get("info@alpha.com") is None
