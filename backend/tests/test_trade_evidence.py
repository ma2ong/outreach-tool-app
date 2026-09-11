"""库里没有一个字说他们买屏（docs/112）。

真实两条：EKM Exports 是南非农产品出口商，被发了邮件和 FB 私信；
Amos Productions 官网自己写着 LED video walls —— 后者不该进这张名单。
"""
import pytest

from app import health, icp
from app.db import connect, init_schema


EKM = {"company_en": "Ekm Exports", "website": "ekm-exports.com",
       "hook": "You export roughly 3 million cartons of produce annually.",
       "business": "小满邮件往来 2 封（1 位联系人），最后一次：Re: Sending of ci and specifications sheet",
       "brief": "", "tags": "", "target_fit": ""}

AMOS = {"company_en": "Amos Productions", "website": "amospro.com",
        "hook": "Saw the staging and event production work you do around Livermore.",
        "business": "Full-service AV production; LED video walls, live sound, lighting, DJ",
        "brief": 'The site mentions "staging", "event production" and "concert".',
        "tags": "租赁商,icp:rental", "target_fit": "租赁公司 (96)"}


def test_the_produce_exporter_has_nothing_on_file_about_this_trade():
    assert icp.has_trade_evidence(EKM) is False


def test_a_company_whose_own_site_says_led_video_walls_is_not_on_this_list():
    """docs/112 R5：判 Amos 不是买家靠的是社媒在发什么，文字层面他就是这行的。"""
    assert icp.has_trade_evidence(AMOS) is True


def test_the_buyer_category_is_itself_evidence():
    """判成「租赁公司 (90)」的公司，类别标签里就写着这一行。"""
    assert icp.has_trade_evidence({"company_en": "X", "target_fit": "租赁公司 (90)"}) is True
    assert icp.has_trade_evidence({"company_en": "X", "target_fit": "未知 (0)"}) is False


@pytest.mark.parametrize("text", [
    "LED display manufacturer", "pantallas LED para eventos", "painéis de LED",
    "전광판 시공", "digital signage and billboards", "AV rental and staging",
    "显示屏工程", "video wall integration",
])
def test_the_words_this_trade_is_written_in(text):
    assert icp.has_trade_evidence({"business": text}) is True


@pytest.mark.parametrize("text", [
    "Fresh produce exporter", "Av. Paulista 1000, São Paulo",
    "Accounting and tax services", "Sign up for our newsletter",
])
def test_words_that_do_not_mean_this_trade(text):
    assert icp.has_trade_evidence({"business": text}) is False


def test_an_unknown_verdict_is_written_down_now(tmp_path):
    """docs/112 R1：「看不出」和「没看过」不能长得一样。"""
    conn = connect(str(tmp_path / "t.db"))
    init_schema(conn)
    conn.execute("INSERT INTO leads(no, company_en) VALUES (1,'Ekm Exports')")
    conn.commit()
    icp.apply_to_lead(conn, 1, {"icp_type": "unknown", "fit_score": 0, "hits": []})
    row = conn.execute("SELECT target_fit, tags FROM leads WHERE no=1").fetchone()
    assert row["target_fit"] == "未知 (0)"
    assert "icp:unknown" in row["tags"]


def test_a_later_real_verdict_replaces_the_unknown_one(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    init_schema(conn)
    conn.execute("INSERT INTO leads(no, company_en) VALUES (1,'X')")
    conn.commit()
    icp.apply_to_lead(conn, 1, {"icp_type": "unknown", "fit_score": 0, "hits": []})
    icp.apply_to_lead(conn, 1, {"icp_type": "rental", "fit_score": 90, "hits": ["rental"]})
    row = conn.execute("SELECT target_fit, tags FROM leads WHERE no=1").fetchone()
    assert row["target_fit"] == "租赁公司 (90)"
    assert "icp:unknown" not in row["tags"]


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "h.db"))
    init_schema(c)
    c.execute("INSERT INTO leads(no, company_en, country, website, email, hook, business,"
              " brief, tags, target_fit) VALUES (1,?,?,?,?,?,?,?,?,?)",
              ("Ekm Exports", "South Africa", "ekm-exports.com", "info@ekm-exports.com",
               EKM["hook"], EKM["business"], "", "", ""))
    c.execute("INSERT INTO leads(no, company_en, country, website, email, hook, business,"
              " brief, tags, target_fit) VALUES (2,?,?,?,?,?,?,?,?,?)",
              ("Amos Productions", "USA", "amospro.com", "info@amospro.com",
               AMOS["hook"], AMOS["business"], AMOS["brief"], AMOS["tags"], AMOS["target_fit"]))
    c.commit()
    return c


def test_the_health_check_lists_it_with_the_sentence_we_have(conn):
    found = health.scan(conn)
    off = found.get("off_trade") or []
    assert [l["no"] for l in off] == [1]
    assert "produce" in off[0]["reason"]


def test_the_health_fix_stops_writing_to_them_without_deleting_them(conn):
    """docs/112 R4：这类记录常有真实往来历史，不再联系可撤销，删除不可撤销。"""
    health.fix(conn, ["off_trade"])
    row = conn.execute("SELECT do_not_contact FROM leads WHERE no=1").fetchone()
    assert row["do_not_contact"] == 1
    assert conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0] == 2
    assert conn.execute(
        "SELECT COUNT(*) FROM notes WHERE lead_no=1").fetchone()[0] == 1


def test_the_daily_social_queue_skips_them(conn):
    """docs/112 R3：不确定是停下来问的理由，不是猜的理由。"""
    from app import social_queue

    conn.execute("UPDATE leads SET facebook='EKMexports' WHERE no=1")
    conn.execute("UPDATE leads SET facebook='amosproductions' WHERE no=2")
    conn.commit()
    social_queue.ensure_schema(conn)
    nos = [c["no"] for c in social_queue._candidates(conn, None)]
    assert 1 not in nos and 2 in nos


def test_a_reseller_is_not_an_outsider_just_because_its_brief_says_wholesale():
    """Thinksign / Look DS：简介只写着 wholesale、reseller，差点被判成外行。

    分级已经把它们归进「经销商」——那是读了整个官网得出的结论。而 `wholesale`
    本身不能进词表：EKM 就是个农产品批发出口商。
    """
    reseller = {"company_en": "Thinksign", "target_fit": "经销商 (80)",
                "brief": 'The site mentions "wholesale" and "reseller" (resale).',
                "hook": "Saw the resale work on your site.", "business": ""}
    assert icp.is_off_trade(reseller) is False
    assert icp.is_off_trade({**reseller, "target_fit": "未知 (0)"}) is True


def test_too_little_text_is_not_a_verdict():
    """docs/112 R2：刚采集进来还没读过官网的公司，是「还没看过」，不是「看不出」。"""
    assert icp.is_off_trade({"company_en": "Alpha", "website": "alpha.com"}) is False
    assert icp.is_off_trade({"company_en": "Alpha", "business": "Fresh produce"}) is False
