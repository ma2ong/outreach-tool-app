"""一个没人在官网上见过的邮箱（docs/89）。

不联网：`recover` 收一个 fetch 函数，测试传假页面进去。
"""
import pytest

from app import activities, email_provenance, outreach, sequences


def _page(text: str):
    return lambda url: text


@pytest.fixture
def unsourced(conn):
    """一家有官网、有邮箱、但说不出这个邮箱从哪来的公司。"""
    conn.execute("UPDATE leads SET email='guess@alpha.com', website='alpha.com',"
                 " email_source=NULL, email_status='valid' WHERE no=1")
    conn.commit()
    return 1


def test_the_address_on_their_contact_page_gains_its_source(conn, unsourced):
    """验收 1：官网上印着这个地址 —— 补上出处，照常发。"""
    out = email_provenance.recover(
        conn, unsourced, fetch=_page("Contact us: guess@alpha.com"))

    assert out["outcome"] == "confirmed"
    row = conn.execute("SELECT email, email_source FROM leads WHERE no=1").fetchone()
    assert row["email"] == "guess@alpha.com"
    assert row["email_source"].startswith("site.")


def test_the_address_printed_on_the_site_beats_the_guessed_one(conn, unsourced):
    """验收 2：官网上写的是别的地址 —— 印出来的那个赢。"""
    out = email_provenance.recover(
        conn, unsourced, fetch=_page("Sales: sales@alpha.com"))

    assert out["outcome"] == "replaced"
    row = conn.execute("SELECT email, email_source FROM leads WHERE no=1").fetchone()
    assert row["email"] == "sales@alpha.com"
    assert row["email_source"].startswith("site.")


def test_a_site_with_no_address_leaves_the_source_empty_and_raises_a_task(conn, unsourced):
    """验收 3：官网上一个邮箱都没有 —— 出处仍是空，转成一条去找联系方式的任务。"""
    out = email_provenance.recover(conn, unsourced, fetch=_page("About our company"))

    assert out["outcome"] == "unknown"
    assert not (conn.execute("SELECT email_source FROM leads WHERE no=1")
                .fetchone()["email_source"] or "")
    titles = [a["title"] for a in activities.list_all(conn)]
    assert any("联系方式" in t for t in titles)


def test_a_company_with_no_website_is_not_fetched(conn):
    """验收 4：没有官网就没得抓，也不该去试。"""
    conn.execute("UPDATE leads SET email='x@beta.com', website=NULL,"
                 " email_source=NULL WHERE no=2")
    conn.commit()

    def explode(url):                      # 一旦被调用就说明规则错了
        raise AssertionError("没有官网时不应该发起抓取")

    out = email_provenance.recover(conn, 2, fetch=explode)
    assert out["outcome"] == "no_website"


def test_an_empty_source_never_means_do_not_contact(conn, unsourced):
    """验收 5：不知道邮箱对不对，不等于这家公司不要联系。"""
    email_provenance.recover(conn, unsourced, fetch=_page("About our company"))

    assert conn.execute(
        "SELECT COALESCE(do_not_contact,0) d FROM leads WHERE no=1").fetchone()["d"] == 0


def test_a_first_letter_without_a_source_does_not_reach_the_queue(conn):
    """R2：出处是空的，第一封信不发 —— 拦在所有发送路径共用的那个队列上。"""
    conn.execute("UPDATE leads SET email='guess@alpha.com', email_source=NULL WHERE no=1")
    conn.execute("UPDATE leads SET email='seen@beta.com',"
                 " email_source='site.contact-page' WHERE no=2")
    steps = []
    steps.append({"day_offset": 0, "subject": "hi", "body": "Hi {contact},\n\nhello\n"})
    seq = sequences.create_sequence(conn, "冷邮件", "email", steps)
    sequences.enroll_leads(conn, seq, [1, 2])
    conn.commit()

    # 出处闸和「这个渠道上没有地址」走同一个机制：报名被停在 blocked，
    # 状态是看得见的，而不是队列莫名其妙变短。
    assert sequences.block_unsendable(conn) == 1
    queued = {d["lead_no"] for d in sequences.due_queue(conn, "email")}
    assert queued == {2}

    # 补回出处之后，同一条报名要能自己回来 —— 否则补救就成了单向门。
    conn.execute("UPDATE leads SET email_source='site.contact-page' WHERE no=1")
    conn.commit()
    assert sequences.reopen_sendable(conn) == 1
    assert {d["lead_no"] for d in sequences.due_queue(conn, "email")} == {1, 2}


def test_a_company_already_written_to_keeps_its_follow_ups(conn):
    """R2 的边界：已经发过信的不受影响 —— 那个地址已经投递成功过。"""
    conn.execute("UPDATE leads SET email='guess@alpha.com', email_source=NULL WHERE no=1")
    conn.execute("INSERT INTO send_log(lead_no, channel, campaign, sent_at)"
                 " VALUES (1,'email','冷邮件','2026-08-01T00:00:00')")
    steps = []
    steps.append({"day_offset": 0, "subject": "hi", "body": "Hi {contact},\n\nhello\n"})
    steps.append({"day_offset": 14, "subject": "re", "body": "Hi {contact},\n\nagain\n"})
    seq = sequences.create_sequence(conn, "冷邮件", "email", steps)
    sequences.enroll_leads(conn, seq, [1])
    conn.commit()

    assert {d["lead_no"] for d in sequences.due_queue(conn, "email")} == {1}


def test_the_top_up_pool_does_not_offer_unsourced_companies(conn):
    """补位池也要守同一条规则，否则报名了却永远发不出去。"""
    conn.execute("UPDATE leads SET email='guess@gamma.com', email_source=NULL WHERE no=3")
    conn.commit()

    assert 3 not in outreach.never_touched(conn, "email")
