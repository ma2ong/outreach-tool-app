"""The customer type a company is filed under (docs/60).

The list column read `target_fit`, which 39 of 303 Korean leads have, while the type
Allen actually assigned sits in `tags`, which 176 of them have. So the column was empty
for reasons that had nothing to do with his data.

`tags` is a mixed column: his vocabulary (工程商) and the classifier's working notes
(icp:signage) share it, and the Xiaoman import joined multiple tags with 、 while the tag
box uses commas. Both have to be read correctly before either is shown as a type.
"""
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
            (4, 'Plain Co', NULL, 'USA', NULL, NULL, NULL);
        INSERT INTO contacts(lead_no, name, title, is_primary, created_at, updated_at)
        VALUES
            (1, '김종수', '대표', 1, '2026-08-01', '2026-08-01'),
            (1, 'Someone Else', 'Staff', 0, '2026-08-01', '2026-08-01');
    """)
    c.commit()
    return c


def test_a_classifier_note_is_not_a_customer_type():
    assert ct.customer_types("icp:signage") == []


def test_his_own_tag_is_a_customer_type():
    assert ct.customer_types("工程商") == ["工程商"]


@pytest.mark.parametrize("raw", ["工程商、租赁客户", "工程商,租赁客户", "工程商，租赁客户"])
def test_every_separator_in_use_splits(raw):
    # The Xiaoman import wrote 、 and the tag box writes , — reading only one of them
    # invents a type called "工程商、租赁客户".
    assert ct.customer_types(raw) == ["工程商", "租赁客户"]


def test_the_machine_note_is_dropped_but_the_real_tag_survives():
    assert ct.customer_types("工程商、租赁客户,icp:signage") == ["工程商", "租赁客户"]


def test_the_picker_offers_his_vocabulary(conn):
    assert ct.options(conn)[:5] == list(ct.KNOWN)


def test_the_picker_never_offers_a_joined_pair_as_one_type(conn):
    assert "工程商、租赁客户" not in ct.options(conn)


def test_a_type_he_invented_joins_the_picker(conn):
    conn.execute("UPDATE leads SET tags='舞台租赁' WHERE no=4")
    conn.commit()
    assert "舞台租赁" in ct.options(conn)


def test_the_list_shows_the_type_he_assigned(conn):
    by_no = {l.no: l for l in repo.list_leads(conn)}
    assert by_no[1].customer_types == ["工程商"]
    assert by_no[3].customer_types == ["工程商", "租赁客户"]
    assert by_no[2].customer_types == []


def test_the_list_shows_the_primary_contact_not_the_first_one(conn):
    by_no = {l.no: l for l in repo.list_leads(conn)}
    assert (by_no[1].primary_contact, by_no[1].primary_title) == ("김종수", "대표")


def test_a_name_he_annotated_is_shown_as_he_wrote_it(conn):
    # 전완기_已回복 is his handwriting, not dirty data.
    by_no = {l.no: l for l in repo.list_leads(conn)}
    assert by_no[2].primary_contact == "전완기_已回复"


def test_a_company_with_no_contact_shows_nothing_invented(conn):
    by_no = {l.no: l for l in repo.list_leads(conn)}
    assert by_no[4].primary_contact is None
