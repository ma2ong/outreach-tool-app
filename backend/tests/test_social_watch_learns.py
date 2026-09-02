"""看了二十三次，看的是同两家（docs/91）。

不联网：`watch` 收一个 engine，测试传一个假的进去。
"""
import datetime as dt

import pytest

from app import social_watch


@pytest.fixture
def watchable(conn):
    """三家挂着 instagram 的公司 —— 够看出轮换有没有发生。"""
    conn.execute("UPDATE leads SET instagram='alphaig' WHERE no=1")
    conn.execute("UPDATE leads SET instagram='betaig' WHERE no=2")
    conn.execute("UPDATE leads SET instagram='gammaig' WHERE no=3")
    conn.commit()
    social_watch.ensure_schema(conn)
    return conn


class _Engine:
    """读到什么由测试给。follow 一律不做。"""

    def __init__(self, text=""):
        self.text = text
        self.read = []

    def read_profile(self, channel, handle):
        self.read.append(handle)
        return {"url": f"https://x/{handle}", "text": self.text}

    def follow(self, channel, handle):
        return {"already": True}


def _events(conn, lead_no=None):
    sql = "SELECT lead_no, summary FROM relationship_events WHERE source='discovery'"
    return [(r["lead_no"], r["summary"]) for r in conn.execute(sql)]


def test_a_second_round_does_not_re_read_the_first_round(watchable):
    """验收 1：628 家在排队时，不该每天重看第 1、2 家。"""
    conn = watchable
    engine = _Engine("Just wrapped the arena show. 2026年8月20日")

    social_watch.watch(conn, engine, limit=2, sleeper=lambda _s: None)
    first = set(engine.read)
    engine.read.clear()
    social_watch.watch(conn, engine, limit=1, sleeper=lambda _s: None)

    assert first and engine.read, "两轮都要真的看了东西"
    assert not (first & set(engine.read)), f"第二轮又看了 {first & set(engine.read)}"


def test_a_visit_is_recorded_without_touching_the_lead_row(watchable):
    """验收 2：看过是看过，改过是改过 —— 别让 recheck / dedupe 以为记录刚更新过。"""
    conn = watchable
    before = conn.execute("SELECT updated_at FROM leads WHERE no=1").fetchone()["updated_at"]

    social_watch.watch(conn, _Engine("Arena show last week. 2026年8月20日"),
                       limit=1, sleeper=lambda _s: None)

    visits = conn.execute("SELECT lead_no, channel, handle FROM social_visits").fetchall()
    assert len(visits) == 1
    assert conn.execute(
        "SELECT updated_at FROM leads WHERE no=1").fetchone()["updated_at"] == before


def test_a_six_year_old_post_is_not_recent_activity(watchable):
    """验收 3：2019 年的帖子说明这条线索凉了，不是「他们在做活动」。"""
    conn = watchable
    stale = "NN LED · 觉得幸福 2019年11月29日 · EVENTO DE HOJE event"

    social_watch.watch(conn, _Engine(stale), limit=1, sleeper=lambda _s: None)

    summaries = [s for _, s in _events(conn)]
    assert not any("社媒动态" in s for s in summaries), summaries
    assert any("久未更新" in s for s in summaries), summaries


def test_the_event_quotes_a_sentence_not_a_category(watchable):
    """验收 4：「活动」两个字喂不出开场白，一句可引用的话可以。"""
    conn = watchable
    text = ("服务条款 · 广告 · Ad Choices · Cookie · 更多 帖子 "
            "2026年8月20日 · We supplied the LED wall for the arena show in Lisbon. "
            "查看更多评论 以 Allen Ma 的身份评论")

    social_watch.watch(conn, _Engine(text), limit=1, sleeper=lambda _s: None)

    summaries = [s for _, s in _events(conn) if "社媒动态" in s]
    assert summaries, "该产生一条社媒动态"
    quote = summaries[0]
    assert "arena show" in quote or "LED wall" in quote
    for chrome in ("服务条款", "Ad Choices", "Cookie", "查看更多评论", "以 Allen Ma"):
        assert chrome not in quote, f"平台导航混进了引文：{chrome}"


def test_the_same_visit_twice_does_not_write_the_event_twice(watchable):
    """验收 6：15 条一模一样的记录是噪音，不是十五次观察。"""
    conn = watchable
    text = "2026年8月20日 · We supplied the LED wall for the arena show."

    social_watch.watch(conn, _Engine(text), limit=1, sleeper=lambda _s: None)
    conn.execute("DELETE FROM social_visits")          # 强制它再看一次同一家
    conn.commit()
    social_watch.watch(conn, _Engine(text), limit=1, sleeper=lambda _s: None)

    assert len([s for _, s in _events(conn) if "社媒动态" in s]) == 1


def test_a_generic_opener_is_replaced_from_what_the_profile_said(watchable):
    """验收 5 上半：103 家还在用那句对谁都一样的开场白，社媒能给出更具体的。"""
    from app.backfill_hooks import GENERIC_HOOK
    from app.personalize import _HOOK_WORK_RE

    conn = watchable
    conn.execute("UPDATE leads SET hook=?, city='Lisbon' WHERE no=1", (GENERIC_HOOK,))
    conn.commit()

    social_watch.watch(conn, _Engine("2026年8月20日 · LED wall for the arena event."),
                       limit=1, sleeper=lambda _s: None)

    hook = conn.execute("SELECT hook FROM leads WHERE no=1").fetchone()["hook"]
    assert hook != GENERIC_HOOK
    # 句式必须还落在 docs/85 认得的形状上，否则韩语开场白整句消失。
    assert _HOOK_WORK_RE.match(hook), hook


def test_an_opener_built_from_their_own_site_is_not_downgraded(watchable):
    """验收 5 下半：拿一个类别词换掉官网建出来的开场白是降级，不做。"""
    conn = watchable
    theirs = "Saw the digital signage work you do around Kitchener."
    conn.execute("UPDATE leads SET hook=?, city='Kitchener' WHERE no=1", (theirs,))
    conn.commit()

    social_watch.watch(conn, _Engine("2026年8月20日 · LED wall for the arena event."),
                       limit=1, sleeper=lambda _s: None)

    assert conn.execute("SELECT hook FROM leads WHERE no=1").fetchone()["hook"] == theirs
