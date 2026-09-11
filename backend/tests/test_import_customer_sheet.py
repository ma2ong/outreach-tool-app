"""The sheet Allen keeps by hand (docs/118).

Most of these tests guard an instruction he wrote in Chinese prose in a 备注 cell. Getting
one of them backwards does not produce a wrong number on a dashboard — it sends a signed
company email to a customer he told us not to write to, and that cannot be taken back.
"""
import datetime as dt

import pytest

from app import import_customer_sheet as sheet
from app.db import connect, init_schema

TODAY = dt.date(2026, 9, 10)


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, email, website, business) VALUES
            (1, 'Samik Electronics', 'South Korea', 'swyun@samikdisplay.co.kr',
             'samikdisplay.co.kr', 'LED displays for stadiums');
    """)
    c.commit()
    return c


def row(**over) -> dict:
    base = {"公司名称": "PIXEL Innovation", "联系人邮箱": "hi@pixel.kr", "国家地区": "韩国",
            "标签": "工程商", "公司网址": "http://pixel.kr"}
    base.update(over)
    return base


def parse(**over) -> dict:
    return sheet.parse_row(row(**over))


def one(conn, name: str):
    return conn.execute("SELECT * FROM leads WHERE company_en=? OR company_local=?",
                        (name, name)).fetchone()


# ------------------------------------------------------- R1 what the 备注 column orders

def test_only_file_it_never_write_to_it(conn):
    sheet.apply(conn, [parse(备注="tony的客户，只入库不联系")], today=TODAY)
    assert one(conn, "PIXEL Innovation")["do_not_contact"] == 1


def test_a_closed_customer_is_not_written_to_either(conn):
    """Allen: 我自己的成交客户也是只入库不联系 — even where the cell does not spell it out."""
    sheet.apply(conn, [parse(备注="我的美国成交客户")], today=TODAY)
    assert one(conn, "PIXEL Innovation")["do_not_contact"] == 1


def test_keep_contacting_beats_the_word_closed(conn):
    """成交客户/强力客户，长时间未再下单了，继续联系 — the more specific half is his judgement,
    and a keyword must not overrule it."""
    sheet.apply(conn, [parse(备注="成交客户/强力客户，长时间未再下单了，继续联系")], today=TODAY)
    assert one(conn, "PIXEL Innovation")["do_not_contact"] == 0


def test_the_instruction_can_be_written_into_the_company_name(conn):
    """(주)컴텔싸인_成交客户 — and the name itself must not keep the marker."""
    sheet.apply(conn, [parse(公司名称="(주)컴텔싸인_成交客户", 公司简称="Comtel Sign")], today=TODAY)
    lead = one(conn, "Comtel Sign")
    assert lead["do_not_contact"] == 1
    assert lead["company_local"] == "(주)컴텔싸인"


# --------------------------------------------- R2 the request the sender cannot fulfil

ANON = ("crystal的成交客户,可以用我的allenma2ong@gmail.com邮箱来联系对方，"
        "对这家先不要说出我的公司名")


def test_write_from_my_gmail_without_naming_the_company_means_do_not_auto_send(conn):
    record = parse(备注=ANON)
    sheet.apply(conn, [record], today=TODAY)
    assert one(conn, "PIXEL Innovation")["do_not_contact"] == 1


def test_that_row_is_named_in_the_report_so_a_human_picks_it_up(conn):
    record = parse(备注=ANON)
    assert sheet.plan(conn, [record])["manual_only"] == ["PIXEL Innovation"]


def test_allens_own_mailbox_never_becomes_a_customer_address(conn):
    record = parse(联系人邮箱="", 备注=ANON)
    assert sheet.ALLEN_MAILBOX not in record["emails"]
    sheet.apply(conn, [record], today=TODAY)
    assert not conn.execute("SELECT 1 FROM contacts WHERE lower(email)=?",
                            (sheet.ALLEN_MAILBOX,)).fetchone()


# ------------------------------------------------ R3 contacted before, or a stranger

def test_no_means_written_to_and_never_got_through(conn):
    """否 is not "never tried" — it must not earn a first cold email."""
    sheet.apply(conn, [parse(是否取得联系="否")], today=TODAY)
    lead = one(conn, "PIXEL Innovation")
    assert lead["stage"] == "contacted"
    status = conn.execute("SELECT status FROM outreach WHERE lead_no=? AND channel='email'",
                          (lead["no"],)).fetchone()
    assert status["status"] == "messaged"


def test_an_empty_cell_is_a_stranger_and_keeps_its_place_in_the_cold_queue(conn):
    sheet.apply(conn, [parse()], today=TODAY)
    lead = one(conn, "PIXEL Innovation")
    assert lead["stage"] == "new"
    assert conn.execute("SELECT 1 FROM outreach WHERE lead_no=?", (lead["no"],)).fetchone() is None


# ------------------------------------------------------- R4 an existing record wins

def test_an_existing_lead_keeps_what_it_already_has(conn):
    sheet.apply(conn, [parse(公司名称="Samik Electronics", 联系人邮箱="other@samikdisplay.co.kr",
                             公司网址="http://old-samik.kr")], today=TODAY)
    lead = one(conn, "Samik Electronics")
    assert lead["email"] == "swyun@samikdisplay.co.kr"
    assert lead["website"] == "samikdisplay.co.kr"


def test_but_blank_fields_get_filled(conn):
    sheet.apply(conn, [parse(公司名称="Samik Electronics", 联系人邮箱="swyun@samikdisplay.co.kr",
                             联系人电话="+82 10-1234-5678", 标签="工程商,租赁商")], today=TODAY)
    lead = one(conn, "Samik Electronics")
    assert lead["phone"] == "+82 10-1234-5678"
    assert lead["tags"] == "工程商,租赁商"


def test_the_row_finds_its_lead_by_website_when_the_email_is_new(conn):
    result = sheet.apply(conn, [parse(公司名称="삼익전자", 公司简称="Samik",
                                      联系人邮箱="new@samikdisplay.co.kr",
                                      公司网址="https://www.samikdisplay.co.kr/")], today=TODAY)
    assert result == {**result, "created": 0, "merged": 1}


# --------------------------------------------------------- R5 Korean names, R6 people

def test_a_korean_name_goes_to_company_local_and_the_roman_one_to_company_en(conn):
    sheet.apply(conn, [parse(公司名称="주식회사 시스메이트", 公司简称="sysmate")], today=TODAY)
    lead = one(conn, "sysmate")
    assert lead["company_local"] == "주식회사 시스메이트"


def test_an_email_in_the_short_name_column_is_an_email_not_a_company_name(conn):
    record = parse(公司名称="onQ Digital", 公司简称="myles@onq.digital", 联系人邮箱="")
    assert record["company_en"] == "onQ Digital"
    assert record["emails"] == ["myles@onq.digital"]


def test_three_addresses_in_a_remark_are_three_people(conn):
    sheet.apply(conn, [parse(联系人邮箱="leon@leon-hq.com",
                             联系人备注="jjh@leon-hq.com\nlhm@leon-hq.com")], today=TODAY)
    lead = one(conn, "PIXEL Innovation")
    rows = conn.execute("SELECT email, is_primary FROM contacts WHERE lead_no=? ORDER BY id",
                        (lead["no"],)).fetchall()
    assert [r["email"] for r in rows] == ["leon@leon-hq.com", "jjh@leon-hq.com", "lhm@leon-hq.com"]
    assert [r["is_primary"] for r in rows] == [1, 0, 0]


def test_what_no_field_can_hold_is_kept_as_a_note(conn):
    sheet.apply(conn, [parse(备注="大公司", 联系人备注="서울시 중구 새문안로 22", col16="已录小满")],
                today=TODAY)
    lead = one(conn, "PIXEL Innovation")
    note = conn.execute("SELECT text FROM notes WHERE lead_no=?", (lead["no"],)).fetchone()["text"]
    assert "大公司" in note and "서울시 중구 새문안로 22" in note and "已录小满" in note


# ------------------------------------------------------------- R7 one spelling, R8 rerun

def test_chinese_country_names_come_out_canonical(conn):
    sheet.apply(conn, [parse(国家地区="澳大利亚")], today=TODAY)
    assert one(conn, "PIXEL Innovation")["country"] == "Australia"


def test_importing_the_same_sheet_twice_changes_nothing_the_second_time(conn):
    records = [parse(备注="大公司")]
    sheet.apply(conn, records, today=TODAY)
    before = conn.execute("SELECT count(*) c FROM notes").fetchone()["c"]
    second = sheet.apply(conn, records, today=TODAY)
    assert second["created"] == 0 and second["notes"] == 0
    assert conn.execute("SELECT count(*) c FROM notes").fetchone()["c"] == before
    assert conn.execute("SELECT count(*) c FROM leads").fetchone()["c"] == 2
