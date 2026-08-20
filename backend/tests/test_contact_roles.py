import pytest

from app import contact_roles as cr


@pytest.mark.parametrize("title,expected", [
    ("CEO", "decision_maker"),
    ("CEO / Founder", "decision_maker"),
    ("Owner", "decision_maker"),
    ("Founders", "decision_maker"),
    ("President", "decision_maker"),
    ("Purchasing Manager", "decision_maker"),
    ("Gerente General", "decision_maker"),
    ("대표", "decision_maker"),
    ("구매팀장", "decision_maker"),
    ("International Sales", "influencer"),
    ("Commercial Management", "influencer"),
    ("Rentals", "influencer"),
    ("CTO", "technical"),
    ("Engineer", "technical"),
    ("CFO", "finance"),
])
def test_a_stated_title_is_read_as_the_role_it_states(title, expected):
    assert cr.role_for(title) == expected


def test_a_sales_title_outranks_the_word_director_inside_it():
    """'Director of Sales' sells for them; they are not the one who signs for us."""
    assert cr.role_for("Director of Sales") == "influencer"
    assert cr.role_for("Sales Director") == "influencer"


def test_a_word_hiding_inside_another_word_does_not_count():
    """Substring matching read 'Director' as technical, because dire(cto)r contains
    'cto', and 'Coordinator' as a decision maker for its 'coo'."""
    assert cr.role_for("Director") == "decision_maker"   # on its own it is one
    assert cr.role_for("Coordinator") == "other"
    assert cr.role_for("Discount Manager") == "other"


@pytest.mark.parametrize("title", ["", None, "   ", "Team", "Staff", "Contact"])
def test_a_title_that_states_no_role_stays_other(title):
    assert cr.role_for(title) == "other"


def test_only_untouched_contacts_are_considered(conn):
    from app import contacts
    contacts.ensure_schema(conn)
    conn.executescript("""
        INSERT INTO contacts(lead_no, name, title, role, is_primary, source, created_at, updated_at)
            VALUES (1, 'A', 'CEO', 'other', 0, 'test', '2026-08-20', '2026-08-20'),
                   (1, 'B', 'CEO', 'technical', 0, 'test', '2026-08-20', '2026-08-20');
    """)
    conn.commit()
    assert [c["name"] for c in cr.candidates(conn)] == ["A"]


def test_allens_own_labels_are_never_overwritten(conn):
    from app import contacts
    contacts.ensure_schema(conn)
    conn.execute("INSERT INTO contacts(lead_no, name, title, role, is_primary, source, created_at, updated_at)"
                 " VALUES (1, 'B', 'CEO', 'technical', 0, 'test', '2026-08-20', '2026-08-20')")
    conn.commit()
    cr.run(conn, apply=True)
    assert conn.execute("SELECT role FROM contacts WHERE name='B'").fetchone()[0] == "technical"


def test_a_preview_writes_nothing(conn):
    from app import contacts
    contacts.ensure_schema(conn)
    conn.execute("INSERT INTO contacts(lead_no, name, title, role, is_primary, source, created_at, updated_at)"
                 " VALUES (1, 'A', 'CEO', 'other', 0, 'test', '2026-08-20', '2026-08-20')")
    conn.commit()
    rows = cr.run(conn, apply=False)
    assert rows[0]["new_role"] == "decision_maker"
    assert conn.execute("SELECT role FROM contacts WHERE name='A'").fetchone()[0] == "other"


def test_applying_writes_the_role(conn):
    from app import contacts
    contacts.ensure_schema(conn)
    conn.execute("INSERT INTO contacts(lead_no, name, title, role, is_primary, source, created_at, updated_at)"
                 " VALUES (1, 'A', '대표', 'other', 0, 'test', '2026-08-20', '2026-08-20')")
    conn.commit()
    cr.run(conn, apply=True)
    assert conn.execute("SELECT role FROM contacts WHERE name='A'").fetchone()[0] == "decision_maker"
