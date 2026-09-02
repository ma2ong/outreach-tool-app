"""一封说不出自己是哪一版的信（docs/90）。"""
import pytest

from app import backfill_variants, campaigns, social_queue


def _sent(conn, no, campaign, variant=None, channel="email"):
    conn.execute(
        "INSERT INTO send_log(lead_no, channel, campaign, sent_at, variant)"
        " VALUES (?,?,?,?,?)", (no, channel, campaign, "2026-08-01T00:00:00", variant))
    conn.commit()


def _variants(conn):
    return [(r["campaign"], r["variant"]) for r in
            conn.execute("SELECT campaign, variant FROM send_log ORDER BY id")]


def test_a_sequence_send_recovers_its_variant_from_the_campaign(conn):
    """验收 1：序列名就写在 campaign 上，读出来不叫猜。"""
    _sent(conn, 1, "序列:冷邮件 3 步跟进（英语）")

    assert backfill_variants.run(conn)["updated"] == 1
    assert _variants(conn) == [("序列:冷邮件 3 步跟进（英语）", "冷邮件 3 步跟进（英语）")]


def test_a_blast_label_is_a_date_not_a_copy_version(conn):
    """验收 2：`email 2026-07-23` 说的是哪天发的，不是哪一版文案。"""
    _sent(conn, 1, "email 2026-07-23")
    _sent(conn, 2, "每日社媒队列", channel="instagram")

    assert backfill_variants.run(conn)["updated"] == 0
    assert all(v is None for _, v in _variants(conn))


def test_a_row_that_already_names_its_copy_is_left_alone(conn):
    """验收 3：已经有变体的行一个字段都不动。"""
    _sent(conn, 1, "序列:冷邮件 3 步跟进（英语）", variant="冷邮件 3 步跟进（英语·活动租赁）")

    assert backfill_variants.run(conn)["updated"] == 0
    assert _variants(conn)[0][1] == "冷邮件 3 步跟进（英语·活动租赁）"


def test_running_it_twice_changes_nothing_the_second_time(conn):
    """验收 4：回填要能重复跑。"""
    _sent(conn, 1, "序列:冷邮件 3 步跟进（韩语）")

    assert backfill_variants.run(conn)["updated"] == 1
    assert backfill_variants.run(conn)["updated"] == 0


def test_a_dm_records_the_copy_family_it_actually_used(conn):
    """验收 5：社媒 DM 也要说得出自己是哪一版。"""
    variant = social_queue.variant_of({"no": 7, "tags": "租赁商"})

    assert variant and variant.startswith("social:")
    campaigns.log_send(conn, 1, "instagram", "每日社媒队列",
                       body="hi", variant=variant)
    assert _variants(conn) == [("每日社媒队列", variant)]


def test_the_queue_keeps_the_version_it_was_built_with(conn):
    """验收 6：排队之后改了标签，发出去的那条记的仍是排队时那一版。"""
    conn.execute("UPDATE leads SET tags='租赁商', instagram='alphaig',"
                 " hook='Saw the arena job.' WHERE no=1")
    conn.commit()
    at_build = social_queue.variant_of(
        dict(conn.execute("SELECT * FROM leads WHERE no=1").fetchone()))

    conn.execute("UPDATE leads SET tags='工程商' WHERE no=1")
    conn.commit()
    now = social_queue.variant_of(
        dict(conn.execute("SELECT * FROM leads WHERE no=1").fetchone()))

    assert at_build != now, "前提：改标签会改变文案家族，否则这条验收测不到东西"
    # 队列行记下的是排队时那一版，发送时不重算。
    assert social_queue.variant_of({"no": 1, "tags": "租赁商"}) == at_build


def test_the_variant_travels_from_the_queue_into_the_send_log(conn):
    """队列上记下的那一版，要真的落到 send_log —— 中间断一节就等于没记。"""
    from app import channel_outreach

    social_queue.ensure_schema(conn)
    conn.execute(
        "INSERT INTO social_dm_queue(queue_date, lead_no, channel, target, body,"
        " rank_order, created_at, variant)"
        " VALUES (date('now'),1,'instagram','alphaig','hi',1,'2026-09-02','social:rental#1')")
    conn.commit()
    item = dict(conn.execute("SELECT * FROM social_dm_queue").fetchone())

    class _Engine:
        def send_message(self, *a, **kw):
            return None

    channel_outreach.send_prepared(conn, [item], _Engine(), None,
                                   campaign="每日社媒队列")

    assert _variants(conn) == [("每日社媒队列", "social:rental#1")]
