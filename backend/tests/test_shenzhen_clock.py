"""发送窗口按深圳时间算，对方时区只决定先发谁（docs/92）。

这些测试守着 09-03 那个 bug 不再回来：队列按深圳日期删除，发送时刻按收件人时区计算，
两个日历互不知情，结果 31 条里 24 条在轮到自己之前就被删掉，六天一条没发出去，而且没有
任何地方留下一个字。

守的是四件事：一天从上午 9 点开始而不是零点、深圳的钟说了算、对方的钟只排序不否决、
错过的时刻往后顺延而不是作废。
"""
import datetime as dt

import pytest

from app import local_time as lt
from app import social_autonomy as sa
from app import social_queue
from app.db import connect, init_schema


def cn(y, m, d, h, mi=0) -> dt.datetime:
    """深圳墙上时钟的那一刻，返回带时区的 UTC —— 循环拿到的就是这个形状。"""
    return dt.datetime(y, m, d, h, mi, tzinfo=dt.UTC) - dt.timedelta(hours=lt.SHENZHEN_OFFSET)


# ---------------------------------------------------------------- R1 深圳的窗口

@pytest.mark.parametrize("hour,minute,expected", [
    (9, 0, "core"),        # 窗口开始
    (12, 30, "core"),
    (18, 19, "core"),      # 最后一分钟
    (18, 20, "paused"),    # 边是关着的
    (18, 25, "paused"),
    (18, 30, "extended"),  # 电脑还开着
    (23, 0, "extended"),
    (2, 0, "extended"),    # 跨过深圳零点，还是同一段
    (8, 59, "extended"),   # 一直到新一天开始前
])
def test_the_window_is_read_off_the_shenzhen_clock(hour, minute, expected):
    assert lt.phase(cn(2026, 9, 3, hour, minute)) == expected


def test_a_naive_time_is_read_as_shenzhen_not_utc():
    """循环传的是带时区的 UTC，队列传的是本地墙上时钟。两种都得答对，否则又是两个日历。"""
    assert lt.phase(dt.datetime(2026, 9, 3, 22, 0)) == "extended"
    assert lt.phase(cn(2026, 9, 3, 22, 0)) == "extended"


# ---------------------------------------------------------------- R2 销售日

@pytest.mark.parametrize("hour,expected_day", [
    (9, 3),     # 新一天从上午 9 点开始
    (14, 3),
    (23, 3),
    (1, 2),     # 深圳凌晨一点还算前一天的延长窗口
    (8, 2),
])
def test_a_day_starts_at_nine_in_the_morning(hour, expected_day):
    assert lt.sales_day(cn(2026, 9, 3, hour)) == dt.date(2026, 9, expected_day)


def test_the_queue_survives_shenzhen_midnight():
    """09-03 的 bug 本身：22:00 排好的队，00:30 还得在。

    旧代码在深圳零点 `DELETE ... WHERE queue_date != today`，把延长窗口正中间的队列
    整批删掉，第二天重排、重抽时刻、再删一遍。
    """
    conn = _book()
    social_queue.build_today(conn, now=cn(2026, 9, 3, 22))
    before = conn.execute("SELECT COUNT(*) FROM social_dm_queue").fetchone()[0]
    assert before > 0

    social_queue.build_today(conn, now=cn(2026, 9, 4, 0, 30))
    rows = conn.execute("SELECT DISTINCT queue_date FROM social_dm_queue").fetchall()
    assert [r[0] for r in rows] == ["2026-09-03"], "跨过深圳零点，销售日没变，队列不该被删"
    assert conn.execute("SELECT COUNT(*) FROM social_dm_queue").fetchone()[0] == before


def test_a_lead_messaged_before_midnight_is_not_requeued_after_it():
    """销售日跨零点，「今天已经发过」也得跨零点，否则 23:00 私信过的客户 00:30 又排一遍。"""
    conn = _book()
    social_queue.build_today(conn, now=cn(2026, 9, 3, 22))
    row = conn.execute("SELECT lead_no FROM social_dm_queue LIMIT 1").fetchone()
    conn.execute("INSERT INTO send_log(lead_no, channel, campaign, sent_at, body)"
                 " VALUES (?,'whatsapp','t',?,'x')",
                 (row[0], cn(2026, 9, 3, 23).isoformat()))
    conn.commit()

    social_queue.build_today(conn, now=cn(2026, 9, 4, 0, 30))
    still = conn.execute("SELECT COUNT(*) FROM social_dm_queue WHERE lead_no=?",
                         (row[0],)).fetchone()[0]
    assert still == 0


# ---------------------------------------------------------------- R3 对方的钟只排序

def test_the_american_evening_finally_goes_out():
    """六天没发出去的那个场景：深圳 22:00，美国上午 —— 旧规则在这一刻已经把队列删了。"""
    conn = _book(country="USA")
    sa.set_mode(conn, "whatsapp", "auto", confirm="whatsapp")
    social_queue.build_today(conn, now=cn(2026, 9, 3, 9))
    sent = _walk(conn, start=cn(2026, 9, 3, 22), until=cn(2026, 9, 4, 1))
    assert sent, "深圳晚上、美国上午，这是一天里最该发的时段"


def test_a_message_waits_for_their_morning_while_one_is_still_coming():
    """偏好必须能让消息「等」，不然它什么都不是。

    深圳 09:00–18:20 对美国是当地 19:00–04:20。只排序不等待的话，队列在对方入睡前就
    排空了 —— 第一次拿真实库跑，31 条里 22 条落在美国凌晨 0–4 点。
    """
    conn = _book(country="USA")
    sa.set_mode(conn, "whatsapp", "auto", confirm="whatsapp")
    social_queue.build_today(conn, now=cn(2026, 9, 3, 9))
    sent = _walk(conn, start=cn(2026, 9, 3, 9), until=cn(2026, 9, 4, 9))
    assert sent
    for item in sent:
        # 深圳 12:00–21:00 正是美国当地 22:00–07:00，这一段应该是空的。
        assert lt.suits_recipient("USA", item["_at"]),             f"落在了美国当地 {lt.local_now('USA', item['_at']):%H:%M}"


def test_when_no_civil_hour_is_left_it_goes_anyway():
    """「实在达不到就不考虑对方时区按计划发」—— 等待到销售日结束为止，不跨天。"""
    conn = _book(country="USA")
    sa.set_mode(conn, "whatsapp", "auto", confirm="whatsapp")
    social_queue.build_today(conn, now=cn(2026, 9, 3, 9))
    # 深圳 08:30，销售日只剩半小时，美国当地 02:30 且今天不会再变好 —— 照发。
    assert _walk(conn, start=cn(2026, 9, 4, 8, 30), until=cn(2026, 9, 4, 9))


def test_a_country_with_no_civil_moment_falls_back_to_our_own_window():
    """docs/65 R1.1 的硬底线取消了：今天够不着对方的白天，就用我们自己的窗口发。"""
    day = dt.date(2026, 9, 3)
    assert lt.civil_slots("Freedonia", day) == []
    moment = lt.shenzhen(lt.moment_for(1, day, "Freedonia"))
    assert lt.CORE[0] <= moment.time() < lt.CORE[1]


def test_a_country_we_cannot_place_is_sent_too():
    """docs/65 R4 反过来了：认不出国家不再是不发的理由，只是排在后面。"""
    conn = _book(country="Freedonia")
    sa.set_mode(conn, "whatsapp", "auto", confirm="whatsapp")
    social_queue.build_today(conn, now=cn(2026, 9, 3, 9))
    assert _walk(conn, start=cn(2026, 9, 3, 19), until=cn(2026, 9, 3, 23))


def test_whoever_is_awake_goes_first():
    """同一刻两条都到点，此刻正落在对方 7–22 点的那条排前面 —— 这是时区剩下的全部作用。"""
    conn = _book(country="USA")
    # 深圳 10:00 = 美国前一天 20:00（在 7–22 内）、日本 11:00（在内）、德国 04:00（不在）。
    conn.executescript("""
        DELETE FROM leads;
        INSERT INTO leads(no, company_en, country, phone) VALUES
            (1, 'Berlin Co', 'Germany', '+4930111111'),
            (2, 'Tokyo Co',  'Japan',   '+81311111111');
    """)
    conn.commit()
    sa.set_mode(conn, "whatsapp", "auto", confirm="whatsapp")
    social_queue.ensure_schema(conn)
    day = "2026-09-03"
    conn.executescript(f"""
        INSERT INTO social_dm_queue(queue_date, lead_no, channel, target, body,
                                    rank_order, status, created_at) VALUES
            ('{day}', 1, 'whatsapp', '4930111111',  'Hi Berlin', 1, 'ready', '{day}'),
            ('{day}', 2, 'whatsapp', '81311111111', 'Hi Tokyo',  2, 'ready', '{day}');
    """)
    conn.commit()
    sent = _walk(conn, start=cn(2026, 9, 3, 9), until=cn(2026, 9, 4, 9))
    assert {i["lead_no"] for i in sent} == {1, 2}
    # 两条都落在各自的白天 —— 时区不再否决谁，但它决定了各自的时刻。
    for item in sent:
        country = conn.execute("SELECT country FROM leads WHERE no=?",
                               (item["lead_no"],)).fetchone()[0]
        assert lt.suits_recipient(country, item["_at"]), f"{country} 落在了对方的深夜"


def test_nothing_goes_out_in_the_evening_pause():
    conn = _book()
    sa.set_mode(conn, "whatsapp", "auto", confirm="whatsapp")
    social_queue.build_today(conn, now=cn(2026, 9, 3, 9))
    assert not _walk(conn, start=cn(2026, 9, 3, 18, 20), until=cn(2026, 9, 3, 18, 30))


# ---------------------------------------------------------------- R4 顺延不作废

def test_a_missed_moment_rolls_forward():
    """`MISSED_AFTER` 取消了。一条消息只因为发出去了或者销售日结束才离开队列。"""
    conn = _book()
    sa.set_mode(conn, "whatsapp", "auto", confirm="whatsapp")
    social_queue.build_today(conn, now=cn(2026, 9, 3, 9))
    # 服务整个白天没跑，晚上才回来 —— 旧规则会把过了两小时的时刻全部作废。
    assert _walk(conn, start=cn(2026, 9, 3, 21), until=cn(2026, 9, 3, 23))


def test_a_whole_day_drains_the_queue():
    """31 条里活下来 7 条是这次修的核心。走完一个销售日，队列应该基本清空。"""
    conn = _book(count=12, country="USA")
    sa.set_mode(conn, "whatsapp", "auto", confirm="whatsapp")
    social_queue.build_today(conn, now=cn(2026, 9, 3, 9))
    queued = conn.execute(
        "SELECT COUNT(*) FROM social_dm_queue WHERE channel='whatsapp'").fetchone()[0]
    sent = _walk(conn, start=cn(2026, 9, 3, 9), until=cn(2026, 9, 4, 9), step=8)
    # 允许差一条：两条时刻撞在销售日最后几分钟时，后一条要让出这一轮的渠道名额，
    # 而这一天已经没有下一轮了。它明天会被重新排回来，不会丢。
    assert len(sent) >= queued - 1, f"排了 {queued} 条，只发出去 {len(sent)} 条"


# ---------------------------------------------------------------- R5 试过就留痕

def test_a_run_where_nothing_succeeded_says_so(monkeypatch):
    """六天全失败长得和六天没事一模一样 —— 这两件事必须长得不一样。"""
    conn = _book()
    sa.set_mode(conn, "whatsapp", "auto", confirm="whatsapp")
    social_queue.build_today(conn, now=cn(2026, 9, 3, 9))
    monkeypatch.setattr(sa, "_deliver", lambda c, items: {
        "sent": 0, "failed": len(items),
        "errors": [{"no": i["lead_no"], "error": "Timeout 30000ms exceeded"} for i in items]})
    # 深圳上午 = 美国前一晚 19:00 起，正是队列该动的时段。
    for minute in range(0, 3 * 60, 10):
        sa.run_due(conn, now=cn(2026, 9, 3, 9) + dt.timedelta(minutes=minute))

    log = sa.last_run(conn)
    assert log, "试过就得留痕，哪怕一条都没成"
    assert log["attempted"] > 0 and log["failed"] > 0
    assert "Timeout" in log["error"]


def test_a_day_that_never_tried_still_writes_nothing(monkeypatch):
    """docs/48 R3 不变：没到点是真的没事，不许写噪音。"""
    conn = _book()
    sa.set_mode(conn, "whatsapp", "auto", confirm="whatsapp")
    monkeypatch.setattr(sa, "_deliver", lambda c, items: {"sent": 0, "failed": 0, "errors": []})
    sa.run_due(conn, now=cn(2026, 9, 3, 18, 25))     # 停顿里
    assert sa.last_run(conn) is None


# ---------------------------------------------------------------- R6 谁在等谁

def test_an_auto_channel_is_not_waiting_for_allen():
    conn = _book()
    social_queue.build_today(conn, now=cn(2026, 9, 3, 9))
    assert social_queue.awaiting_you(conn, now=cn(2026, 9, 3, 9)) > 0
    for channel in social_queue.CHANNELS:
        sa.set_mode(conn, channel, "auto", confirm=channel)
    assert social_queue.awaiting_you(conn, now=cn(2026, 9, 3, 9)) == 0


def test_korea_is_still_waiting_for_him_on_an_auto_channel():
    """docs/63 没变：渠道自动，但韩国压回手动，那这几条确实在等他。"""
    conn = _book(country="South Korea")
    for channel in social_queue.CHANNELS:
        sa.set_mode(conn, channel, "auto", confirm=channel)
    social_queue.build_today(conn, now=cn(2026, 9, 3, 9))
    assert social_queue.awaiting_you(conn, now=cn(2026, 9, 3, 9)) > 0


# ---------------------------------------------------------------- 每条自己的时刻

def test_each_message_still_gets_its_own_moment():
    """docs/65 R3 保留：一批消息同一分钟出去是这套东西最不像人的地方。"""
    day = dt.date(2026, 9, 3)
    moments = {lt.moment_for(no, day, "USA") for no in range(1, 30)}
    assert len(moments) > 15
    for moment in moments:
        assert lt.suits_recipient("USA", moment)


def test_the_moments_spread_across_the_whole_reachable_stretch():
    """全挤在对方上午 7 点那一刻，就是把节流交给了限速器（docs/92 R3）。"""
    day = dt.date(2026, 9, 3)
    moments = sorted(lt.moment_for(no, day, "USA") for no in range(1, 14))
    span = (moments[-1] - moments[0]).total_seconds() / 3600
    assert span > 8, f"13 条只散在 {span:.1f} 小时里"


def test_the_moment_is_stable_for_the_same_lead_and_day():
    day = dt.date(2026, 9, 3)
    assert lt.moment_for(7, day, "USA") == lt.moment_for(7, day, "USA")


# ---------------------------------------------------------------- 夹具

def _book(count: int = 6, country: str = "USA"):
    conn = connect(":memory:")
    init_schema(conn)
    rows = ", ".join(
        f"({i}, 'Co{i}', '{country}', '+1555000{i:04d}', 'Saw the P{i} wall on your site.')"
        for i in range(1, count + 1))
    conn.executescript(
        f"INSERT INTO leads(no, company_en, country, phone, hook) VALUES {rows};")
    conn.commit()
    return conn


def _walk(conn, start: dt.datetime, until: dt.datetime, step: int = 5) -> list[dict]:
    """按真实循环的样子走一段时间，返回这段时间里发出去的东西。"""
    sent: list[dict] = []
    now = start
    while now < until:
        original = sa._deliver

        def deliver(c, items, _at=now):
            sent.extend([{**i, "_at": _at} for i in items])
            return {"sent": len(items), "failed": 0, "errors": [],
                    "sent_ids": [i["id"] for i in items]}

        sa._deliver = deliver
        try:
            sa.run_due(conn, now=now)
        finally:
            sa._deliver = original
        now += dt.timedelta(minutes=step)
    return sent


def test_catching_up_does_not_pick_a_worse_hour_than_it_missed():
    """docs/92 R4 的补充，来自 09-03 17:00 那次上线。

    队列排在上午，服务下午才带着新代码起来，八条消息的时刻都已经过去 —— 顺延是对的，
    但顺延到对方当地凌晨三点就把「不作废」变成了「作废也比这强」。补发也要挑体面时间，
    除非今天已经挑不出了。
    """
    conn = _book(country="USA")
    sa.set_mode(conn, "whatsapp", "auto", confirm="whatsapp")
    social_queue.build_today(conn, now=cn(2026, 9, 3, 9))
    # 深圳 17:00 = 美国当地 03:00，而当天 21:00 起还够得着他们的上午。
    assert not _walk(conn, start=cn(2026, 9, 3, 17), until=cn(2026, 9, 3, 18))
    sent = _walk(conn, start=cn(2026, 9, 3, 21), until=cn(2026, 9, 4, 9))
    assert sent
    for item in sent:
        assert lt.suits_recipient("USA", item["_at"])
