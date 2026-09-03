# -*- coding: utf-8 -*-
"""开场白必须引用客户自己的话，引不出就退回通用的那句（docs/93）。"""
import pytest

from app import hook_writer, personalize, refresh_hooks
from app.agent import llm

PAGE = (
    "Projects\n"
    "In 2025 we supplied and installed the main scoreboard at Estadio Nacional, "
    "a 96 sqm outdoor screen running around the clock.\n"
    "Contact us for a quote.\n"
)
PAGE_KO = (
    "시공 사례\n"
    "2025년 잠실 실내체육관 메인 스크린 시공을 맡았습니다. 실내 P2.5, 총 88제곱미터입니다.\n"
    "문의하기\n"
)


def _lead(conn, no=10, country="USA", hook="Saw the rental work on your site."):
    conn.execute("INSERT INTO leads(no, company_en, country, website, hook) VALUES (?,?,?,?,?)",
                 (no, "Vista AV", country, "vista.com", hook))
    conn.commit()
    return dict(conn.execute("SELECT * FROM leads WHERE no=?", (no,)).fetchone())


def _answer(monkeypatch, payload):
    monkeypatch.setattr(llm, "complete_json", lambda *a, **k: payload)


# R1 ─ 引文对不上就整条作废
def test_a_quote_that_is_not_on_the_page_is_refused(conn, monkeypatch):
    lead = _lead(conn)
    _answer(monkeypatch, {"hook": "Saw the arena screen you built in Lisbon.",
                          "quote": "we built the arena screen in Lisbon",   # 页面上没有
                          "source_url": "https://vista.com/projects"})
    assert hook_writer.improve(conn, lead, PAGE, "https://vista.com/projects") is None
    row = conn.execute("SELECT hook, hook_quote FROM leads WHERE no=10").fetchone()
    assert row["hook"] == "Saw the rental work on your site."
    assert not row["hook_quote"]


# R4 ─ 开场白是一件事实，不是一句夸奖
def test_a_compliment_is_refused(conn, monkeypatch):
    lead = _lead(conn)
    _answer(monkeypatch, {"hook": "You are a leading installer of stadium screens.",
                          "quote": "we supplied and installed the main scoreboard",
                          "source_url": "https://vista.com/projects"})
    assert hook_writer.improve(conn, lead, PAGE, "https://vista.com/projects") is None
    assert conn.execute("SELECT hook FROM leads WHERE no=10").fetchone()["hook"] \
        == "Saw the rental work on your site."


# R1 + R5 ─ 成功时把出处一起写下来
def test_a_verified_quote_is_stored_with_its_source(conn, monkeypatch):
    lead = _lead(conn)
    _answer(monkeypatch, {"hook": "Saw the scoreboard you installed at Estadio Nacional.",
                          "quote": "we supplied and installed the main scoreboard at Estadio Nacional",
                          "source_url": "https://vista.com/projects"})
    out = hook_writer.improve(conn, lead, PAGE, "https://vista.com/projects")
    assert out and out["hook"].startswith("Saw the scoreboard")
    row = conn.execute("SELECT hook, hook_quote, hook_source_url, hook_at FROM leads WHERE no=10").fetchone()
    assert row["hook"] == "Saw the scoreboard you installed at Estadio Nacional."
    assert "main scoreboard" in row["hook_quote"]
    assert row["hook_source_url"] == "https://vista.com/projects"
    assert row["hook_at"]


# R3 ─ 韩语开场白由模型直接写，不再过词表
def test_a_korean_lead_gets_a_korean_hook_that_the_gloss_table_could_not_produce(conn, monkeypatch):
    lead = _lead(conn, no=11, country="South Korea")
    _answer(monkeypatch, {"hook": "Saw the indoor screen you built at Jamsil Arena.",
                          "hook_ko": "잠실 실내체육관 메인 스크린 시공 사례를 봤습니다.",
                          "quote": "잠실 실내체육관 메인 스크린 시공을 맡았습니다",
                          "source_url": "https://vista.com/ko/projects"})
    assert hook_writer.improve(conn, lead, PAGE_KO, "https://vista.com/ko/projects")
    row = dict(conn.execute("SELECT * FROM leads WHERE no=11").fetchone())
    assert row["hook_ko"] == "잠실 실내체육관 메인 스크린 시공 사례를 봤습니다."
    # 词表通道对这句英文会返回空；存下来的韩语句子必须赢过它
    assert personalize.hook_ko(row) == "잠실 실내체육관 메인 스크린 시공 사례를 봤습니다."


# R2 ─ 模型不可用不能让今天少发一封信
@pytest.mark.parametrize("boom", [
    llm.LLMUnavailable("缺少 backend/deepseek_key.txt"),
    llm.LLMError("timeout"),
    ValueError("bad json"),
])
def test_a_model_that_fails_leaves_the_letter_alone(conn, monkeypatch, boom):
    lead = _lead(conn)
    def raise_it(*a, **k):
        raise boom
    monkeypatch.setattr(llm, "complete_json", raise_it)
    assert hook_writer.improve(conn, lead, PAGE, "https://vista.com/projects") is None
    assert conn.execute("SELECT hook FROM leads WHERE no=10").fetchone()["hook"] \
        == "Saw the rental work on your site."


# R5 ─ 带出处的开场白不被塌陷改写器碰
def test_refresh_hooks_leaves_a_sourced_hook_alone(conn):
    hook_writer.ensure_schema(conn)
    for no in (20, 21):
        conn.execute("INSERT INTO leads(no, company_en, city, hook, brief) VALUES (?,?,?,?,?)",
                     (no, f"Co{no}", "Austin", "Saw the rental work on your site.",
                      "rental; signage"))
    conn.execute("UPDATE leads SET hook_quote='we supplied the arena screen' WHERE no=20")
    conn.commit()
    changed = {row["no"] for row in refresh_hooks.collisions(conn)}
    assert 20 not in changed and 21 in changed


# 试跑抓到的三个真实失败形状（09-03，didmonitor.com / foreal.kr）
def test_the_quote_pasted_back_is_not_a_hook(conn, monkeypatch):
    lead = _lead(conn)
    _answer(monkeypatch, {"hook": "we supplied and installed the main scoreboard.",
                          "quote": "we supplied and installed the main scoreboard at Estadio Nacional",
                          "source_url": "https://vista.com/projects"})
    assert hook_writer.improve(conn, lead, PAGE, "https://vista.com/projects") is None


def test_a_label_is_not_a_sentence(conn, monkeypatch):
    lead = _lead(conn)
    _answer(monkeypatch, {"hook": "Samsung official B2B dealer : Comolab (1466869)",
                          "quote": "we supplied and installed the main scoreboard",
                          "source_url": "https://vista.com/projects"})
    assert hook_writer.improve(conn, lead, PAGE, "https://vista.com/projects") is None


def test_the_english_slot_will_not_take_a_korean_sentence(conn, monkeypatch):
    """英文信用的是 hook 这一档。它落进去是韩文，整封英文信就断在第二行。"""
    lead = _lead(conn, no=12, country="South Korea")
    _answer(monkeypatch, {"hook": "잠실 실내체육관 시공 사례를 봤습니다.",
                          "hook_ko": "잠실 실내체육관 시공 사례를 봤습니다.",
                          "quote": "잠실 실내체육관 메인 스크린 시공을 맡았습니다",
                          "source_url": "https://vista.com/ko"})
    assert hook_writer.improve(conn, lead, PAGE_KO, "https://vista.com/ko") is None
    assert conn.execute("SELECT hook FROM leads WHERE no=12").fetchone()["hook"] \
        == "Saw the rental work on your site."


def test_a_quote_the_page_prints_in_bold_still_counts(conn, monkeypatch):
    """jina 交回的是 markdown。**加粗**的那一行，人眼和模型看到的都是没有星号的版本。"""
    page = "/ About the project\n\n**CMS 구축 및 운영 유지보수**\n\n**(현재 3,300여개)**\n\n/ client\n"
    assert hook_writer.quoted_from("CMS 구축 및 운영 유지보수 (현재 3,300여개)", page)


def test_a_bare_proper_noun_is_not_evidence(conn):
    """'예술의전당' 在页面上出现 6 次，但一个地名不承载「这是他们做的」这个断言。"""
    assert not hook_writer.quoted_from("예술의전당", "예술의전당 협력사 안내 예술의전당")
