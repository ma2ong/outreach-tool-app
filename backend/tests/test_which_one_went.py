"""到底哪一条发出去了（docs/102）。

09-04 第一轮自动发送：WhatsApp 排第一且失败、Instagram 排第二且成功，而两处调用方都写着
`items[:result["sent"]]` —— 于是失败那条被标成 `sent`，成功那条还挂在队列里，时间戳盖在
一个没发生过的发送上，仪表盘报告 whatsapp 发了 1 条。一个计数回答不了一个身份问题。
"""
import datetime as dt

import pytest

from app import channel_outreach, social_autonomy as sa, social_queue
from app.db import connect, init_schema


class _Engine:
    """按渠道决定成败的假引擎 —— 真实那轮就是「第一条失败、第二条成功」。"""

    def __init__(self, fails=()):
        self.fails = set(fails)
        self.sent = []

    def send_message(self, channel, target, message, image=None):
        if channel in self.fails:
            raise RuntimeError(f"{channel} 炸了")
        self.sent.append((channel, target))


@pytest.fixture(autouse=True)
def _no_pacing(monkeypatch):
    """发送器两条之间真的 sleep 60–300 秒。测的是记账，不是节奏。"""
    monkeypatch.setattr(channel_outreach, "DEFAULT_DELAY",
                        {c: (0, 0) for c in ("whatsapp", "instagram", "facebook")})


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    social_queue.ensure_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, phone, instagram) VALUES
            (1, 'Atlanta Pro AV', 'USA', '+14048352230', NULL),
            (2, 'Pixel Wall',     'USA', NULL, 'pixelwall');
        INSERT INTO social_dm_queue(queue_date, lead_no, channel, target, body,
                                    rank_order, status, created_at) VALUES
            ('2026-09-04', 1, 'whatsapp',  '14048352230', 'Hi Atlanta', 1, 'ready', '2026-09-04'),
            ('2026-09-04', 2, 'instagram', 'pixelwall',   'Hi Pixel',   2, 'ready', '2026-09-04');
    """)
    c.commit()
    return c


def _items(conn):
    return [dict(r) for r in conn.execute(
        "SELECT id, lead_no, channel, target, body FROM social_dm_queue ORDER BY rank_order")]


def _status(conn, lead_no):
    return conn.execute(
        "SELECT status FROM social_dm_queue WHERE lead_no=?", (lead_no,)).fetchone()[0]


# ---------------------------------------------------------------- R1

def test_the_sender_says_which_ones_went(conn):
    engine = _Engine(fails={"whatsapp"})
    result = channel_outreach.send_prepared(conn, _items(conn), engine)
    assert result["sent"] == 1
    ids = result["sent_ids"]
    assert len(ids) == 1
    lead = conn.execute("SELECT lead_no FROM social_dm_queue WHERE id=?", (ids[0],)).fetchone()[0]
    assert lead == 2, "成功的是 Instagram 那条，不是排在前面的 WhatsApp"


def test_the_failed_row_is_not_marked_sent(conn, monkeypatch):
    """09-04 的实况：Atlanta Pro AV 从没发出去，却被标成已发。"""
    engine = _Engine(fails={"whatsapp"})
    for channel in ("whatsapp", "instagram"):
        sa.set_mode(conn, channel, "auto", confirm=channel)
    monkeypatch.setattr(sa, "_deliver", lambda c, items: channel_outreach.send_prepared(
        c, items, engine))
    _run_all_day(conn)
    assert _status(conn, 1) == "ready", "没发出去的不能是 sent"
    assert _status(conn, 2) == "sent"


def test_the_timestamp_lands_on_the_channel_that_actually_sent(conn, monkeypatch):
    engine = _Engine(fails={"whatsapp"})
    for channel in ("whatsapp", "instagram"):
        sa.set_mode(conn, channel, "auto", confirm=channel)
    monkeypatch.setattr(sa, "_deliver", lambda c, items: channel_outreach.send_prepared(
        c, items, engine))
    _run_all_day(conn)
    from app import settings
    assert not settings.get(conn, "social_last_send_at_whatsapp"),         "whatsapp 一条都没发成，不该有时间戳"
    assert settings.get(conn, "social_last_send_at_instagram")


def test_no_run_record_ever_claims_a_channel_that_did_not_send(conn, monkeypatch):
    """这是仪表盘上那句「whatsapp 发了 1 条」的来源。一整天里没有任何一轮可以那样说。

    WhatsApp 会整天重试并整天失败，所以当天最后一条记录本来就是它的失败 —— 要守的不是
    「最后一条说什么」，而是「没有一条说了假话」。
    """
    engine = _Engine(fails={"whatsapp"})
    for channel in ("whatsapp", "instagram"):
        sa.set_mode(conn, channel, "auto", confirm=channel)
    monkeypatch.setattr(sa, "_deliver", lambda c, items: channel_outreach.send_prepared(
        c, items, engine))

    claimed = []
    start = dt.datetime(2026, 9, 4, 1, 0, tzinfo=dt.UTC)
    for minute in range(0, 24 * 60, 10):
        sa.run_due(conn, now=start + dt.timedelta(minutes=minute))
        log = sa.last_run(conn)
        if log:
            claimed.append(log["channels"])

    assert {"instagram": 1} in claimed, "真发出去的那一轮要说出来"
    assert not any("whatsapp" in c for c in claimed), "没发成的渠道不许出现在任何一轮里"


def test_a_deferred_item_is_neither_sent_nor_failed(conn, monkeypatch):
    """日限额挡下的条目不算成功也不算失败 —— items[:sent] 在这里同样对不上。"""
    monkeypatch.setattr(channel_outreach, "DAILY_CAP", {"whatsapp": 0, "instagram": 40,
                                                        "facebook": 20})
    engine = _Engine()
    result = channel_outreach.send_prepared(conn, _items(conn), engine)
    assert result["deferred"] == 1
    sent_lead = conn.execute("SELECT lead_no FROM social_dm_queue WHERE id=?",
                             (result["sent_ids"][0],)).fetchone()[0]
    assert sent_lead == 2


def test_uncertain_queue_send_stays_visible_and_cannot_be_sent_twice(conn):
    class AcceptedThenTimeout:
        def __init__(self):
            self.calls = 0

        def send_message(self, *_args, **_kwargs):
            self.calls += 1
            raise TimeoutError("click result unknown")

    engine = AcceptedThenTimeout()
    item = _items(conn)[0]
    first = channel_outreach.send_prepared(conn, [item], engine)
    second = channel_outreach.send_prepared(conn, [item], engine)

    assert first["failed"] == 1
    assert second["sent"] == 0
    assert engine.calls == 1
    assert _status(conn, item["lead_no"]) == "ready"
    assert conn.execute("SELECT status FROM delivery_intents").fetchone()["status"] == "unknown"


def test_confirming_uncertain_queue_send_repairs_queue_and_crm(conn):
    from app import delivery_intents

    class Timeout:
        def send_message(self, *_args, **_kwargs):
            raise TimeoutError("click result unknown")

    item = _items(conn)[0]
    channel_outreach.send_prepared(conn, [item], Timeout(), campaign="Queue repair")
    intent = delivery_intents.unresolved(conn)[0]

    delivery_intents.resolve(conn, intent["id"], "sent")

    assert _status(conn, item["lead_no"]) == "sent"
    assert conn.execute(
        "SELECT status FROM outreach WHERE lead_no=? AND channel=?",
        (item["lead_no"], item["channel"]),
    ).fetchone()["status"] == "messaged"
    assert conn.execute("SELECT campaign FROM send_log").fetchone()["campaign"] == "Queue repair"


# ---------------------------------------------------------------- R3

def test_every_channel_leaves_its_own_error(conn, monkeypatch):
    """09-03 夜里三个渠道各失败一次，记录里只有第一条错误，WhatsApp 的从没出现过。"""
    engine = _Engine(fails={"whatsapp", "instagram"})
    for channel in ("whatsapp", "instagram"):
        sa.set_mode(conn, channel, "auto", confirm=channel)
    monkeypatch.setattr(sa, "_deliver", lambda c, items: channel_outreach.send_prepared(
        c, items, engine))
    _run_all_day(conn)
    log = sa.last_run(conn)
    assert set(log["errors"]) == {"whatsapp", "instagram"}
    assert "whatsapp 炸了" in log["errors"]["whatsapp"]


def _run_all_day(conn):
    start = dt.datetime(2026, 9, 4, 1, 0, tzinfo=dt.UTC)      # 深圳 09:00
    for minute in range(0, 24 * 60, 10):
        sa.run_due(conn, now=start + dt.timedelta(minutes=minute))


# ---------------------------------------------------------------- R2 死掉的上下文

class _DeadThenAlive:
    """第一次导航抛「context 已关闭」，重开之后正常 —— 09-04 WhatsApp 的实况。"""

    def __init__(self, fail_times=1):
        self.left = fail_times
        self.visited = []

    def goto(self, url, **_kw):
        if self.left:
            self.left -= 1
            raise RuntimeError(
                "Page.goto: Target page, context or browser has been closed")
        self.visited.append(url)


def _engine_with_pages(pages):
    from app.playwright_engine import PlaywrightEngine

    engine = PlaywrightEngine()
    engine._ctx = {"whatsapp": object()}
    it = iter(pages)
    engine._page = lambda _channel: next(it)
    return engine


def test_a_dead_context_is_found_by_the_navigation_and_retried_once():
    """`_page` 返回缓存页面时一个测试都没做过，所以真实的测试只能是第一次导航。"""
    dead, alive = _DeadThenAlive(), _DeadThenAlive(fail_times=0)
    engine = _engine_with_pages([dead, alive])
    page = engine._open("whatsapp", "https://web.whatsapp.com/send?phone=1")
    assert page is alive
    assert alive.visited == ["https://web.whatsapp.com/send?phone=1"]
    assert "whatsapp" not in engine._ctx, "死掉的 context 不能留在缓存里"


def test_it_retries_once_and_only_once():
    engine = _engine_with_pages([_DeadThenAlive(), _DeadThenAlive()])
    with pytest.raises(RuntimeError, match="has been closed"):
        engine._open("whatsapp", "https://web.whatsapp.com/send?phone=1")


def test_an_error_that_is_not_a_dead_context_is_not_retried():
    """超时、网络错误照常抛出去 —— 重试只对「什么都还没打字」的那一类失败安全。"""
    class _Timeout:
        def goto(self, _url, **_kw):
            raise RuntimeError("Timeout 60000ms exceeded")

    engine = _engine_with_pages([_Timeout(), _Timeout()])
    with pytest.raises(RuntimeError, match="Timeout"):
        engine._open("whatsapp", "https://web.whatsapp.com/send?phone=1")
