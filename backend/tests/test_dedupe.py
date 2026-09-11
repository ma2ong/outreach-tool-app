import pytest

from app import dedupe, repository
from app.db import connect, init_schema


def test_normalize_website():
    assert dedupe.normalize_website("https://www.Daktronics.com/") == "daktronics.com"
    assert dedupe.normalize_website("http://x.com") == "x.com"
    assert dedupe.normalize_website("x.com/path") == "x.com/path"
    assert dedupe.normalize_website(None) is None
    assert dedupe.normalize_website("") == ""


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, website, email, phone) VALUES
            (1, 'Daktronics', 'USA', 'https://www.daktronics.com', NULL, NULL),
            (2, 'Daktronics Inc', 'USA', 'daktronics.com', 'sales@daktronics.com', '+1 555'),
            (3, 'Insane Impact', 'USA', NULL, 'a@insane.com', NULL),
            (4, 'insane impact', 'USA', 'insaneimpact.com', NULL, NULL),
            (5, 'Unique Co', 'Chile', 'unique.cl', NULL, NULL);
        INSERT INTO outreach(lead_no, channel, status, touch_count, reply_received) VALUES
            (1, 'email', 'messaged', 1, 0),
            (2, 'email', 'replied', 2, 1),
            (2, 'whatsapp', 'messaged', 1, 0);
        INSERT INTO notes(lead_no, created_at, text) VALUES (2, '2026-07-01', 'asked for quote');
    """)
    c.commit()
    return c


def test_normalize_all_websites(conn):
    changed = dedupe.normalize_all_websites(conn)
    assert changed == 1  # only lead 1 had scheme/www form
    assert conn.execute("SELECT website FROM leads WHERE no=1").fetchone()["website"] == "daktronics.com"


def test_find_groups_by_normalized_website_and_name(conn):
    groups = dedupe.find_duplicate_groups(conn)
    assert {(g["keep"], tuple(g["dups"])) for g in groups} == {(1, (2,)), (3, (4,))}


def test_merge_keeps_reply_fills_fields_moves_notes(conn):
    dedupe.merge_leads(conn, 1, [2])
    assert conn.execute("SELECT COUNT(*) FROM leads WHERE no=2").fetchone()[0] == 0
    keeper = conn.execute("SELECT * FROM leads WHERE no=1").fetchone()
    assert keeper["email"] == "sales@daktronics.com"   # filled from dup
    assert keeper["phone"] == "+1 555"
    o = {r["channel"]: r for r in conn.execute("SELECT * FROM outreach WHERE lead_no=1")}
    assert o["email"]["status"] == "replied"           # reply never lost
    assert o["email"]["touch_count"] == 3              # 1 + 2 combined
    assert o["whatsapp"]["status"] == "messaged"       # dup-only channel moved over
    assert conn.execute("SELECT lead_no FROM notes").fetchone()["lead_no"] == 1


def test_merge_all_and_find_duplicate_normalizes(conn):
    res = dedupe.merge_all(conn)
    assert res == {"groups": 2, "removed": 2}
    assert dedupe.find_duplicate_groups(conn) == []
    # find_duplicate now matches regardless of input form
    assert repository.find_duplicate(conn, website="https://WWW.daktronics.com/") == 1


def test_insert_lead_stores_normalized(conn):
    no = repository.insert_lead(conn, {"company_en": "New", "website": "https://www.new.com/"})
    assert conn.execute("SELECT website FROM leads WHERE no=?", (no,)).fetchone()["website"] == "new.com"


def test_a_merge_never_costs_the_company_its_email(tmp_path):
    """Two records of one company, each reachable on a different channel (docs/live).

    DisplayHub #291 carried the address and #361 the number. Demoting one primary and
    then syncing the lead from the other wrote the email back as NULL, and a company
    with no email is in no email path at all.
    """
    from app import contacts, dedupe
    from app.db import connect, init_schema

    conn = connect(str(tmp_path / "t.db"))
    init_schema(conn)
    contacts.ensure_schema(conn)
    conn.executescript("""
        INSERT INTO leads(no, company_en, country, email, email_status) VALUES
            (291, 'Display Hub Ltd', 'South Korea', 'support@displayhub.com', 'role');
        INSERT INTO leads(no, company_en, country, phone) VALUES
            (361, 'DisplayHub', 'South Korea', '+82 2-546-3288');
    """)
    conn.commit()
    contacts.migrate_lead(conn, 291)
    contacts.migrate_lead(conn, 361)

    dedupe.merge_leads(conn, keep=361, dups=[291])

    kept = conn.execute("SELECT email, phone FROM leads WHERE no=361").fetchone()
    assert kept["email"] == "support@displayhub.com"
    assert kept["phone"] == "+82 2-546-3288"


# ------------------------------------------------ docs/129: what counts as the same company

def _lead(conn, no, **f):
    cols = {"company_en": None, "company_local": None, "country": None, "website": None,
            "email": None, "phone": None, "instagram": None, "do_not_contact": 0, **f}
    conn.execute(f"INSERT INTO leads(no, {', '.join(cols)}) VALUES (?, {', '.join('?' * len(cols))})",
                 [no, *cols.values()])
    conn.commit()


def _pairs(conn):
    return {(g["keep"], tuple(g["dups"])) for g in dedupe.find_duplicate_groups(conn)}


def test_a_shared_contact_email_makes_one_company(conn):
    from app import contacts
    _lead(conn, 10, company_en="Shown Probe", country="South Korea", website="shownprove.co.kr")
    _lead(conn, 11, company_en="Shownprove", website="shownprove.com", email="snp@shownprove.com")
    contacts.create(conn, 10, {"email": "snp@shownprove.com"})
    assert (10, (11,)) in _pairs(conn)


def test_the_legal_form_is_not_part_of_the_name(conn):
    _lead(conn, 10, company_en="SNTech", company_local="에스엔테크", country="South Korea")
    _lead(conn, 11, company_en="Sntls", company_local="(주)에스엔테크", country="South Korea",
          website="sntls.co.kr")
    assert (10, (11,)) in _pairs(conn)


def test_the_same_name_in_two_countries_is_two_companies(conn):
    _lead(conn, 10, company_en="LED Solutions Canada", company_local="LED Solutions",
          country="Canada", website="ledsolutions.ca")
    _lead(conn, 11, company_en="Ledsolutions", country="Finland", website="ledsolutions.fi")
    assert not any(10 in (k, *d) for k, d in _pairs(conn))
    assert any(g["keep"] == 10 for g in dedupe.find_possible_duplicates(conn))


def test_a_blog_host_shared_by_everyone_proves_nothing(conn):
    _lead(conn, 10, company_en="A", country="South Korea", website="blog.naver.com/a")
    _lead(conn, 11, company_en="B", country="South Korea", website="blog.naver.com/b")
    assert not any(10 in (k, *d) for k, d in _pairs(conn))


def test_one_phone_two_websites_is_for_a_person_to_decide(conn):
    _lead(conn, 10, company_en="ATH Productions", country="USA", website="athproductions.com",
          phone="+14098605551")
    _lead(conn, 11, company_en="Bounce Multimedia", country="USA", website="bouncemultimedia.com",
          phone="+14098605551")
    assert not any(10 in (k, *d) for k, d in _pairs(conn))
    assert any(g["keep"] == 10 for g in dedupe.find_possible_duplicates(conn))


def test_but_a_stub_with_only_that_phone_is_the_same_company(conn):
    _lead(conn, 10, company_en="RDL LED", country="USA", phone="+19096800141")
    _lead(conn, 11, company_en="Reddotlogics", country="USA", website="reddotlogics.com",
          phone="+19096800141")
    assert (10, (11,)) in _pairs(conn)


def test_do_not_contact_survives_the_merge(conn):
    _lead(conn, 10, company_en="Ailed", country="South Korea", website="ailed.co.kr")
    _lead(conn, 11, company_en="Ailed Co., Ltd", country="South Korea", website="ailed.co.kr",
          do_not_contact=1)
    dedupe.merge_leads(conn, 10, [11])
    assert conn.execute("SELECT do_not_contact FROM leads WHERE no=10").fetchone()[0] == 1
