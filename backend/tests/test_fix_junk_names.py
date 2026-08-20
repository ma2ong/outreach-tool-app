from app import fix_junk_names as fix


def test_a_domain_becomes_an_honest_name():
    assert fix.name_from_domain("https://www.blipbillboards.com/") == "Blipbillboards"
    assert fix.name_from_domain("optec.com") == "Optec"
    assert fix.name_from_domain("led-screen-rental.com") == "Led Screen Rental"
    assert fix.name_from_domain(None) == ""


def test_a_tagline_is_not_a_company_name():
    assert fix.looks_like_a_name("Optec Displays")
    assert fix.looks_like_a_name("LED Screen Rental Service")
    # what the sites actually returned, and what must never land in the company column
    assert not fix.looks_like_a_name("Self-Serve Digital Billboard Advertising Platform")
    assert not fix.looks_like_a_name("Staging & Event Solutions for Concerts")
    assert not fix.looks_like_a_name("")


def test_only_junk_named_leads_are_touched(conn):
    conn.execute("UPDATE leads SET company_en='Contact' WHERE no=1")
    conn.commit()
    assert [c["no"] for c in fix.candidates(conn)] == [1]


def test_a_real_site_name_wins_over_the_domain(conn):
    conn.execute("UPDATE leads SET company_en='Contact Us', website='optec.com' WHERE no=1")
    conn.commit()
    fix.run(conn, apply=True, fetch_fn=lambda url: "# Optec Displays\n\ncontact us")
    assert conn.execute("SELECT company_en FROM leads WHERE no=1").fetchone()[0] == "Optec Displays"


def test_a_marketing_title_falls_back_to_the_domain(conn):
    conn.execute("UPDATE leads SET company_en='Home', website='blipbillboards.com' WHERE no=1")
    conn.commit()
    fix.run(conn, apply=True,
            fetch_fn=lambda url: "# Self-Serve Digital Billboard Advertising Platform")
    assert conn.execute("SELECT company_en FROM leads WHERE no=1").fetchone()[0] == "Blipbillboards"


def test_a_dead_site_still_gets_a_name(conn):
    conn.execute("UPDATE leads SET company_en='404', website='eidim.com' WHERE no=1")
    conn.commit()
    def boom(url):
        raise RuntimeError("site is behind Cloudflare")
    fix.run(conn, apply=True, fetch_fn=boom)
    assert conn.execute("SELECT company_en FROM leads WHERE no=1").fetchone()[0] == "Eidim"


def test_the_rename_is_traceable_afterwards(conn):
    conn.execute("UPDATE leads SET company_en='Contact', website='optec.com' WHERE no=1")
    conn.commit()
    fix.run(conn, apply=True, fetch_fn=lambda url: "# Optec Displays")
    note = conn.execute("SELECT text FROM notes WHERE lead_no=1 ORDER BY id DESC").fetchone()[0]
    assert "Contact" in note and "Optec Displays" in note


def test_a_preview_changes_nothing(conn):
    conn.execute("UPDATE leads SET company_en='Contact', website='optec.com' WHERE no=1")
    conn.commit()
    rows = fix.run(conn, apply=False, fetch_fn=lambda url: "# Optec Displays")
    assert rows[0]["new_name"] == "Optec Displays"
    assert conn.execute("SELECT company_en FROM leads WHERE no=1").fetchone()[0] == "Contact"
    assert conn.execute("SELECT COUNT(*) c FROM notes WHERE lead_no=1").fetchone()["c"] == 0


def test_nothing_is_ever_deleted(conn):
    """These records have real websites and real contacts. Renaming is the whole job."""
    before = conn.execute("SELECT COUNT(*) c FROM leads").fetchone()["c"]
    conn.execute("UPDATE leads SET company_en='Page not found' WHERE no=1")
    conn.commit()
    fix.run(conn, apply=True, fetch_fn=lambda url: "")
    assert conn.execute("SELECT COUNT(*) c FROM leads").fetchone()["c"] == before
