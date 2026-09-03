"""一个没人在官网上见过的邮箱（docs/89）。

不联网：`recover` 收一个 fetch 函数，测试传假页面进去。

这里最重要的一条是 `test_research_never_holds_a_letter_back`：研究归研究，
它不许让任何一封信少发。
"""
import pytest

from app import email_provenance, outreach, sequences


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


def test_a_site_with_no_address_writes_nothing_at_all(conn, unsourced):
    """验收 3：读不到有效信息就什么都不写 —— 不写出处，也不造一条没人会做的任务。"""
    out = email_provenance.recover(conn, unsourced, fetch=_page("About our company"))

    assert out["outcome"] == "unknown"
    assert not (conn.execute("SELECT email_source FROM leads WHERE no=1")
                .fetchone()["email_source"] or "")
    from app import activities
    assert activities.list_all(conn) == []


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
    """不知道邮箱对不对，不等于这家公司不要联系。"""
    email_provenance.recover(conn, unsourced, fetch=_page("About our company"))

    assert conn.execute(
        "SELECT COALESCE(do_not_contact,0) d FROM leads WHERE no=1").fetchone()["d"] == 0


def test_research_never_holds_a_letter_back(conn):
    """这一条比上面所有的都重要（Allen 09-03）。

    一家说不出邮箱出处的公司，照常进队列、照常发。研究是并排跑的另一件事，
    它的产出是把地址补对，不是把信扣下来。
    """
    conn.execute("UPDATE leads SET email='guess@alpha.com', email_source=NULL WHERE no=1")
    conn.execute("UPDATE leads SET email='seen@beta.com',"
                 " email_source='site.contact-page' WHERE no=2")
    steps = [{"day_offset": 0, "subject": "hi", "body": "Hi {contact},\n\nhello\n"}]
    seq = sequences.create_sequence(conn, "冷邮件", "email", steps)
    sequences.enroll_leads(conn, seq, [1, 2])
    conn.commit()

    assert sequences.block_unsendable(conn) == 0, "没有出处不是停发的理由"
    assert {d["lead_no"] for d in sequences.due_queue(conn, "email")} == {1, 2}


def test_the_top_up_pool_still_offers_a_company_with_no_provenance(conn):
    """补位池同理：出处不明照样可以是今天要写的第一封信。"""
    conn.execute("UPDATE leads SET email='guess@gamma.com', email_source=NULL WHERE no=3")
    conn.commit()

    assert 3 in outreach.never_touched(conn, "email")


def test_finding_a_better_address_lowers_bounces_without_lowering_volume(conn):
    """研究该有的样子：换掉一个猜出来的地址，信照发，只是发对了地方。"""
    # lead 1 在 fixture 里已经写过信了，用还没写过的那家才测得到「仍然可发」。
    conn.execute("UPDATE leads SET email='guess@gamma.com', website='gamma.com',"
                 " email_source=NULL WHERE no=3")
    conn.commit()

    out = email_provenance.recover(conn, 3, fetch=_page("Sales: sales@gamma.com"))

    assert out["outcome"] == "replaced"
    row = conn.execute("SELECT email, email_source FROM leads WHERE no=3").fetchone()
    assert row["email"] == "sales@gamma.com" and row["email_source"].startswith("site.")
    # 这家公司仍然是可发的 —— 研究没有让它掉出任何池子。
    assert 3 in outreach.never_touched(conn, "email")
