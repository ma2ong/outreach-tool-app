"""Customer type storage/display compatibility for Rental / Install / General."""
import pytest

from app import customer_types as ct
from app import repository as repo
from app.db import connect, init_schema


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    from app.contacts import ensure_schema
    ensure_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, company_local, country, tags, contact_name, title)
        VALUES
            (1, 'Kinoton Korea', '키노톤코리아', 'South Korea', '工程商', NULL, NULL),
            (2, 'Samik', '삼익전자', 'South Korea', 'icp:signage', '전완기_已回复', NULL),
            (3, 'Hyosung', '효성ITX', 'South Korea', '工程商、租赁客户', NULL, NULL),
            (4, 'Plain Co', NULL, 'USA', NULL, NULL, NULL),
            (5, 'Dealer Co', NULL, 'USA', '批发商', NULL, NULL);
        INSERT INTO contacts(lead_no, name, title, is_primary, created_at, updated_at)
        VALUES
            (1, '김종수', '대표', 1, '2026-08-01', '2026-08-01'),
            (1, 'Someone Else', 'Staff', 0, '2026-08-01', '2026-08-01');
    """)
    c.commit()
    return c


def test_machine_note_is_not_a_customer_type():
    assert ct.customer_types("icp:signage") == []


@pytest.mark.parametrize("raw,expected", [
    ("Rental", ["Rental"]),
    ("租赁商", ["Rental"]),
    ("Install", ["Install"]),
    ("工程商", ["Install"]),
    ("General", ["General"]),
    ("批发商", ["General"]),
    ("广告商", ["General"]),
    ("outdoor", ["General"]),
])
def test_old_and_new_labels_canonicalise(raw, expected):
    assert ct.customer_types(raw) == expected


@pytest.mark.parametrize("raw", ["工程商、租赁客户", "工程商,租赁客户", "工程商，租赁客户"])
def test_all_separators_are_supported(raw):
    assert ct.customer_types(raw) == ["Install", "Rental"]


def test_machine_note_is_dropped_but_customer_type_survives():
    assert ct.customer_types("工程商、租赁客户,icp:signage") == ["Install", "Rental"]


def test_picker_offers_exactly_three_values(conn):
    assert ct.options(conn) == ["Rental", "Install", "General"]


def test_arbitrary_tags_do_not_become_customer_types(conn):
    conn.execute("UPDATE leads SET tags='舞台租赁' WHERE no=4")
    conn.commit()
    assert ct.customer_types("舞台租赁") == []
    assert ct.options(conn) == ["Rental", "Install", "General"]


def test_list_shows_canonical_customer_type(conn):
    by_no = {l.no: l for l in repo.list_leads(conn)}
    assert by_no[1].customer_types == ["Install"]
    assert by_no[3].customer_types == ["Install", "Rental"]
    assert by_no[5].customer_types == ["General"]
    assert by_no[2].customer_types == []


def test_list_shows_primary_contact(conn):
    by_no = {l.no: l for l in repo.list_leads(conn)}
    assert (by_no[1].primary_contact, by_no[1].primary_title) == ("김종수", "대표")


def test_annotated_contact_name_is_preserved(conn):
    by_no = {l.no: l for l in repo.list_leads(conn)}
    assert by_no[2].primary_contact == "전완기_已回复"


def test_company_without_contact_stays_blank(conn):
    by_no = {l.no: l for l in repo.list_leads(conn)}
    assert by_no[4].primary_contact is None
