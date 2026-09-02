"""一句话进来，一个待确认的动作出去（docs/88）。

这里不调模型：`interpret` 是唯一会调模型的地方，测试把它替换掉，
剩下的每一条规则都必须在没有模型的情况下自己成立。
"""
import datetime as dt

import pytest

from app import activities, settings
from app.agent import command, executors, proposals


@pytest.fixture
def spoken(monkeypatch):
    """让 interpret 返回指定结果，不碰任何后端。"""
    def use(action, args=None, confidence=0.9, question=""):
        monkeypatch.setattr(command, "interpret", lambda conn, said: {
            "action": action, "args": args or {}, "confidence": confidence,
            "question": question,
        })
    return use


@pytest.fixture
def all_auto(conn):
    """把八个自主开关全部打到 auto —— 这正是生产库现在的状态。"""
    conn.execute("UPDATE leads SET email='a@alpha.com' WHERE no=1")
    conn.execute("UPDATE leads SET email='b@beta.com' WHERE no=2")
    conn.commit()
    proposals.ensure_schema(conn)
    for kind in proposals.KINDS:
        proposals.set_autonomy(conn, kind, "auto")
    return conn


def test_a_command_waits_even_when_every_dial_is_on_auto(all_auto, spoken):
    """R2：开关是给代码路径设的，不是给一句话设的。"""
    spoken("send_outreach", {"market": "USA", "limit": 2})
    out = command.run(all_auto, "给美国那批发一轮")

    assert out["outcome"] == "proposed"
    assert out["proposal"]["status"] == "pending"
    assert out["proposal"]["execution_result"] in (None, "")
    # 提议躺在队列里等人，没有任何一条被执行
    assert [p["status"] for p in proposals.list_proposals(all_auto)] == ["pending"]


def test_the_number_of_companies_is_on_screen_before_the_button(all_auto, spoken):
    """R4：一句模糊的话乘以 460 是这个入口最现实的事故形状。"""
    spoken("send_outreach", {"market": "USA", "limit": 1})
    one = command.run(all_auto, "给美国发 1 家")
    spoken("send_outreach", {"market": "USA", "limit": 5})
    many = command.run(all_auto, "给美国发 5 家")

    def touched(out):
        return dict(out["impact"])["影响客户"]

    assert touched(one) == "1 家"
    assert touched(many) == "2 家"          # 库里美国只有两家，说了 5 也只碰 2


def test_rescheduling_edits_the_date_and_leaves_a_record(conn, spoken):
    """R1：579 条排期是 agent 自己定的，改期得有入口 —— 而且要留痕。"""
    activities.create(conn, 1, {"title": "跟进 Alpha AV：先完成 ICP 分级", "type": "task",
                                "due_at": "2026-10-01"})
    spoken("reschedule_work", {"due_at": "today", "scope": "ICP"})
    out = command.run(conn, "那些分级任务全提到今天")

    assert out["outcome"] == "proposed"
    proposals.approve(conn, out["proposal"]["id"])
    done = proposals.get(conn, out["proposal"]["id"])
    assert done["status"] == "executed"
    assert activities.list_all(conn)[0]["due_at"] == dt.date.today().isoformat()
    # 直接 UPDATE 不留痕的实现不算通过
    assert "reschedule_work" in {p["kind"] for p in proposals.list_proposals(conn, status=None)}


def test_a_sentence_it_cannot_read_produces_nothing(conn, spoken):
    """R3：低置信度是停下来问的理由，不是猜的理由。"""
    spoken("send_outreach", {"market": "USA"}, confidence=0.2)
    out = command.run(conn, "那个啥你看着办")

    assert out["outcome"] == "ask"
    assert out["question"]
    assert proposals.list_proposals(conn, status=None) == []


def test_a_missing_market_is_asked_for_not_filled_in(conn, spoken):
    """R3：参数缺就问，不填默认值。"""
    spoken("stop_sequence", {})
    out = command.run(conn, "停掉跟进")

    assert out["outcome"] == "ask"
    assert "市场" in out["question"]
    assert proposals.list_proposals(conn, status=None) == []


def test_pricing_is_refused_not_negotiated(conn, spoken):
    """白名单之外一律拒绝 —— 换个说法也绕不过去。"""
    spoken("none", question="定价归 Allen，我不做这件事。")
    out = command.run(conn, "给他报个价，2.9 的做到 320 一平")

    assert out["outcome"] == "refused"
    assert proposals.list_proposals(conn, status=None) == []


def test_the_ledger_counts_how_often_a_sentence_is_repeated(conn, spoken):
    """R5：同一句话说到第三遍，就该有人把它写成规则。"""
    spoken("today")
    for _ in range(3):
        out = command.run(conn, "今天什么情况")

    assert out["times"] == 3
    assert command.history(conn)[0]["times"] == 3


def test_reading_the_day_touches_nothing(conn, spoken):
    """只读就是只读：不落提议，也不改设置。"""
    settings.set_value(conn, "autosend_last_result", "09-02 09:14 自动发送：成功 40")
    spoken("today")
    out = command.run(conn, "今天什么情况")

    assert out["outcome"] == "answered"
    assert any("成功 40" in line["v"] for line in out["answer"]["lines"])
    assert proposals.list_proposals(conn, status=None) == []


def test_every_command_action_lands_on_an_existing_executor(conn):
    """R6/验收 6：命令入口不引入新的执行分支。"""
    for action in command.WRITE_ACTIONS:
        assert action in proposals.KINDS
        assert action in executors.HANDLERS
