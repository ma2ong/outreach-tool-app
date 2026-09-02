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
(docs/76 R4): P0.7-P1.8, P2-P3, P2.6-P3.9, P3.9-P4.8, P2.5-P10.

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
# No company name anywhere — not in the subject, not in the body. Allen: 主题和正文都不能
# 出现对方的公司名 {company}，如果正文要说到对方的公司名时可以说，贵司或者你们公司来代替
# 即可. The bodies below never named them; the subjects led with it, and that lead is what
# reads as mail merge — 别人一看你的名字就不会看了.
#
# It costs something and the cost is known: `message_guard` counts the company name as a
# personalisation clue, so first letters held for being impersonal go from 88 to 383 of
# 1,008. Those 383 have no hook, no city and no site words in the letter — the name was
# the only thing tying the page to them, and a name in a subject line is exactly what he
# says gets it deleted. Giving them a hook is the fix; weakening the check is not.
#
# Style is borrowed, product claims are not. An earlier version lifted a series name and
# cabinet dimensions straight out of his June 2025 emails; Allen's correction:
# 不要写一模一样的邮件，只是叫你参考一下写作的风格…你毕竟不熟悉我的产品线，所以不用具体到
# 哪个产品之类的。He is right — a series can be renamed or discontinued and I would not
# know. Every pitch, brightness and cabinet type below is a row in `products` with
# agent_approved=1, which is the only product claim this file is allowed to make.
EN_OPENER = {
    "rental": ("rental LED panels, P2.6-P4.8 die-cast", """Hi {contact},

{hook}

This is Allen from Shenzhen Maxcolor Visual, an LED display manufacturer in Shenzhen. {fit}

For rental work we run P2.6-P3.9 indoor at 600-800 nits and P3.9-P4.8 outdoor at
4,500-5,500 nits, die-cast cabinets, front and rear service.

If any of this is close to what you use, I'd be glad to send the spec sheet — weight and
power per cabinet included. Just let me know which pitch, whenever it's convenient.
"""),
    "install": ("P2-P3 indoor, P2.5-P10 outdoor, front or rear service", """Hi {contact},

{hook}

This is Allen from Shenzhen Maxcolor, an LED display manufacturer in Shenzhen. {fit}

For fixed work we run P2-P3 indoor at 600-800 nits and P2.5-P10 outdoor at
5,500-8,000 nits, front or rear service.

If that's close to what you spec, I'd be glad to send the sheet — weight and power per
cabinet, ready to drop into a drawing. Happy to do it whenever it's useful.
"""),
    "outdoor": ("outdoor P2.5-P10, 5,500-8,000 nits, front-serviceable", """Hi {contact},

{hook}

This is Allen from Shenzhen Maxcolor Visual, an LED display manufacturer in Shenzhen. {fit}

P2.5-P10 at 5,500-8,000 nits, front-serviceable, built to run all day in daylight.

If something outdoor is in planning, I'd be glad to put together the specs for the pitch
that suits the viewing distance. No rush on my side.
"""),
    "general": ("Maxcolor LED panels — indoor, rental and outdoor", """Hi {contact},

{hook}

This is Allen from Shenzhen Maxcolor, an LED display manufacturer in Shenzhen. {fit}

Indoor P2-P3 at 600-800 nits, rental P2.6-P4.8 die-cast, outdoor P2.5-P10 at
5,500-8,000 nits, and fine pitch down to P0.7 for control rooms and studios.

If any of these are close to what you work with, I'd be glad to send the matching spec
sheet. Just let me know whenever it's convenient.
"""),
}

# One line from them, one useful thing back. Never a line about whether we deserve their
# attention — docs/82 R1 bans that shape too.
EN_SECOND = {
    "rental": "Happy to check whether our cabinets mix with the ones you run —\nthe brand is all it takes, whenever you have a moment.",
    "install": "Happy to put together the sheet for whatever spec you are looking\nat, weight and power per cabinet included — a rough size and pitch is all it takes.",
    "outdoor": "Happy to work out the pitch and brightness for a given screen size\nand viewing distance, if that is useful at some point.",
    "general": "Happy to send the spec sheet for whichever pitch you run — no rush\nat all on my side.",
}

# --- Korean ------------------------------------------------------------------------

# docs/82 R2. 学的是他 2025-06 那批韩语信的写法，不是内容：先报工厂和自己，再摆能力范围
# 和参数，最后邀请。「안녕하세요~ 심천 LED 전광판 업체 맥스컬러입니다 … 관심하신 제품
# 있으시면 연락주세요~」——具体到某个系列的产品声明不抄，那是他的产线，不是我的。
KO_OPENER = {
    "rental": ("렌탈용 LED 패널, P2.6-P4.8 다이캐스팅", """안녕하세요, {contact}님.

{hook_ko}

저는 심천 LED 디스플레이 제조업체 맥스컬러의 Allen 마이용입니다. {fit_ko}

렌탈용은 실내 P2.6-P3.9(600-800 nits), 실외 P3.9-P4.8(4,500-5,500 nits)이고,
다이캐스팅 캐비닛에 전면·후면 유지보수 모두 됩니다.

쓰시는 사양과 비슷하다면 사양서 기꺼이 보내드리겠습니다. 캐비닛별 무게와 소비전력까지
함께 정리해 드립니다. 편하실 때 말씀만 주세요.
"""),
    "install": ("시공용 실내 P2-P3 / 실외 P2.5-P10, 전후면 유지보수", """안녕하세요, {contact}님.

{hook_ko}

저는 심천 LED 전광판 업체 맥스컬러의 Allen 마이용입니다. {fit_ko}

고정 설치는 실내 P2-P3(600-800 nits), 실외 P2.5-P10(5,500-8,000 nits), 전면·후면
유지보수 모두 가능합니다.

검토하시는 사양과 비슷하다면 사양서 기꺼이 보내드리겠습니다. 캐비닛별 무게와 소비전력까지
들어가 도면에 그대로 넣으실 수 있습니다. 편하실 때 말씀만 주세요.
"""),
    "outdoor": ("실외 P2.5-P10, 5,500-8,000 nits, 전면 유지보수", """안녕하세요, {contact}님.

{hook_ko}

저는 심천 LED 디스플레이 제조업체 맥스컬러의 Allen 마이용입니다. {fit_ko}

P2.5-P10, 5,500-8,000 nits, 전면 유지보수 가능하고 주간 야외 상시 가동을 전제로 만듭니다.

실외 건 검토 중이시라면 시청 거리에 맞는 피치로 사양 정리해서 기꺼이 보내드리겠습니다.
급하지 않으니 편하실 때 말씀 주세요.
"""),
    "general": ("맥스컬러 LED 패널, 실내·렌탈·실외", """안녕하세요, {contact}님.

{hook_ko}

저는 심천 LED 전광판 업체 맥스컬러의 Allen 마이용입니다. {fit_ko}

실내 P2-P3(600-800 nits), 렌탈 P2.6-P4.8 다이캐스팅, 실외 P2.5-P10(5,500-8,000 nits),
그리고 관제실·스튜디오용 P0.7부터의 미세 피치까지 다 됩니다.

위 범위 중 쓰시는 것과 비슷한 게 있으면 해당 사양서 기꺼이 보내드리겠습니다.
편하실 때 편하게 말씀 주세요.
"""),
}

KO_SECOND = {
    "rental": "쓰시는 캐비닛 브랜드만 알려주셔도 됩니다. 기존 장비와 맞는지 당일에 확인해서 "
               "맞는지 알려드리고 해당 사양서를 보내드리겠습니다.",
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

A short summary of the whole range, in case it's useful to keep on file: fine pitch from
P0.7 for control rooms and studios, P2-P3 indoor commercial, P2.6-P4.8 die-cast rental, and P2.5-P10 outdoor at
5,500-8,000 nits. All of it made in Shenzhen.

Whenever a job comes up, I'd be glad to put the specs and a quote together for it —
same day, and no obligation either way.
"""

KO_LAST = """안녕하세요, {contact}님.

저희가 만드는 전 범위를 한 번에 정리해 드립니다. 관제실·스튜디오용 P0.7부터의 미세 피치,
실내 상업용 P2-P3, 렌탈용 P2.6-P4.8 다이캐스팅, 실외 P2.5-P10(5,500-8,000 nits) —
전부 심천에서 만듭니다.

나중에 프로젝트 생기시면 사양서와 견적 기꺼이 정리해 드리겠습니다. 편하실 때 언제든
말씀 주세요.
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


def close_orphaned_enrollments(conn) -> int:
    """Complete anyone waiting on a step that no longer exists.

    Deleting a follow-up letter shortens the sequence, and the due queue joins
    `sequence_steps` on `step_order = current_step` — so an enrollment parked past the
    new end stops matching and simply disappears from the queue while still reading as
    "active". It sends nothing and reports nothing, which is the one failure mode this
    book keeps producing. They have had every letter the sequence still contains, so
    completed is the truth.
    """
    cur = conn.execute(
        "UPDATE sequence_enrollments SET status='completed'"
        " WHERE status='active' AND NOT EXISTS ("
        "   SELECT 1 FROM sequence_steps st"
        "   WHERE st.sequence_id = sequence_enrollments.sequence_id"
        "     AND st.step_order = sequence_enrollments.current_step)")
    return cur.rowcount


def seed_all(conn) -> dict[tuple[str, bool], int]:
    """Every segment in both languages; returns {(segment, korean): sequence_id}."""
    out = {}
    for korean in (False, True):
        for segment in SEGMENTS:
            out[(segment, korean)] = seed(
                conn, name_for(segment, korean), steps_for(segment, korean))
    close_orphaned_enrollments(conn)
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
