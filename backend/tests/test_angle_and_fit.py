"""The second angle, the type-aware line, and moving on instead of parking (docs/67).

The first English angle sent 361 letters for one reply. Its middle paragraph — "We
manufacture the panels behind that kind of work, indoor and outdoor, P1.86 through P10"
— is a sentence every LED factory in Shenzhen can send, and it asked the reader to open
a project file before they could answer.

What these tests hold is the machinery that makes a second attempt possible: a line
aimed at this kind of buyer, and a follow-up that switches angle rather than stopping.
"""
import pytest

from app import personalize
from app.agent import followup_decision
from app.db import connect, init_schema


@pytest.mark.parametrize("kind,marker", [
    ("租赁商", "reload every week"),
    ("工程商", "three years after the install"),
    ("广告商", "daylight"),
    ("代理商", "OEM"),
])
def test_the_line_is_aimed_at_this_kind_of_buyer(kind, marker):
    out = personalize.render("{fit}", {"company_en": "X", "tags": kind})
    assert marker in out


def test_an_unknown_type_says_nothing_rather_than_guessing():
    # A line addressed to the wrong kind of company is worse than a shorter letter.
    assert personalize.render("{fit}", {"company_en": "X", "tags": ""}) == ""
    assert personalize.render("{fit}", {"company_en": "X", "tags": "icp:rental"}) == ""


def test_the_korean_letter_gets_the_korean_line():
    out = personalize.render("{fit_ko}", {"company_en": "X", "tags": "租赁商"})
    assert "캐비닛" in out
    assert "reload" not in out


def test_an_empty_line_does_not_leave_a_hole_in_the_letter():
    # Three blank lines mid-letter reads as a template that failed to fill in.
    body = "Hi {contact},\n\n{hook}\n\n{fit}\n\nWe build panels.\n\nBest"
    out = personalize.render(body, {"company_en": "X", "contact_name": "",
                                    "hook": "Saw the work.", "tags": ""})
    assert "\n\n\n" not in out
    assert "Saw the work.\n\nWe build panels." in out


def test_a_korean_greeting_with_no_name_drops_the_honorific_too():
    """"안녕하세요, 님." is an honorific addressed to nobody, which reads worse in Korean
    than the missing name it was covering."""
    tpl = "안녕하세요, {contact}님.\n\n{hook}"
    out = personalize.render(tpl, {"company_en": "X", "contact_name": "",
                                   "hook": "H."})
    assert out.startswith("안녕하세요.")
    assert "님" not in out.splitlines()[0]


def test_a_korean_name_is_never_spoken_but_a_known_title_is():
    """docs/96 推翻了这条测试原来断言的行为（「안녕하세요, 김종수님.」）。

    Allen 09-03：韩语 B2B 冷邮件里直呼名字是失礼的，对的写法是职位加 님；职位不知道
    时就只说 안녕하세요 —— 知道名字也不叫。
    """
    tpl = "안녕하세요, {contact}님.\n\n{fit_ko}"
    base = {"company_en": "X", "contact_name": "김종수", "tags": ""}
    named = personalize.render(tpl, base).splitlines()[0]
    titled = personalize.render(tpl, {**base, "title": "대표"}).splitlines()[0]
    assert named == "안녕하세요."
    assert titled == "안녕하세요, 대표님."


@pytest.mark.parametrize("hook,expected_fragment", [
    ("Saw P1, P2 and P2.5 panels listed on your site.", "P1, P2, P2.5"),
    ("Saw the LED signage work you do around Hwaseong.", "LED 전광판"),
    ("Saw the rental and events work on your site.", "렌탈 · 행사"),
])
def test_the_korean_letter_gets_a_korean_opener(hook, expected_fragment):
    """The stored hook is English because brief.py glosses every site term into English.
    Dropping that sentence into a Korean letter reads half-finished."""
    out = personalize.render("{hook_ko}", {"company_en": "X", "hook": hook})
    assert expected_fragment in out
    assert "Saw" not in out


@pytest.mark.parametrize("hook", ["Saw the widget work on your site.", "", None])
def test_an_unfamiliar_opener_falls_back_to_the_generic_korean_line(hook):
    """半句英文混在韩语信里是不行的 —— 那条规矩没变，`hook_ko()` 仍然返回空。

    变的是空之后拿什么补：docs/100（Allen 09-04「空 hook 也不要拦，直接用通用 hook」）
    让渲染补上那句通用韩语，而不是留一个空行然后被守卫拦成 impersonal。
    """
    from app.backfill_hooks import GENERIC_HOOK_KO

    lead = {"company_en": "X", "hook": hook}
    assert personalize.hook_ko(lead) == ""          # 认不出的句式仍然不硬译
    out = personalize.render("{hook_ko}", lead)
    assert out == GENERIC_HOOK_KO
    assert "Saw" not in out


def test_a_dash_with_nothing_after_it_goes_too():
    # "We build LED panels in Shenzhen — {fit}." with no type rendered "... Shenzhen —."
    out = personalize.render("We build panels — {fit}.", {"company_en": "X", "tags": ""})
    assert out == "We build panels."


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, email) VALUES
            (1, 'Verum AV', 'USA', 'a@verumav.com');
        INSERT INTO sequences(id, name, channel) VALUES
            (1, '冷邮件 3 步跟进（英语）', 'email'),
            (2, '冷邮件 3 步跟进（英语·角度二）', 'email'),
            (3, '冷邮件 3 步跟进（韩语）', 'email');
        INSERT INTO sequence_enrollments(id, lead_no, sequence_id, current_step, status,
                                         enrolled_at, next_due_date)
        VALUES (10, 1, 1, 2, 'active', '2026-07-01', '2026-08-01');
    """)
    c.commit()
    return c


def test_a_delay_moves_the_due_date_and_nothing_else(conn):
    """What replaced angle switching: the only thing that holds a letter back for timing
    is the two-week cooldown, and it reschedules rather than parking (docs/75 R1)."""
    followup_decision.apply(conn, {"enrollment_id": 10, "action": "delay",
                                   "next_due_date": "2026-09-15"})
    row = conn.execute(
        "SELECT sequence_id, status, current_step, next_due_date"
        " FROM sequence_enrollments WHERE id=10").fetchone()
    assert row["status"] == "active"
    assert row["next_due_date"] == "2026-09-15"
    assert (row["sequence_id"], row["current_step"]) == (1, 2)   # stays where it was


def test_nothing_parks_any_more(conn):
    """`quality_hold` was the state for "ran out of angles". There are no angles."""
    followup_decision.apply(conn, {"enrollment_id": 10, "action": "delay",
                                   "next_due_date": "2026-09-15"})
    assert conn.execute(
        "SELECT COUNT(*) FROM sequence_enrollments WHERE status='quality_hold'"
    ).fetchone()[0] == 0
