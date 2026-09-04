"""一家公司只有一个可信名字时才叫出口，其余一律 Hi,（docs/98）。

`decision_maker_radar` 扫了 545 次、产出 270 个候选人，246 个停在 `new` 一次没用过 ——
被 `promote_candidate` 里「自动晋级需要邮箱或 LinkedIn」那一行挡住。那条规则守的是
「这个人会不会收到我们的信」，是对的；但叫一个人的名字不需要有他的联系方式，而这 88 家
公司的信照样每天在发往 info@，开头是一句 "Hi,"。

守四件事：韩国不碰、不确定就不叫、脏名字进不来、Allen 改过的不被改回去。
"""
import pytest

from app import contact_names, decision_maker_radar
from app.db import connect, init_schema


@pytest.fixture
def conn():
    c = connect(":memory:")
    init_schema(c)
    decision_maker_radar.ensure_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, website, email) VALUES
            (1, 'UTG Digital Media',  'Canada',      'https://utgdm.com',    'info@utgdm.com'),
            (2, 'Data Projections',   'USA',         'https://dataproj.com', 'info@dataproj.com'),
            (3, 'Kinoton Korea',      'South Korea', 'https://kinoton.kr',   'info@kinoton.kr'),
            (4, 'Alpha Signs Inc',    'USA',         'https://alpha.com',    'info@alpha.com'),
            (5, 'Beta Rental',        'Brazil',      'https://beta.com',     'info@beta.com');
    """)
    c.commit()
    return c


def _candidate(conn, lead_no: int, name: str, title: str = "CEO",
               url: str | None = None, confidence: int = 81) -> None:
    conn.execute(
        "INSERT INTO contact_candidates(lead_no, name, title, role_kind, source_url,"
        " evidence, confidence, status, fingerprint, created_at, updated_at)"
        " VALUES (?,?,?,'commercial',?,'seen on the about page',?,'new',?,?,?)",
        (lead_no, name, title, url or f"https://{['x','utgdm','dataproj','kinoton','alpha','beta'][lead_no]}.com/about",
         confidence, f"{lead_no}:{name}", "2026-09-04", "2026-09-04"))
    conn.commit()


def _yes(conn, items):
    """判官说「都是人名」—— 让确定性过滤和「只有一个才用」那两条单独受测。"""
    return {i["name"] for i in items}


def _greeting_name(conn, lead_no: int) -> str:
    row = conn.execute("SELECT contact_name FROM leads WHERE no=?", (lead_no,)).fetchone()
    return (row["contact_name"] or "").strip()


# ---------------------------------------------------------------- R2 确定才叫

def test_one_credible_candidate_becomes_the_greeting(conn):
    _candidate(conn, 1, "Alan Wehbe", "Founder")
    contact_names.fill(conn, judge=_yes)
    assert _greeting_name(conn, 1) == "Alan Wehbe"


def test_several_candidates_mean_we_do_not_know_which_one(conn):
    """Data Projections 有六个真人名字。不知道该叫哪一个，就是不确定（docs/98 R2）。"""
    for name in ("Jim Scalise", "Kris Begnaud", "Megan Stasio", "Travis Corgey"):
        _candidate(conn, 2, name, "President")
    contact_names.fill(conn, judge=_yes)
    assert _greeting_name(conn, 2) == ""


def test_confidence_is_not_used_to_break_the_tie(conn):
    """九个候选的可信度全是 81。拿它排序只是把抛硬币写成算法。"""
    _candidate(conn, 2, "Jim Scalise", "President", confidence=88)
    _candidate(conn, 2, "Kris Begnaud", "President", confidence=81)
    contact_names.fill(conn, judge=_yes)
    assert _greeting_name(conn, 2) == ""


# ---------------------------------------------------------------- R3 脏名字

def test_the_company_calling_itself_by_name_is_not_a_person(conn):
    _candidate(conn, 2, "Data Projections", "President")
    contact_names.fill(conn, judge=_yes)
    assert _greeting_name(conn, 2) == ""


@pytest.mark.parametrize("suffix", ["Inc", "Inc.", "LLC", "Ltd", "GmbH"])
def test_the_company_name_without_its_suffix_is_not_a_person_either(conn, suffix):
    _candidate(conn, 4, "Alpha Signs", "CEO")
    contact_names.fill(conn, judge=_yes)
    assert _greeting_name(conn, 4) == ""


@pytest.mark.parametrize("junk", ["Read More", "Learn More", "Our Team",
                                  "Contact Us", "View Profile", "Read Bio"])
def test_web_furniture_is_not_a_person(conn, junk):
    """这些全都通过了 docs/95 R3 那道闸 —— 它挡职位词，不挡网页控件。"""
    _candidate(conn, 1, junk, "President")
    contact_names.fill(conn, judge=_yes)
    assert _greeting_name(conn, 1) == ""


def test_a_title_word_is_still_blocked_by_the_existing_gate(conn):
    """95 号 R3 那道闸原样复用，不在这里重写一遍。"""
    _candidate(conn, 1, "Operations Manager", "CEO")
    contact_names.fill(conn, judge=_yes)
    assert _greeting_name(conn, 1) == ""


def test_one_dirty_candidate_does_not_make_a_clean_one_ambiguous(conn):
    """先滤掉不算数的，再数还剩几个（docs/98 R3 的顺序）。"""
    _candidate(conn, 1, "Read More", "President")
    _candidate(conn, 1, "Alan Wehbe", "Founder")
    contact_names.fill(conn, judge=_yes)
    assert _greeting_name(conn, 1) == "Alan Wehbe"


# ---------------------------------------------------------------- R4 证据来源

def test_a_name_from_somewhere_that_is_not_their_own_site_is_not_used(conn):
    _candidate(conn, 5, "Paulo Souza", "CEO", url="https://some-directory.com/beta")
    contact_names.fill(conn, judge=_yes)
    assert _greeting_name(conn, 5) == ""


# ---------------------------------------------------------------- R1 韩国

def test_korea_is_left_entirely_alone(conn):
    """称呼那一列此刻有另一份工作在写，两边不能同时动（Allen 09-04）。"""
    _candidate(conn, 3, "Park Ji-sung", "대표")
    contact_names.fill(conn, judge=_yes)
    assert _greeting_name(conn, 3) == ""


# ---------------------------------------------------------------- R5 不覆盖他

def test_a_company_that_already_has_a_greeting_is_not_touched(conn):
    conn.execute("UPDATE leads SET contact_name='Carlos' WHERE no=1")
    conn.commit()
    _candidate(conn, 1, "Alan Wehbe", "Founder")
    contact_names.fill(conn, judge=_yes)
    assert _greeting_name(conn, 1) == "Carlos"


def test_clearing_a_name_allen_did_not_want_makes_it_stay_cleared(conn):
    """会把用户的修改改回去的自动化，比从不动手的自动化更糟（docs/98 R5）。"""
    _candidate(conn, 1, "Alan Wehbe", "Founder")
    contact_names.fill(conn, judge=_yes)
    assert _greeting_name(conn, 1) == "Alan Wehbe"

    conn.execute("UPDATE leads SET contact_name='' WHERE no=1")
    conn.commit()
    contact_names.fill(conn, judge=_yes)
    assert _greeting_name(conn, 1) == "", "他删掉的名字不该被填回来"


def test_the_contact_row_carries_no_address_so_it_is_never_cc_d(conn):
    """docs/95 R1 的抄送只认有邮箱的联系人。名字不是渠道。"""
    _candidate(conn, 1, "Alan Wehbe", "Founder")
    contact_names.fill(conn, judge=_yes)
    row = conn.execute(
        "SELECT email, source FROM contacts WHERE lead_no=1").fetchone()
    assert row is not None
    assert (row["email"] or "") == ""
    assert row["source"] == "agent.public-site"


def test_running_twice_changes_nothing_the_second_time(conn):
    _candidate(conn, 1, "Alan Wehbe", "Founder")
    first = contact_names.fill(conn, judge=_yes)
    second = contact_names.fill(conn, judge=_yes)
    assert first["named"] == 1
    assert second["named"] == 0
    assert conn.execute("SELECT COUNT(*) FROM contacts WHERE lead_no=1").fetchone()[0] == 1


# ---------------------------------------------------------------- 报告

def test_it_says_how_many_stayed_anonymous_and_why(conn):
    """39 家有名字、36 家继续 Hi, —— 后者不是失败，但也不该是看不见的。"""
    _candidate(conn, 1, "Alan Wehbe", "Founder")
    _candidate(conn, 2, "Jim Scalise", "President")
    _candidate(conn, 2, "Kris Begnaud", "President")
    _candidate(conn, 3, "Park Ji-sung", "대표")
    result = contact_names.fill(conn, judge=_yes)
    assert result["named"] == 1
    assert result["ambiguous"] == 1
    assert result["korea_skipped"] == 1


# ---------------------------------------------------------------- R7 模型判官

def test_without_a_model_nobody_gets_named(conn):
    """「不确定的情况下直接 Hi」—— 模型不可用就是最彻底的不确定（docs/98 R7）。"""
    _candidate(conn, 1, "Alan Wehbe", "Founder")
    result = contact_names.fill(conn, judge=lambda c, items: set())
    assert _greeting_name(conn, 1) == ""
    assert result["rejected"] == 1


def test_a_name_the_model_made_up_is_thrown_away(conn):
    """模型只判断，不写。它给出的、我们没发给它的字符串，是没人在客户页面上读到过的字。"""
    _candidate(conn, 1, "Alan Wehbe", "Founder")
    contact_names.fill(conn, judge=lambda c, items: {"Alan W. Wehbe Jr"})
    assert _greeting_name(conn, 1) == ""


def test_the_model_never_gets_to_rewrite_the_name(conn):
    """"Meet Josh" 判成人名也只会原样用，不会被修剪成 "Josh" —— 修剪是编造的近亲。"""
    _candidate(conn, 1, "Meet Josh", "owner")
    contact_names.fill(conn, judge=lambda c, items: {"Meet Josh"})
    assert _greeting_name(conn, 1) == "Meet Josh"


def test_the_model_is_asked_once_for_the_whole_batch(conn):
    calls = []

    def counting(c, items):
        calls.append(len(items))
        return {i["name"] for i in items}

    _candidate(conn, 1, "Alan Wehbe", "Founder")
    _candidate(conn, 4, "Maria Santos", "CEO")
    contact_names.fill(conn, judge=counting)
    assert calls == [2], "一天一批一次调用，不是一个名字一次"


# ---------------------------------------------------------------- R1 韩文

def test_a_korean_company_with_no_country_is_still_korean(conn):
    """库里有三家这样的：country 为空，名字是 이승근、职位是 대표。
    Allen 的规则说的是韩国公司，不是「国家这一列填了没有」。"""
    conn.execute("UPDATE leads SET country=NULL WHERE no=5")
    conn.commit()
    _candidate(conn, 5, "이승근", "대표")
    result = contact_names.fill(conn, judge=_yes)
    assert _greeting_name(conn, 5) == ""
    assert result["korea_skipped"] == 1
