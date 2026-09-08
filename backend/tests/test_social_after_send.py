"""发完私信就站在他主页上，别空手离开（docs/110）。

不联网：engine 是假的，页面文字由测试给。
"""
import datetime as dt

import pytest

from app import social_watch
from app.db import connect, init_schema


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, instagram) VALUES
            (1, 'Hinckley Productions', 'USA', 'hinckleyproductions');
    """)
    c.commit()
    social_watch.ensure_schema(c)
    from app import sales_intelligence
    sales_intelligence.ensure_schema(c)  # 空雷达也要能查得出 0 条
    return c


def _recent(days_ago: int = 20) -> str:
    d = dt.date.today() - dt.timedelta(days=days_ago)
    return f"{d.year}年{d.month}月{d.day}日"


PROFILE = ("Hinckley Productions. Live event production and streaming. "
           f"{_recent()} Just wrapped the arena installation for the summer festival. "
           "info@hinckleyproductions.com +1 608 555 0134 hinckleyproductions.com")


class _Engine:
    def __init__(self, text=PROFILE, follow_result=None, read_fails=False, follow_fails=False):
        self.text = text
        self.read = []
        self.followed = []
        self.read_fails = read_fails
        self.follow_fails = follow_fails
        self.follow_result = follow_result or {"already": False}

    def read_profile(self, channel, handle):
        if self.read_fails:
            raise RuntimeError("需要登录才能看")
        self.read.append(handle)
        return {"handle": handle, "channel": channel,
                "url": f"https://www.instagram.com/{handle}/", "text": self.text}

    def follow(self, channel, handle):
        if self.follow_fails:
            raise RuntimeError("action blocked")
        self.followed.append(handle)
        return self.follow_result


def test_after_a_dm_it_follows_reads_and_records(conn):
    engine = _Engine()
    out = social_watch.after_send(conn, engine, 1, "instagram", "hinckleyproductions")

    assert engine.followed == ["hinckleyproductions"]
    assert out["followed"] == "已关注"
    # 主页上的联系方式补进空字段
    lead = conn.execute("SELECT email, phone, website FROM leads WHERE no=1").fetchone()
    assert lead["email"] == "info@hinckleyproductions.com"
    assert lead["phone"]
    # 近况进销售雷达，按帖子日期排（docs/110 R5）
    signal = conn.execute("SELECT * FROM buying_signals WHERE lead_no=1").fetchone()
    assert signal["signal_type"] == "social"
    assert "arena installation" in signal["evidence"]
    assert signal["source_url"].startswith("https://www.instagram.com/")
    assert signal["occurred_at"] == (dt.date.today() - dt.timedelta(days=20)).isoformat()
    # 访问记下来了，浏览额度没被花掉（docs/110 R3）
    assert conn.execute("SELECT COUNT(*) FROM social_visits WHERE lead_no=1").fetchone()[0] == 1
    assert social_watch.remaining(conn) == social_watch.DAILY_LIMIT


def test_our_own_message_is_not_their_news(conn):
    """docs/110 R4：聊天浮层还在页面上，我们自己的信不许被当成客户动态或联系方式。"""
    sent = ("Hi, we build LED display walls for event production companies. "
            "Happy to send specs — allen@mcvisual.com +86 138 0000 0000")
    engine = _Engine(text=f"Hinckley Productions. Live event production. {sent}")
    social_watch.after_send(conn, engine, 1, "instagram", "hinckleyproductions", sent_body=sent)

    lead = conn.execute("SELECT email, phone FROM leads WHERE no=1").fetchone()
    assert lead["email"] is None and lead["phone"] is None
    assert conn.execute("SELECT COUNT(*) FROM buying_signals").fetchone()[0] == 0


def test_an_undated_post_stays_out_of_the_radar(conn):
    """docs/110 R5：雷达按日期排，读不出日期的动态只进时间线。"""
    engine = _Engine(text="Hinckley Productions. Just wrapped the arena installation.")
    social_watch.after_send(conn, engine, 1, "instagram", "hinckleyproductions")
    assert conn.execute("SELECT COUNT(*) FROM buying_signals").fetchone()[0] == 0
    assert conn.execute(
        "SELECT COUNT(*) FROM relationship_events WHERE lead_no=1").fetchone()[0] >= 1


def test_reading_the_same_profile_twice_writes_one_signal(conn):
    engine = _Engine()
    social_watch.after_send(conn, engine, 1, "instagram", "hinckleyproductions")
    social_watch.after_send(conn, engine, 1, "instagram", "hinckleyproductions")
    assert conn.execute("SELECT COUNT(*) FROM buying_signals WHERE lead_no=1").fetchone()[0] == 1


def test_already_following_costs_no_budget(conn):
    """docs/110 R2：没有发生写动作就不扣额度。"""
    engine = _Engine(follow_result={"already": True})
    before = social_watch.follows_left(conn)
    out = social_watch.after_send(conn, engine, 1, "instagram", "hinckleyproductions")
    assert out["followed"] == "本来就已关注"
    assert social_watch.follows_left(conn) == before


def test_a_refused_follow_stops_following_for_the_day(conn):
    engine = _Engine(follow_fails=True)
    out = social_watch.after_send(conn, engine, 1, "instagram", "hinckleyproductions")
    assert "关注失败" in out["followed"]
    assert social_watch.follows_left(conn) == 0


def test_the_follow_budget_still_binds(conn):
    from app import settings
    settings.set_value(conn, "social_watch_date", dt.date.today().isoformat())
    settings.set_value(conn, "social_follow_count", str(social_watch.FOLLOW_LIMIT))
    engine = _Engine()
    out = social_watch.after_send(conn, engine, 1, "instagram", "hinckleyproductions")
    assert engine.followed == []
    assert "额度" in out["followed"]


def test_nothing_here_can_break_the_send(conn):
    """docs/110 R7：主页读不了、关注点不动，都只是一行记录。"""
    engine = _Engine(read_fails=True)
    out = social_watch.after_send(conn, engine, 1, "instagram", "hinckleyproductions")
    assert out["read"] is False
    assert conn.execute("SELECT COUNT(*) FROM social_visits WHERE lead_no=1").fetchone()[0] == 1


def test_whatsapp_has_no_profile_to_stand_on(conn):
    engine = _Engine()
    out = social_watch.after_send(conn, engine, 1, "whatsapp", "+15551234")
    assert out == {}
    assert engine.read == [] and engine.followed == []


def test_a_named_person_on_the_page_becomes_a_candidate_not_a_fact(conn):
    """docs/110 R6：主页上写着职位的人进候选，不直接写进客户资料。"""
    engine = _Engine(text=("Hinckley Productions\nSteve Paladino\nCo-Founder\n"
                           "steve@hinckleyproductions.com\nLive event production"))
    social_watch.after_send(conn, engine, 1, "instagram", "hinckleyproductions")
    row = conn.execute("SELECT name, title, status FROM contact_candidates WHERE lead_no=1").fetchone()
    assert row["name"] == "Steve Paladino"
    assert row["status"] == "new"
    assert conn.execute("SELECT contact_name FROM leads WHERE no=1").fetchone()["contact_name"] is None


class _SendEngine(_Engine):
    """会发信，也会读主页和关注 —— 发送那条路上用的就是同一个 engine。"""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.sent = []

    def send_message(self, channel, target, message, image=None):
        self.sent.append((channel, target, message))


def test_the_send_path_harvests_the_profile_it_is_standing_on(conn):
    """docs/110 R1：发送这条路走完，关注和近况都要有。"""
    from app import channel_outreach

    engine = _SendEngine()
    result = channel_outreach.send_prepared(
        conn, [{"lead_no": 1, "channel": "instagram",
                "target": "hinckleyproductions", "body": "hi"}], engine)

    assert result["sent"] == 1
    assert engine.followed == ["hinckleyproductions"]
    assert engine.read == ["hinckleyproductions"]
    assert conn.execute("SELECT COUNT(*) FROM buying_signals WHERE lead_no=1").fetchone()[0] == 1


def test_a_broken_profile_read_never_fails_the_send(conn):
    """docs/110 R7：顺手做的事出错，信仍然是发出去了的。"""
    from app import channel_outreach

    engine = _SendEngine(read_fails=True, follow_fails=True)
    result = channel_outreach.send_prepared(
        conn, [{"lead_no": 1, "channel": "instagram",
                "target": "hinckleyproductions", "body": "hi"}], engine)

    assert result == {**result, "sent": 1, "failed": 0}
    assert conn.execute(
        "SELECT status FROM outreach WHERE lead_no=1 AND channel='instagram'"
    ).fetchone()["status"] == "messaged"


def test_whatsapp_sends_do_not_try_to_read_a_profile(conn):
    from app import channel_outreach

    conn.execute("UPDATE leads SET phone='+15551234' WHERE no=1")
    conn.commit()
    engine = _SendEngine()
    channel_outreach.send_prepared(
        conn, [{"lead_no": 1, "channel": "whatsapp", "target": "+15551234", "body": "hi"}],
        engine)
    assert engine.read == [] and engine.followed == []


def test_the_batch_reports_what_it_picked_up(conn):
    """一批发完，说得出关注了几家、记下几条（docs/110 R1）。"""
    from app import channel_outreach

    engine = _SendEngine()
    result = channel_outreach.send_prepared(
        conn, [{"lead_no": 1, "channel": "instagram",
                "target": "hinckleyproductions", "body": "hi"}], engine)
    assert result["followed"] == 1
    assert result["learned"] >= 1
