"""Importing customers Allen already worked, without treating them as strangers.

The system sends a first cold email to every untouched lead each morning. Importing a
customer he quoted in 2023 as "untouched" means that customer wakes up to
"Saw the rental work you do around Houston. We manufacture LED panels" — reading, from
their side, as a supplier who has forgotten who they are. That is worse than never
having written, so these tests mostly guard the direction of each mistake.
"""
import datetime as dt

import pytest

from app import import_customers
from app.db import connect, init_schema

TODAY = dt.date(2026, 8, 26)


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, email, phone, website, hook) VALUES
            (1, 'Verum AV', 'USA', 'info@verumav.com', '346-837-8628', 'verumav.com',
             'Saw the rental work.');
    """)
    c.commit()
    return c


# ---------------------------------------------------------------- the one that matters

def test_an_imported_customer_is_treated_as_already_contacted(conn):
    """The direction of this mistake is not symmetric. Mislabelling an old customer
    "untouched" costs a relationship; mislabelling a stranger "touched" costs a few days
    of him sitting quietly in a list he was not in yesterday."""
    result = import_customers.apply(conn, [
        {"company_en": "Old Friend Displays", "email": "buyer@oldfriend.com"}], today=TODAY)
    assert result["created"] == 1
    no = conn.execute("SELECT no FROM leads WHERE company_en='Old Friend Displays'").fetchone()["no"]
    row = conn.execute("SELECT status FROM outreach WHERE lead_no=? AND channel='email'",
                       (no,)).fetchone()
    assert row and row["status"] == "messaged"


def test_an_imported_customer_does_not_land_in_todays_cold_queue(conn):
    """The whole point, stated as the outcome rather than the mechanism."""
    from app import outreach as email_outreach

    import_customers.apply(conn, [
        {"company_en": "Old Friend Displays", "email": "buyer@oldfriend.com"}], today=TODAY)
    no = conn.execute("SELECT no FROM leads WHERE company_en='Old Friend Displays'").fetchone()["no"]
    assert email_outreach.eligible_leads(conn, [no], "email") == []


def test_an_unknown_contact_date_is_recorded_as_unknown(conn):
    """Writing today's date as if it were the contact date would be inventing a fact —
    the same rule as spec 45."""
    import_customers.apply(conn, [
        {"company_en": "No Date Co", "email": "x@nodate.com"}], today=TODAY)
    note = conn.execute(
        "SELECT text FROM notes WHERE lead_no=(SELECT no FROM leads WHERE company_en='No Date Co')"
    ).fetchone()
    assert note and "日期未知" in note["text"]


def test_a_supplied_contact_date_is_kept(conn):
    import_customers.apply(conn, [
        {"company_en": "Dated Co", "email": "x@dated.com", "last_contact": "2023-05-11"}],
        today=TODAY)
    row = conn.execute(
        "SELECT message_sent_date FROM outreach WHERE lead_no="
        "(SELECT no FROM leads WHERE company_en='Dated Co')").fetchone()
    assert row["message_sent_date"] == "2023-05-11"


# ---------------------------------------------------------------- merging

def test_an_existing_record_is_never_overwritten(conn):
    """The CRM export may be three years old; the record here was read off their site
    last month. Filling a blank is a gain, replacing a verified value is a loss."""
    result = import_customers.apply(conn, [
        {"company_en": "Verum AV", "email": "old@verumav.com", "city": "Houston, TX"}],
        today=TODAY)
    row = conn.execute("SELECT email, city FROM leads WHERE no=1").fetchone()
    assert row["email"] == "info@verumav.com"   # kept
    assert row["city"] == "Houston, TX"          # filled, was empty
    assert result["merged"] == 1 and result["created"] == 0


def test_a_match_can_be_made_on_website_or_company_name(conn):
    import_customers.apply(conn, [
        {"company_en": "Verum AV Solutions", "website": "verumav.com"}], today=TODAY)
    assert conn.execute("SELECT COUNT(*) c FROM leads").fetchone()["c"] == 1


# ---------------------------------------------------------------- relationship state

def test_a_won_customer_is_marked_won_not_prospected(conn):
    """These are the most valuable records in the file, and the ones a self-introduction
    would embarrass us in front of."""
    import_customers.apply(conn, [
        {"company_en": "Repeat Buyer", "email": "r@buyer.com", "status": "成交"}], today=TODAY)
    assert conn.execute(
        "SELECT stage FROM leads WHERE company_en='Repeat Buyer'").fetchone()["stage"] == "won"


def test_a_refusal_stops_all_contact(conn):
    import_customers.apply(conn, [
        {"company_en": "Not Interested Ltd", "email": "n@ni.com", "status": "黑名单"}],
        today=TODAY)
    assert conn.execute(
        "SELECT do_not_contact FROM leads WHERE company_en='Not Interested Ltd'"
    ).fetchone()["do_not_contact"] == 1


def test_a_lost_deal_is_kept_as_history_not_as_a_fresh_lead(conn):
    import_customers.apply(conn, [
        {"company_en": "Lost One", "email": "l@lost.com", "status": "丢单"}], today=TODAY)
    assert conn.execute(
        "SELECT stage FROM leads WHERE company_en='Lost One'").fetchone()["stage"] == "lost"


# ---------------------------------------------------------------- reading the file

def test_chinese_and_english_headers_both_map(conn):
    rows = import_customers.map_rows([
        {"公司名称": "中文列公司", "邮箱": "a@cn.com", "国家": "USA", "联系人": "王先生"},
    ])
    assert rows[0]["company_en"] == "中文列公司"
    assert rows[0]["email"] == "a@cn.com"
    assert rows[0]["contact_name"] == "王先生"


def test_an_unrecognised_column_is_kept_but_not_guessed_at(conn):
    """The information stays; it just does not get to pretend it is structured data."""
    rows = import_customers.map_rows([
        {"Company": "X Co", "Email": "x@x.com", "客户等级": "A类", "神秘字段": "42"}])
    assert "客户等级：A类" in rows[0]["business"]
    assert "神秘字段：42" in rows[0]["business"]


def test_a_row_with_no_company_and_no_contact_is_not_a_customer(conn):
    result = import_customers.apply(conn, [{"business": "只有备注"}], today=TODAY)
    assert result["created"] == 0 and result["skipped"] == 1


def test_the_preview_says_what_would_happen_before_anything_is_written(conn):
    preview = import_customers.preview(conn, [
        {"company_en": "Verum AV", "email": "x@verumav.com"},
        {"company_en": "Brand New Co", "email": "n@new.com"},
        {"business": "垃圾行"},
    ])
    assert preview["created"] == 1 and preview["merged"] == 1 and preview["skipped"] == 1
    assert conn.execute("SELECT COUNT(*) c FROM leads").fetchone()["c"] == 1  # 没写库
