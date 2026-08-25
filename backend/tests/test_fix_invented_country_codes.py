from app.fix_invented_country_codes import is_invented, local_form


def test_invented_prefix_is_detected():
    assert is_invented("+8777734346")   # eidim.com's toll-free number
    assert is_invented("+7472624770")


def test_real_country_codes_are_left_alone():
    for real in ("+8613809866355", "+5511956635316", "+821012345678", "+16162021473"):
        assert not is_invented(real), real


def test_local_numbers_are_not_touched():
    assert not is_invented("877.773.4346")
    assert not is_invented(None)


def test_local_form_groups_north_american_numbers():
    assert local_form("+7472624770") == "747-262-4770"
    assert local_form("+20230831") == "20230831"


def test_real_korean_number_is_never_rewritten():
    """'+82 2 510-2000' has the same ten-digit shape as a US local number stored with
    an invented '+'. Shape alone cannot separate them, so neither is rewritten."""
    assert not is_invented("+82 2 510-2000")


def test_suspects_report_without_changing_anything(tmp_path):
    from app.db import connect, init_schema
    from app.fix_invented_country_codes import suspects

    conn = connect(str(tmp_path / "t.db"))
    init_schema(conn)
    conn.executescript("""
        INSERT INTO leads(no, company_en, country, phone) VALUES
            (1, 'Verum AV', 'USA', '+3468378628'),
            (2, 'Samik', 'South Korea', '+82 2 510-2000');
    """)
    conn.commit()
    found = suspects(conn)
    assert [row["no"] for row in found] == [1]
    assert found[0]["reads_as"] == "Spain"
    assert conn.execute("SELECT phone FROM leads WHERE no=1").fetchone()["phone"] == "+3468378628"
