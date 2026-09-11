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


# ----------------------------------------------------------------- R4 the sheet wins

def test_where_the_sheet_and_the_book_disagree_the_sheet_wins(conn):
    """Allen 09-11: 库里原本有的公司信息与我的表格重复的，以表格的信息为准."""
    sheet.apply(conn, [parse(公司名称="Samik Electronics", 联系人邮箱="other@samikdisplay.co.kr",
                             公司网址="http://new-samik.kr")], today=TODAY)
    lead = one(conn, "Samik Electronics")
    assert lead["email"] == "other@samikdisplay.co.kr"
    assert lead["website"] == "new-samik.kr"


def test_the_old_value_is_written_down_once(conn):
    records = [parse(公司名称="Samik Electronics", 联系人邮箱="other@samikdisplay.co.kr",
                     公司网址="http://new-samik.kr")]
    sheet.apply(conn, records, today=TODAY)
    sheet.apply(conn, records, today=TODAY)
    notes = conn.execute("SELECT text FROM notes WHERE lead_no=1 AND text LIKE '%覆盖前%'").fetchall()
    assert len(notes) == 1
    assert "swyun@samikdisplay.co.kr" in notes[0]["text"] and "samikdisplay.co.kr" in notes[0]["text"]


def test_the_book_s_primary_steps_down_but_is_not_lost(conn):
    sheet.apply(conn, [parse(公司名称="Samik Electronics", 联系人昵称="황정식 대표",
                             联系人邮箱="other@samikdisplay.co.kr")], today=TODAY)
    rows = conn.execute("SELECT name, email, is_primary FROM contacts WHERE lead_no=1"
                        " ORDER BY is_primary DESC").fetchall()
    assert [tuple(r) for r in rows] == [("황정식", "other@samikdisplay.co.kr", 1),
                                        (None, "swyun@samikdisplay.co.kr", 0)]


def test_two_spellings_of_one_number_are_not_a_disagreement(conn):
    conn.execute("UPDATE leads SET phone='+82 10-1234-5678', website='jdkat.com' WHERE no=1")
    conn.commit()
    sheet.apply(conn, [parse(公司名称="Samik Electronics", 联系人邮箱="swyun@samikdisplay.co.kr",
                             联系人电话="010-1234-5678", 公司网址="http://www.jdkat.com/?_main=1")],
                today=TODAY)
    lead = one(conn, "Samik Electronics")
    assert lead["phone"] == "+82 10-1234-5678" and lead["website"] == "jdkat.com"
    assert conn.execute("SELECT count(*) c FROM notes WHERE text LIKE '%覆盖前%'").fetchone()["c"] == 0


def test_his_labels_replace_his_labels_but_the_classifier_s_stay(conn):
    conn.execute("UPDATE leads SET tags='批发商,工程商,icp:signage' WHERE no=1")
    conn.commit()
    sheet.apply(conn, [parse(公司名称="Samik Electronics", 联系人邮箱="swyun@samikdisplay.co.kr",
                             标签="工程商")], today=TODAY)
    assert one(conn, "Samik Electronics")["tags"] == "工程商,icp:signage"


def test_blank_fields_get_filled(conn):
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


# ------------------------------------------ R9 content beats header, R10 wrong is blank

def test_a_phone_in_the_name_cell_is_still_a_phone(conn):
    """Darim: the phone sat in 联系人邮箱, the company Instagram in 联系人电话, and the
    contact's own Instagram after their name. None of it was filed the first time."""
    sheet.apply(conn, [parse(公司名称="다림시스템 주식회사", 公司简称="Darim System Co.,LTD",
                             联系人昵称="김영대 https://www.instagram.com/kim.reo/",
                             联系人邮箱="+82 10-5407-0402",
                             联系人电话="https://www.instagram.com/darim_istudio/",
                             联系人备注="https://www.facebook.com/YoungReo")], today=TODAY)
    lead = one(conn, "Darim System Co.,LTD")
    assert lead["phone"] == "+82 10-5407-0402"
    assert lead["contact_name"] == "김영대"
    assert lead["instagram"] == "darim_istudio"
    assert lead["facebook"] == "YoungReo"
    note = conn.execute("SELECT text FROM notes WHERE lead_no=?", (lead["no"],)).fetchone()["text"]
    assert "instagram.com/kim.reo" in note


def test_name_title_and_phone_written_as_one_word_come_apart(conn):
    record = parse(联系人昵称="이채원 이사님010-4482-0017")
    assert (record["contact_name"], record["title"], record["phone"]) == \
        ("이채원", "이사", "010-4482-0017")


def test_an_instagram_link_in_the_website_column_is_not_a_website(conn):
    sheet.apply(conn, [parse(公司网址="https://www.instagram.com/1st_justmedia/")], today=TODAY)
    lead = one(conn, "PIXEL Innovation")
    assert lead["instagram"] == "1st_justmedia"
    assert not lead["website"]


def test_an_email_filed_as_a_phone_counts_as_blank(conn):
    conn.execute("UPDATE leads SET phone='sales01@lumens.co.kr' WHERE no=1")
    conn.commit()
    sheet.apply(conn, [parse(公司名称="Samik Electronics", 联系人邮箱="swyun@samikdisplay.co.kr",
                             联系人电话="+82 10-1234-5678")], today=TODAY)
    assert one(conn, "Samik Electronics")["phone"] == "+82 10-1234-5678"


def test_a_different_number_in_the_sheet_replaces_it_and_the_old_one_is_kept_in_a_note(conn):
    conn.execute("UPDATE leads SET phone='+82 2-546-3288' WHERE no=1")
    conn.commit()
    sheet.apply(conn, [parse(公司名称="Samik Electronics", 联系人邮箱="swyun@samikdisplay.co.kr",
                             联系人电话="+82 10-1234-5678")], today=TODAY)
    assert one(conn, "Samik Electronics")["phone"] == "+82 10-1234-5678"
    note = conn.execute("SELECT text FROM notes WHERE text LIKE '%覆盖前%'").fetchone()["text"]
    assert "+82 2-546-3288" in note


# ------------------------------------------------- R11 every person, one note per company

def test_a_name_next_to_a_phone_in_the_remark_is_a_second_contact(conn):
    sheet.apply(conn, [parse(联系人昵称="신동명 대표/부장:+82-10-8225-8081",
                             联系人备注="장승구 실장:+82-10-8200-4641")], today=TODAY)
    lead = one(conn, "PIXEL Innovation")
    rows = conn.execute("SELECT name, title, phone, is_primary FROM contacts WHERE lead_no=?"
                        " ORDER BY id", (lead["no"],)).fetchall()
    assert [tuple(r) for r in rows] == [("신동명", "대표/부장", "+82-10-8225-8081", 1),
                                        ("장승구", "실장", "+82-10-8200-4641", 0)]


def test_an_email_next_to_a_name_belongs_to_that_person(conn):
    sheet.apply(conn, [parse(联系人昵称="남형호 대표", 联系人邮箱="ska90mcp@naver.com",
                             联系人电话="정기철 팀장jkc8972@naver.com（已回复邮件)")], today=TODAY)
    lead = one(conn, "PIXEL Innovation")
    rows = conn.execute("SELECT name, email FROM contacts WHERE lead_no=? ORDER BY id",
                        (lead["no"],)).fetchall()
    assert [tuple(r) for r in rows] == [("남형호", "ska90mcp@naver.com"),
                                        ("정기철", "jkc8972@naver.com")]


def test_a_reimport_refreshes_the_one_sheet_note_instead_of_adding_a_second(conn):
    sheet.apply(conn, [parse(备注="大公司")], today=TODAY)
    sheet.apply(conn, [parse(备注="大公司，有回邮件")], today=TODAY)
    lead = one(conn, "PIXEL Innovation")
    notes = conn.execute("SELECT text FROM notes WHERE lead_no=?", (lead["no"],)).fetchall()
    assert len(notes) == 1 and "有回邮件" in notes[0]["text"]


def test_a_name_with_an_aside_in_it_is_cleaned_when_the_sheet_names_nobody(conn):
    conn.execute("UPDATE leads SET contact_name='임정재 부장(已加微信)' WHERE no=1")
    conn.commit()
    sheet.apply(conn, [parse(公司名称="Samik Electronics", 联系人邮箱="swyun@samikdisplay.co.kr")],
                today=TODAY)
    lead = one(conn, "Samik Electronics")
    assert (lead["contact_name"], lead["title"]) == ("임정재", "부장")
    contact = conn.execute("SELECT note FROM contacts WHERE lead_no=1 AND is_primary=1").fetchone()
    assert "已加微信" in contact["note"]
