"""它早就告诉过我们了（docs/104）。

WhatsApp 网页版弹的是「电话号码+27 12 809 1494没有注册 WhatsApp。」，而认这句话的正则写的
是 `invalid|not.*valid|isn't on whatsapp|无效` —— 一个都不匹配。于是 docs/59「记住没有
WhatsApp 的号码」从上线到 09-04 一次都没生效过：库里 1318 家空白、2 家 active、
**0 家 none**，同一批死号码每天重排、每天再弹一次同一个框。
"""
import re

import pytest

from app import channel_outreach
from app.playwright_engine import PlaywrightEngine as E


# Allen 09-04 截图上的原文，一个字没改。
REAL_DIALOG = "电话号码+27 12 809 1494没有注册 WhatsApp。"


@pytest.mark.parametrize("text", [
    REAL_DIALOG,
    "电话号码 +8613800138000 没有注册 WhatsApp。",
    "该电话号码未注册 WhatsApp",
    "Phone number +27 12 809 1494 is not on WhatsApp.",
    "The phone number you entered isn't on WhatsApp.",
    "This phone number is not registered on WhatsApp.",
    "Le numéro n'est pas sur WhatsApp",
])
def test_the_platform_saying_no_is_recognised(text):
    assert E.says_not_on_whatsapp(text) is True


@pytest.mark.parametrize("text", [
    # 我们自己的正文 —— `?text=` 已经把它预填进输入框，整页搜索会看见它。
    "Hi, we manufacture LED panels for event and rental work — stage, touring.",
    "Saw the P2 video wall on your site. Worth a conversation?",
    # 只有否定词、没提 WhatsApp：可能是客户页面上的任何一句话
    "That address is not valid anymore",
    "无效的优惠码",
    # 只提 WhatsApp、没有否定：比如对方主页写着「WhatsApp us」
    "WhatsApp us on +1 555 0100",
])
def test_our_own_words_are_never_read_as_a_refusal(text):
    assert E.says_not_on_whatsapp(text) is False


def test_both_halves_are_required():
    """两个条件缺一不可 —— 少一个就会把好号码永久标死（docs/104 R1）。"""
    assert E.says_not_on_whatsapp("没有注册") is False
    assert E.says_not_on_whatsapp("WhatsApp") is False
    assert E.says_not_on_whatsapp("没有注册 WhatsApp") is True


def test_the_error_it_raises_is_the_one_that_gets_remembered():
    """两条正则各自独立地漏掉了同一句话。现在引擎只负责抛一个固定串（docs/104 R4）。"""
    assert channel_outreach._NOT_ON_WHATSAPP.search(E.NOT_ON_WHATSAPP_ERROR)


def test_a_dead_number_is_written_down(tmp_path):
    """docs/59 的那条规则，第一次真的生效。"""
    from app.db import connect, init_schema

    conn = connect(str(tmp_path / "t.db"))
    init_schema(conn)
    conn.execute("INSERT INTO leads(no, company_en, phone) VALUES (1,'X','+27128091494')")
    conn.commit()
    channel_outreach._note_whatsapp_result(conn, 1, "whatsapp", E.NOT_ON_WHATSAPP_ERROR)
    assert conn.execute("SELECT whatsapp_status FROM leads WHERE no=1").fetchone()[0] == "none"


def test_a_browser_failure_is_not_the_number_s_fault(tmp_path):
    """docs/59 R1 不变：超时、context 死掉是我们这一轮的事实，不是这个号码的。"""
    from app.db import connect, init_schema

    conn = connect(str(tmp_path / "t.db"))
    init_schema(conn)
    conn.execute("INSERT INTO leads(no, company_en, phone) VALUES (1,'X','+27128091494')")
    conn.commit()
    channel_outreach._note_whatsapp_result(
        conn, 1, "whatsapp", "Target page, context or browser has been closed")
    assert conn.execute("SELECT whatsapp_status FROM leads WHERE no=1").fetchone()[0] is None


def test_the_wait_for_a_composer_that_will_never_come_is_short():
    """认不出新写法时，也不该花 45 秒等一个不会出现的输入框（docs/104 R3）。"""
    import inspect

    source = inspect.getsource(E._send_op)
    whatsapp_part = source.split("if channel == \"instagram\"")[0]
    assert "timeout=45000" not in whatsapp_part
    assert "timeout=20000" in whatsapp_part
