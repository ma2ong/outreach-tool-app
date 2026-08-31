"""One cold sequence per customer segment, per language (docs/76).

Allen: "文案不要一模一样，针对不同的客户可以多几个版本，不要全部客户都一样。"

This replaces the single letter everyone used to get. It is not the angle machinery
coming back — angles switched on failure, chosen by the system; a segment is chosen
before the first letter, from what the company is, and never changes because a number
looked bad.

Where the differentiation goes (docs/76 R2): the opener is written per segment, the
second letter carries one line that belongs to that segment, and the third is shared.
By the third letter it no longer matters whether they rent or install — differences cost
something to maintain, so they are spent where they change whether the letter is read.

Every opener names products, and every pitch in it is a row in the product library
(docs/76 R4): P0.7-P1.8, P2-P3, P2.6-P3.9, P3.9-P4.8, P4-P10.

Run:  python -m app.seed_sequences            # preview
      python -m app.seed_sequences --apply
"""
from __future__ import annotations

import sys

from app.copy_segments import LABEL, SEGMENTS
from app.db import connect

EN_SIGN = """Allen Ma · Shenzhen Maxcolor Visual
WhatsApp/WeChat +86 135-7087-1001"""

KO_SIGN = """Allen Ma · Shenzhen Maxcolor Visual
Kakaotalk / WeChat +86 13570871001"""

# --- English -----------------------------------------------------------------------

# docs/82 R2. Allen's own order, taken from 3,031 letters he wrote himself: name the
# factory and yourself, put a specific product with its numbers in front of them, then
# invite a reply with something deliverable the same day. His Korean subject lines are
# the same shape — 전후면 유지보수 OK! R3 렌탈형 제품 만나보세요 — a product plus its hardest
# spec, never a question about the reader.
#
# The subject keeps {company} in front of the product. Allen's own subjects do not — but
# his went out one at a time by hand, while this path is judged by `message_guard`, and
# the company name in the subject is the whole reason an automated letter reads as
# addressed to someone. Drop it and every Korean sequence is blocked before sending.
#
# Every pitch and brightness below is a row in `products` with agent_approved=1. The R3
# name and the 500x500 / 500x1000mm cabinets come from his own June 2025 emails, where
# he sent them seven times in one week.
EN_OPENER = {
    "rental": ("{company} — Maxcolor R3 rental, P2.6-P4.8 die-cast 500x500", """Hi {contact},

{hook}

This is Allen from Shenzhen Maxcolor — we build the panels ourselves, {fit}.

Our R3 rental series runs P2.6-P3.9 indoor at 1,000-1,200 nits and P3.9-P4.8 outdoor at
4,500-5,500 nits. Die-cast cabinets, 500x500 and 500x1000mm, front and rear service.

Tell me the pitch and cabinet size you work with and I'll send the spec sheet the same
day — weight, power draw and the cabinet drawing.
"""),
    "install": ("{company} — P2-P3 indoor, P4-P10 outdoor, from our own factory", """Hi {contact},

{hook}

This is Allen from Shenzhen Maxcolor — we build the panels ourselves, {fit}.

For fixed work we run P2-P3 indoor at 800-1,200 nits and P4-P10 outdoor at
5,500-8,000 nits, front or rear service.

Tell me the size you're speccing and I'll send the sheet the same day — weight and power
per cabinet, so it drops straight into your drawing.
"""),
    "outdoor": ("{company} — outdoor P4-P10, 5,500-8,000 nits, front-serviceable", """Hi {contact},

{hook}

This is Allen from Shenzhen Maxcolor — we build outdoor LED ourselves, {fit}.

P4-P10 at 5,500-8,000 nits, front-serviceable, built to run all day in daylight.

Tell me the screen size and the viewing distance and I'll send the spec sheet for that
pitch the same day.
"""),
    "general": ("{company} — LED panels direct from the Maxcolor factory", """Hi {contact},

{hook}

This is Allen from Shenzhen Maxcolor — we build the panels ourselves, {fit}.

Indoor P2-P3 at 800-1,200 nits, rental P2.6-P4.8 die-cast, outdoor P4-P10 at
5,500-8,000 nits, and fine pitch down to P0.7 for control rooms and studios.

Tell me the pitch and size you work with and I'll send the matching spec sheet the same
day.
"""),
}

# One line from them, one useful thing back. Never a line about whether we deserve their
# attention — docs/82 R1 bans that shape too.
EN_SECOND = {
    "rental": "The cabinet brand you run is enough — I'll come back the same day\nwith whether ours mix with your stock, and the cabinet drawing if they do.",
    "install": "A rough size and pitch is enough — I'll come back with the sheet for\nthat spec, weight and power per cabinet included.",
    "outdoor": "The screen size is enough — I'll come back with the pitch and the\nbrightness that suits that viewing distance.",
    "general": "The pitch you run now is enough — I'll come back with the matching\nspec sheet the same day.",
}

# --- Korean ------------------------------------------------------------------------

# docs/82 R2. 他自己 2025-06 那批韩语信的原样：先报工厂，再摆一个具体系列和它的参数，
# 最后邀请。「안녕하세요~ 심천 LED 전광판 업체 맥스컬러입니다 … 관심하신 제품 있으시면 연락주세요~」
KO_OPENER = {
    "rental": ("{company} — 맥스컬러 R3 렌탈, P2.6-P4.8 다이캐스팅 500x500", """안녕하세요, {contact}님.

{hook_ko}

저는 심천 LED 전광판 업체 맥스컬러의 Allen 마이용입니다 — {fit_ko}. 저희는 자체 공장에서
패널을 직접 만듭니다.

최신 R3 렌탈 시리즈는 실내 P2.6-P3.9(1,000-1,200 nits), 실외 P3.9-P4.8(4,500-5,500 nits)
입니다. 다이캐스팅 캐비닛 500x500 / 500x1000mm, 전면·후면 유지보수 모두 됩니다.

쓰시는 피치와 캐비닛 크기만 알려주시면 당일에 사양서 보내드리겠습니다 — 무게, 소비전력,
캐비닛 도면까지 함께요.
"""),
    "install": ("{company} — 시공용 실내 P2-P3 / 실외 P4-P10, 자체 공장", """안녕하세요, {contact}님.

{hook_ko}

저는 심천 LED 전광판 업체 맥스컬러의 Allen 마이용입니다 — {fit_ko}. 저희는 자체 공장에서
패널을 직접 만듭니다.

고정 설치는 실내 P2-P3(800-1,200 nits), 실외 P4-P10(5,500-8,000 nits), 전면·후면
유지보수 모두 가능합니다.

다음 건 크기만 알려주시면 당일에 사양서 보내드리겠습니다 — 캐비닛별 무게와 소비전력까지
들어가서 도면에 그대로 넣으실 수 있습니다.
"""),
    "outdoor": ("{company} — 실외 P4-P10, 5,500-8,000 nits, 전면 유지보수", """안녕하세요, {contact}님.

{hook_ko}

저는 심천 LED 전광판 업체 맥스컬러의 Allen 마이용입니다 — {fit_ko}. 실외 LED를 자체
공장에서 직접 만듭니다.

P4-P10, 5,500-8,000 nits, 전면 유지보수 가능하고 주간 야외 상시 가동을 전제로 만듭니다.

화면 크기와 시청 거리만 알려주시면 해당 피치 사양서를 당일에 보내드리겠습니다.
"""),
    "general": ("{company} — 맥스컬러 자체 공장에서 만드는 LED 패널", """안녕하세요, {contact}님.

{hook_ko}

저는 심천 LED 전광판 업체 맥스컬러의 Allen 마이용입니다 — {fit_ko}. 저희는 자체 공장에서
패널을 직접 만듭니다.

실내 P2-P3(800-1,200 nits), 렌탈 P2.6-P4.8 다이캐스팅, 실외 P4-P10(5,500-8,000 nits),
그리고 관제실·스튜디오용 P0.7부터의 미세 피치까지 다 됩니다.

쓰시는 피치와 크기만 알려주시면 해당 사양서를 당일에 보내드리겠습니다.
"""),
}

KO_SECOND = {
    "rental": "쓰시는 캐비닛 브랜드만 알려주셔도 됩니다. 기존 장비와 맞는지 당일에 확인해서 "
               "맞으면 캐비닛 도면까지 같이 보내드리겠습니다.",
    "install": "대략적인 크기와 피치만으로도 충분합니다. 해당 사양의 사양서를 무게·소비전력까지 "
               "넣어 보내드리겠습니다.",
    "outdoor": "화면 크기만 알려주셔도 됩니다. 그 시청 거리에 맞는 피치와 밝기를 정리해서 "
               "보내드리겠습니다.",
    "general": "지금 쓰시는 피치만 알려주셔도 충분합니다. 맞는 사양서를 당일에 보내드리겠습니다.",
}

# The third letter is the same for everyone (docs/76 R2). It used to be a goodbye —
# "Last note. If panels aren't on your plan, that's a fine answer." — which is exactly
# the shape docs/82 bans. It now spends its one turn giving away the whole range and a
# same-day promise, with no price in it: pricing stays Allen's (message_guard).
EN_LAST = """Hi {contact},

One more from me, with the whole range in it: fine pitch from P0.7 for control rooms and
studios, P2-P3 indoor commercial, P2.6-P4.8 die-cast rental, and P4-P10 outdoor at
5,500-8,000 nits. All of it built in our own factory in Shenzhen.

Send me a size and a pitch whenever a job comes up and you will have the spec sheet and
a quote the same day.
"""

KO_LAST = """안녕하세요, {contact}님.

저희가 만드는 전 범위를 한 번에 정리해 드립니다. 관제실·스튜디오용 P0.7부터의 미세 피치,
실내 상업용 P2-P3, 렌탈용 P2.6-P4.8 다이캐스팅, 실외 P4-P10(5,500-8,000 nits) —
전부 심천 자체 공장에서 만듭니다.

프로젝트가 생기시면 크기와 피치만 주세요. 당일에 사양서와 견적 함께 드리겠습니다.
"""

EN_HANDOFF = "\n\nNot your area? Point me at whoever handles displays and I'll send them the specs directly.\n\n"
KO_HANDOFF = "\n\n담당이 아니시면 디스플레이 담당자분만 알려주세요. 제가 직접 사양서 보내드리겠습니다.\n\n"

# docs/75 R1: the schedule may never outrun the two-week frequency rule.
OFFSETS = (0, 14, 28)


def name_for(segment: str, korean: bool) -> str:
    return f"冷邮件 3 步跟进（{'韩语' if korean else '英语'}·{LABEL[segment]}）"


def steps_for(segment: str, korean: bool) -> list[tuple]:
    if korean:
        opener, second, last, sign = KO_OPENER, KO_SECOND, KO_LAST, KO_SIGN
        greeting, handoff = "안녕하세요, {contact}님.\n\n", KO_HANDOFF
    else:
        opener, second, last, sign = EN_OPENER, EN_SECOND, EN_LAST, EN_SIGN
        greeting, handoff = "Hi {contact},\n\n", EN_HANDOFF
    subject, body = opener[segment]
    follow = f"Re: {subject}"
    return [
        (0, OFFSETS[0], subject, body + "\n" + sign),
        (1, OFFSETS[1], follow, greeting + second[segment] + handoff + sign),
        (2, OFFSETS[2], follow, last + "\n" + sign),
    ]


def seed(conn, name: str, steps) -> int:
    row = conn.execute("SELECT id FROM sequences WHERE name=?", (name,)).fetchone()
    if row:
        seq_id = row["id"]
        conn.execute("DELETE FROM sequence_steps WHERE sequence_id=?", (seq_id,))
    else:
        seq_id = conn.execute(
            "INSERT INTO sequences(name, channel) VALUES (?, 'email')", (name,)).lastrowid
    for order, offset, subject, body in steps:
        conn.execute(
            "INSERT INTO sequence_steps(sequence_id, step_order, day_offset, subject, body)"
            " VALUES (?,?,?,?,?)", (seq_id, order, offset, subject, body))
    return seq_id


def seed_all(conn) -> dict[tuple[str, bool], int]:
    """Every segment in both languages; returns {(segment, korean): sequence_id}."""
    out = {}
    for korean in (False, True):
        for segment in SEGMENTS:
            out[(segment, korean)] = seed(
                conn, name_for(segment, korean), steps_for(segment, korean))
    conn.commit()
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    apply_changes = "--apply" in sys.argv
    with connect("outreach.db") as conn:
        from app import copy_segments
        counts = copy_segments.counts(conn)
        print("客户库分段：")
        for segment in SEGMENTS:
            print(f"  {segment:9} {LABEL[segment]:6} {counts[segment]:4} 家")
        print()
        for korean in (False, True):
            for segment in SEGMENTS:
                print(f"  {name_for(segment, korean):32} "
                      f"{steps_for(segment, korean)[0][2]}")
        if not apply_changes:
            print("\n确认没问题就加 --apply 写入")
            return
        made = seed_all(conn)
        print(f"\n已写入 {len(made)} 条序列")


if __name__ == "__main__":
    main()
