# -*- coding: utf-8 -*-
"""正则提名，模型判断谁是人（docs/101）。"""
import datetime as dt

from app import decision_maker_radar as radar
from app import people_detector
from app.agent import llm

PAGE = """## Our team

Dan Baird
Operations Manager
dbaird@gopce.com

Air Sanitizer
Technical Director

Nationwide Delivery
project manager
"""
PAGES = [{"url": "https://gopce.com/about", "text": PAGE}]


def _judge(monkeypatch, verdicts):
    monkeypatch.setattr(llm, "complete_json", lambda *a, **k: {"people": verdicts})


def _names(rows):
    return [r["name"] for r in rows]


def test_the_regex_still_finds_the_candidates(conn):
    """模型判断的是正则提出来的名单 —— 先确认名单里有什么。"""
    found = _names(people_detector.detect_pages(PAGES, "gopce.com"))
    assert "Dan Baird" in found


def test_an_obvious_non_person_never_reaches_the_model(conn, monkeypatch):
    """「Nationwide Delivery」被那张黑名单先挡掉，省下模型判错它的机会。"""
    asked = []
    monkeypatch.setattr(llm, "complete_json",
                        lambda c, task, system, user, **k: asked.append(user) or {"people": []})
    people_detector.detect_pages_with_model(conn, PAGES, "gopce.com")
    assert asked and "Nationwide Delivery" not in asked[0]


def test_the_model_drops_what_the_blocklist_could_not(conn, monkeypatch):
    """「Air Sanitizer」两段普通名词，正则挡不住，模型该认出它不是人。"""
    rows = [r for r in people_detector.detect_pages(PAGES, "gopce.com")
            if people_detector.judge_people]  # 名单本身
    rows = [r for r in rows if r["name"] in ("Dan Baird", "Air Sanitizer")]
    _judge(monkeypatch, [{"id": i, "is_person": r["name"] == "Dan Baird"}
                         for i, r in enumerate(rows)])
    kept = people_detector.judge_people(conn, rows)
    assert _names(kept) == ["Dan Baird"]


def test_a_row_the_model_forgot_to_answer_is_kept(conn, monkeypatch):
    """模型漏答一行，不该悄悄把这个人删掉 —— 没回答不是否定。"""
    rows = [{"name": "Dan Baird", "title": "Operations Manager"},
            {"name": "Tom Pappanduros", "title": "Production Manager"}]
    _judge(monkeypatch, [{"id": 0, "is_person": True}])
    assert _names(people_detector.judge_people(conn, rows)) == ["Dan Baird", "Tom Pappanduros"]


def test_an_unavailable_model_leaves_the_list_alone(conn, monkeypatch):
    """判不了就照旧 —— 少一个判断不是少一封信。"""
    def boom(*a, **k):
        raise llm.LLMUnavailable("no key")
    monkeypatch.setattr(llm, "complete_json", boom)
    rows = [{"name": "Dan Baird", "title": "Operations Manager"}]
    assert people_detector.judge_people(conn, rows) == rows


def test_a_company_whose_sequence_ended_is_still_worth_a_name(conn):
    """299 家发过信的公司因为「序列还在跑」这一条永远排不上队。"""
    conn.execute("UPDATE leads SET website='alpha.com', contact_name='' WHERE no=1")
    conn.execute("INSERT INTO send_log(lead_no, channel, campaign, sent_at, subject, body)"
                 " VALUES (1,'email','c','2026-08-01','s','b')")
    conn.commit()
    radar.ensure_schema(conn)
    rows = radar._cold_accounts_missing_authority(conn, dt.date(2026, 9, 4), set())
    assert 1 in {r["lead_no"] for r in rows}
