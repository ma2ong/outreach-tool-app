"""Merging the Xiaoman customer list into leads that mostly already exist (docs/55).

The risk here is not losing records — it is quietly degrading good ones. Xiaoman carries
three things that look like data and are not: phone numbers Allen truncated on purpose so
colleagues on the shared account could not take his customers, job titles the CRM filled
in as "Department", and shared mailbox names standing in for people. These tests guard
the direction of each judgement.
"""
import json

import pytest

from app import xiaoman_import_customers as xic
from app.db import connect, init_schema


def row(**over):
    base = {
        "name": "Basic Tech", "country": "KR", "city": "", "ali_store_id": None,
        "origin_name": "", "cus_tag_info": [], "tel_full_new_info": None,
        "customer": {"name": "", "post": "", "email": "a@basictech.co.kr",
                     "tel_list_info": []},
    }
    base.update(over)
    return base


def load(rows, tmp_path):
    path = tmp_path / "customers.json"
    path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return xic.load(path)


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, email) VALUES
            (1, 'Basic Tech', 'KR', 'sales@basictech.co.kr'),
            (2, 'babo2861@naver.com', 'KR', 'babo2861@naver.com');
    """)
    c.commit()
    return c


def test_alibaba_buyer_identity_records_are_left_out(tmp_path):
    rows = load([row(name="Keep"), row(name="Drop", ali_store_id="270470200")], tmp_path)
    assert [r["company_en"] for r in rows] == ["Keep"]


def test_alibaba_is_decided_by_store_id_not_by_the_source_text(tmp_path):
    # A real customer who once asked a question on Alibaba still says 阿里 in the source.
    rows = load([row(name="Real", origin_name="阿里询盘，TM咨询")], tmp_path)
    assert [r["company_en"] for r in rows] == ["Real"]


def test_a_truncated_phone_is_dropped_rather_than_stored(tmp_path):
    rows = load([row(customer={"email": "a@b.com", "name": "", "post": "",
                               "tel_list_info": [{"info_value": {"tel": "109445"}}]})],
                tmp_path)
    assert rows[0]["phone"] == ""


def test_a_full_phone_is_kept(tmp_path):
    rows = load([row(customer={"email": "a@b.com", "name": "", "post": "",
                               "tel_list_info": [{"info_value": {"tel": "909-680-0141"}}]})],
                tmp_path)
    assert rows[0]["phone"] == "909-680-0141"


@pytest.mark.parametrize("post", ["Department", "Staff", "--"])
def test_crm_filler_is_not_a_job_title(tmp_path, post):
    rows = load([row(customer={"email": "a@b.com", "name": "", "post": post,
                               "tel_list_info": []})], tmp_path)
    assert rows[0]["title"] == ""


def test_a_real_job_title_survives(tmp_path):
    rows = load([row(customer={"email": "a@b.com", "name": "", "post": "President",
                               "tel_list_info": []})], tmp_path)
    assert rows[0]["title"] == "President"


@pytest.mark.parametrize("name", ["info", "sales", "escribe"])
def test_a_shared_mailbox_is_not_a_person(tmp_path, name):
    rows = load([row(customer={"email": f"{'escribe' if name == 'escribe' else 'x'}@b.com",
                               "name": name, "post": "", "tel_list_info": []})], tmp_path)
    assert rows[0]["contact_name"] == ""


def test_another_contact_at_a_known_company_is_not_a_second_company(conn, tmp_path):
    rows = load([row(customer={"email": "mountain@basictech.co.kr", "name": "이창훈",
                               "post": "", "tel_list_info": []})], tmp_path)
    stats = xic.run(conn, rows, apply_changes=True)
    assert (stats["created"], stats["merged"]) == (0, 1)
    assert conn.execute("SELECT contact_name FROM leads WHERE no=1").fetchone()[0] == "이창훈"


def test_two_strangers_on_the_same_free_mail_host_stay_apart(conn, tmp_path):
    rows = load([row(name="Someone Else",
                     customer={"email": "other@naver.com", "name": "", "post": "",
                               "tel_list_info": []})], tmp_path)
    stats = xic.run(conn, rows, apply_changes=True)
    assert stats["created"] == 1


def test_a_local_name_fills_company_local_beside_the_english_one(conn, tmp_path):
    rows = load([row(name="베이직테크",
                     customer={"email": "mountain@basictech.co.kr", "name": "", "post": "",
                               "tel_list_info": []})], tmp_path)
    xic.run(conn, rows, apply_changes=True)
    kept = conn.execute("SELECT company_en, company_local FROM leads WHERE no=1").fetchone()
    assert (kept["company_en"], kept["company_local"]) == ("Basic Tech", "베이직테크")


def test_a_real_name_replaces_a_company_name_that_is_just_the_email(conn, tmp_path):
    rows = load([row(name="LED리더",
                     customer={"email": "babo2861@naver.com", "name": "", "post": "",
                               "tel_list_info": []})], tmp_path)
    xic.run(conn, rows, apply_changes=True)
    kept = conn.execute("SELECT company_en, company_local FROM leads WHERE no=2").fetchone()
    # R8: the name now lives in company_en, so company_local must not repeat it.
    assert kept["company_en"] == "LED리더"
    assert not kept["company_local"]


def test_an_existing_real_name_is_never_overwritten(conn, tmp_path):
    rows = load([row(name="Basictech Co Ltd",
                     customer={"email": "sales@basictech.co.kr", "name": "", "post": "",
                               "tel_list_info": []})], tmp_path)
    xic.run(conn, rows, apply_changes=True)
    assert conn.execute("SELECT company_en FROM leads WHERE no=1").fetchone()[0] == "Basic Tech"


def test_allens_handwritten_note_survives_and_marks_the_deal(conn, tmp_path):
    rows = load([row(name="Basic Tech（成交客户)",
                     customer={"email": "sales@basictech.co.kr", "name": "", "post": "",
                               "tel_list_info": []})], tmp_path)
    xic.run(conn, rows, apply_changes=True)
    kept = conn.execute("SELECT stage, business FROM leads WHERE no=1").fetchone()
    assert kept["stage"] == "won"
    assert "成交客户" in kept["business"]


def test_preview_writes_nothing(conn, tmp_path):
    rows = load([row(name="베이직테크",
                     customer={"email": "mountain@basictech.co.kr", "name": "", "post": "",
                               "tel_list_info": []})], tmp_path)
    xic.run(conn, rows, apply_changes=False)
    assert not conn.execute("SELECT company_local FROM leads WHERE no=1").fetchone()[0]
