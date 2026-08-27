from app import countries, repository as repo


def test_every_spelling_of_one_market_lands_on_one_name():
    """The case this exists for: 130 leads in "Korea", 14 in "South Korea", 1 in "韩国"
    made three bars on the dashboard and three answers to the same filter."""
    for written in ("Korea", "korea", " KOREA ", "韩국".replace("국", "国"),
                    "Korea, South", "Republic of Korea", "KR", "South Korea"):
        assert countries.normalize(written) == "South Korea"


def test_canonical_names_match_what_the_book_already_uses():
    """Chosen so switching this on needed no migration and cannot re-label old rows."""
    assert countries.normalize("United States") == "USA"
    assert countries.normalize("United Kingdom") == "UK"
    assert countries.normalize("Brasil") == "Brazil"
    assert countries.normalize("méxico") == "Mexico"


def test_an_unknown_country_is_trimmed_but_never_guessed_at():
    """Title-casing "UAE" into "Uae" would be a mistake dressed up as tidiness."""
    assert countries.normalize("  UAE ") == "UAE"
    assert countries.normalize("Côte d'Ivoire") == "Côte d'Ivoire"
    assert countries.normalize(None) is None


def test_blank_and_missing_mean_the_same_thing():
    # Keeping both spellings of "we do not know" put an unlabelled empty row in the
    # country filter that selected three leads out of 1313.
    assert countries.normalize("") is None
    assert countries.normalize("   ") is None


def test_a_new_lead_is_normalized_on_the_way_in(conn):
    no = repo.insert_lead(conn, {"company_en": "Hanul LED", "country": "Korea",
                                 "website": "hanul.co.kr"})
    assert conn.execute("SELECT country FROM leads WHERE no=?", (no,)).fetchone()[0] == \
        "South Korea"


def test_editing_the_country_by_hand_is_normalized_too(conn):
    repo.update_lead(conn, 1, {"country": "korea"})
    assert conn.execute("SELECT country FROM leads WHERE no=1").fetchone()[0] == "South Korea"
