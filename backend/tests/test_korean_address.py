# -*- coding: utf-8 -*-
"""韩语信只称呼职位，不称呼名字（docs/96）。

Allen 09-03：「윤주영，不能说 안녕하세요, 윤주영님。一定要知道对方职位的情况下才加上
对方的职位……如果不知道对方的职位的情况下就算知道对方的名字也不要称呼对方的名称，
直接说 안녕하세요。」
"""
import pytest

from app import personalize

KO = "안녕하세요, {contact}님."


@pytest.mark.parametrize("title,expected", [
    ("대표", "안녕하세요, 대표님."),
    ("대표이사", "안녕하세요, 대표님."),      # 名片印 대표이사，当面叫 대표님
    ("CEO", "안녕하세요, 대표님."),           # 韩国一人公司老板的名片就是 대표
    ("President", "안녕하세요, 대표님."),
    ("과장", "안녕하세요, 과장님."),
    ("차장", "안녕하세요, 차장님."),
    ("이사", "안녕하세요, 이사님."),
    ("상무", "안녕하세요, 상무님."),
    ("대리", "안녕하세요, 대리님."),
    ("부장", "안녕하세요, 부장님."),
])
def test_a_known_title_is_the_address(title, expected):
    assert personalize.render(KO, {"contact_name": "윤주영", "title": title}) == expected


def test_a_name_without_a_title_is_never_spoken(_conn=None):
    """知道名字也不叫 —— 直接 안녕하세요."""
    assert personalize.render(KO, {"contact_name": "윤주영"}) == "안녕하세요."
    assert personalize.render(KO, {"contact_name": "김종수 (Kim Jong-su)"}) == "안녕하세요."


@pytest.mark.parametrize("title", ["Director", "Manager", "International Sales",
                                   "Exhibition Contact", "Sales Engineer"])
def test_an_english_title_that_does_not_map_to_a_rank_is_dropped(title):
    """부장 和 과장 差两级。从一个笼统的英文头衔猜哪一级，猜错比不称呼更糟。"""
    assert personalize.render(KO, {"contact_name": "윤주영", "title": title}) == "안녕하세요."


def test_the_title_inside_a_name_still_counts():
    """库里存的是「이종윤 부장」这种 —— 职位就在名字里。"""
    assert personalize.render(KO, {"contact_name": "이종윤 부장"}) == "안녕하세요, 부장님."


def test_english_letters_still_greet_by_first_name():
    """这条规矩只管韩语抬头。英文信里叫名字是正常的。"""
    assert personalize.render("Hi {contact},", {"contact_name": "Michael Wiener"}) == "Hi Michael,"
    assert personalize.render("Hi {contact},", {"contact_name": "김종수", "title": "CEO"}) == "Hi 김종수,"
