from app import contacts, dedupe, health, inbound, replies, repository


def test_first_contact_becomes_primary_and_syncs_legacy_fields(conn):
    contact = contacts.create(conn, 2, {
        "name": "Maria Santos", "title": "Purchasing Manager",
        "email": "Maria@Beta.com", "phone": "+1 555 1000",
        "role": "decision_maker",
    })
    assert contact["is_primary"] is True and contact["email"] == "maria@beta.com"
    lead = conn.execute(
        "SELECT contact_name, title, email, phone FROM leads WHERE no=2").fetchone()
    assert tuple(lead) == ("Maria Santos", "Purchasing Manager", "maria@beta.com", "+1 555 1000")


def test_switch_update_and_delete_primary_contact(conn):
    first = contacts.create(conn, 1, {"name": "Ana", "email": "ana@alpha.com"})
    second = contacts.create(conn, 1, {
        "name": "Tom", "email": "tom@alpha.com", "role": "technical"})
    assert second["is_primary"] is False
    contacts.set_primary(conn, second["id"])
    assert conn.execute("SELECT email FROM leads WHERE no=1").fetchone()[0] == "tom@alpha.com"
    contacts.update(conn, second["id"], {"title": "Technical Director"})
    assert conn.execute("SELECT title FROM leads WHERE no=1").fetchone()[0] == "Technical Director"
    contacts.delete(conn, second["id"])
    promoted = contacts.get(conn, first["id"])
    assert promoted["is_primary"] is True
    assert conn.execute("SELECT email FROM leads WHERE no=1").fetchone()[0] == "ana@alpha.com"


def test_legacy_contact_migration_is_idempotent(conn):
    conn.execute(
        "UPDATE leads SET contact_name='Buyer', title='Owner', email='buyer@gamma.com',"
        " phone='+55 11 9999 0000' WHERE no=3")
    conn.commit()
    assert contacts.migrate_existing(conn)["created"] == 1
    assert contacts.migrate_existing(conn)["created"] == 0
    rows = contacts.list_all(conn, 3)
    assert len(rows) == 1 and rows[0]["source"] == "legacy" and rows[0]["is_primary"]


def test_inserted_lead_immediately_gets_a_primary_contact(conn):
    no = repository.insert_lead(conn, {
        "company_en": "New LED Buyer", "email": "info@newbuyer.com", "phone": "+44 20 1234 5678"})
    row = contacts.list_all(conn, no)[0]
    assert row["is_primary"] and row["email"] == "info@newbuyer.com"


def test_secondary_email_reply_is_attributed_to_company_and_person(conn):
    contacts.create(conn, 1, {"name": "Main", "email": "main@alpha.com"})
    secondary = contacts.create(conn, 1, {
        "name": "Engineer", "email": "engineer@alpha.com", "role": "technical"})
    result = replies.process_messages(conn, [{
        "from_addr": "engineer@alpha.com", "subject": "Re: CAD",
        "body": "Please send drawing", "received_at": "2026-08-04T10:00:00",
    }])
    assert result["replies"] == 1
    inbox = conn.execute("SELECT lead_no, contact_id FROM inbox_messages").fetchone()
    assert inbox["lead_no"] == 1 and inbox["contact_id"] == secondary["id"]


def test_reply_from_new_person_at_known_company_creates_secondary_contact(conn):
    contacts.create(conn, 1, {"name": "Main", "email": "info@alpha.com"})
    result = replies.process_messages(conn, [{
        "from_addr": "john@alpha.com", "from_name": "John Buyer", "subject": "Re: quote",
        "body": "Let's discuss", "received_at": "2026-08-04T10:00:00",
    }])
    assert result["replies"] == 1
    adopted = contacts.find_email(conn, "john@alpha.com", lead_no=1)
    assert adopted["name"] == "John Buyer" and adopted["source"] == "reply"
    assert adopted["is_primary"] == 0
    assert conn.execute("SELECT contact_id FROM inbox_messages").fetchone()[0] == adopted["id"]


def test_secondary_whatsapp_number_matches_without_becoming_primary(conn):
    contacts.create(conn, 1, {"name": "Main", "phone": "+55 11 90000 1111"})
    secondary = contacts.create(conn, 1, {
        "name": "Site tech", "phone": "+55 11 98888 7777", "role": "technical"})
    result = inbound.process_threads(conn, "whatsapp", [{
        "sender": "+55 11 98888-7777", "name": "Site tech",
        "preview": "Need spare modules", "outgoing": False, "unread": True,
    }])
    assert result["lead_nos"] == [1]
    assert conn.execute("SELECT contact_id FROM inbox_messages").fetchone()[0] == secondary["id"]


def test_ambiguous_email_across_companies_is_not_guessed(conn):
    contacts.create(conn, 1, {"email": "shared@gmail.com"})
    contacts.create(conn, 2, {"email": "shared@gmail.com"})
    assert "shared@gmail.com" not in contacts.email_leads(conn)


def test_customer_search_finds_secondary_contact(conn):
    contacts.create(conn, 1, {"name": "Ana Purchasing", "email": "ana.secondary@alpha.com"})
    assert [lead.no for lead in repository.list_leads(conn, search="Ana Purchasing")] == [1]
    assert 1 in {lead.no for lead in repository.list_leads(conn, has="email")}


def test_merge_dedupes_same_email_and_preserves_people(conn):
    first = contacts.create(conn, 1, {"name": "Buyer", "email": "buyer@alpha.com"})
    contacts.create(conn, 2, {
        "name": "Buyer", "email": "buyer@alpha.com", "title": "Owner"})
    extra = contacts.create(conn, 2, {"name": "Engineer", "email": "tech@alpha.com"})
    dedupe.merge_leads(conn, 1, [2])
    rows = contacts.list_all(conn, 1)
    assert {r["email"] for r in rows} == {"buyer@alpha.com", "tech@alpha.com"}
    assert contacts.get(conn, first["id"])["title"] == "Owner"
    assert contacts.get(conn, extra["id"])["lead_no"] == 1


def test_merge_promotes_reachable_contact_when_keeper_primary_has_no_channel(conn):
    contacts.create(conn, 1, {"name": "Unknown buyer"})
    reachable = contacts.create(conn, 2, {"name": "Owner", "email": "owner@beta.com"})
    dedupe.merge_leads(conn, 1, [2])
    assert contacts.get(conn, reachable["id"])["is_primary"] is True
    assert conn.execute("SELECT email FROM leads WHERE no=1").fetchone()[0] == "owner@beta.com"


def test_contact_history_prevents_bulk_cleaning(conn):
    conn.execute(
        "UPDATE leads SET website=NULL, instagram=NULL, email=NULL, phone=NULL, facebook=NULL WHERE no=2")
    conn.commit()
    assert 2 in {lead["no"] for lead in health.cleanable(conn)}
    contacts.create(conn, 2, {"name": "Unknown buyer"})
    assert 2 not in {lead["no"] for lead in health.cleanable(conn)}
