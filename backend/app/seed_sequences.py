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
# Style is borrowed, product claims are not. An earlier version lifted a series name and
# cabinet dimensions straight out of his June 2025 emails; Allen's correction:
# 不要写一模一样的邮件，只是叫你参考一下写作的风格…你毕竟不熟悉我的产品线，所以不用具体到
# 哪个产品之类的。He is right — a series can be renamed or discontinued and I would not
# know. Every pitch, brightness and cabinet type below is a row in `products` with
# agent_approved=1, which is the only product claim this file is allowed to make.
# docs/82 R7, R8, R9. Three corrections from Allen after reading the first version:
#
#   邮件主题永远不要出现公司名…不然别人一看你的名字就不会看了。直接从名字就能够判断出
#   这个邮件值不值得看。
#   不要老是强调自己是 Maxcolor，如果能不提的话也可以不提。
#   {fit} 这句话写的也很不好，都是废话。
#
# So: no company name in the subject at all — not ours, which is unknown and gets the
# letter deleted, and not theirs, which reads as mail merge. The subject has to earn the
# open on its own content, the way his do (전후면 유지보수 OK! R3 렌탈형 제품 만나보세요).
# {company} moves into the closing line, where it still satisfies `message_guard` without
# being the first thing they see. The brand appears once, in the signature.
#
# {fit} is gone entirely: "built for crews that reload every week, and sized to mix with
# stock you already own" is adjectives, and the specs above it already say the same thing
# in numbers.
#
# Every pitch and brightness is a row in `products` with agent_approved=1. Indoor is
# 600-800 nits, per Allen: 室内的亮度一般是 600~800，最高可到 1000，一般说 600~800 就可以了。
EN_OPENER = {
    "rental": ("rental LED specs", """Hi {contact},

{hook}

I'm Allen, handling export sales for an LED display manufacturer in Shenzhen.

For rental fleets, we cover P2.6-P3.9 indoor at 600-800 nits and P3.9-P4.8 outdoor at
4,500-5,500 nits, with die-cast cabinets and front/rear service.

Would a cabinet sheet with weight, power and service access be useful to {company}?
"""),
    "install": ("fixed-install LED specs", """Hi {contact},

{hook}

I'm Allen, handling export sales for an LED display manufacturer in Shenzhen.

For fixed installation, we cover P2-P3 indoor at 600-800 nits and P4-P10 outdoor at
5,500-8,000 nits, with front or rear service.

Would a drawing-ready sheet with cabinet weight, power and service clearance be useful
to {company}?
"""),
    "outdoor": ("outdoor LED specs", """Hi {contact},

{hook}

I'm Allen, handling export sales for an LED display manufacturer in Shenzhen.

Our outdoor fixed range is P4-P10 at 5,500-8,000 nits, with front or rear service.

Would a pitch and brightness chart by viewing distance be useful to {company}?
"""),
    "general": ("LED panel range", """Hi {contact},

{hook}

I'm Allen, handling export sales for an LED display manufacturer in Shenzhen.

Indoor P2-P3 at 600-800 nits, rental P2.6-P4.8 die-cast, outdoor P4-P10 at 5,500-8,000
nits, and fine pitch down to P0.7 for control rooms and studios.

Would a one-page spec comparison of those four ranges be useful to {company}?
"""),
}

EN_SECOND = {
    "rental": "For an easier cabinet comparison, our sheet can put dimensions, mounting,\n"
              "maximum and average power, and front/rear service on one page.\n\n"
              "Would that format be useful to {company}?",
    "install": "For fixed-install drawings, we can provide cabinet dimensions and weight,\n"
               "maximum and average power, and service clearance in one table.\n\n"
               "Would a drawing-ready version be useful to {company}?",
    "outdoor": "For outdoor selection, our comparison lines up viewing distance, pitch,\n"
               "5,500-8,000 nits brightness, and front/rear service options.\n\n"
               "Would that be useful for an early site review at {company}?",
    "general": "To make the range easier to compare, we can put fine pitch, indoor\n"
               "commercial, rental and outdoor options on one page, with brightness,\n"
               "weight and power fields.\n\nWould that overview be useful to {company}?",
}

# --- Korean ------------------------------------------------------------------------

# docs/82 R2. 学的是他 2025-06 那批韩语信的写法，不是内容：先报工厂和自己，再摆能力范围
# 和参数，最后邀请。「안녕하세요~ 심천 LED 전광판 업체 맥스컬러입니다 … 관심하신 제품
# 있으시면 연락주세요~」——具体到某个系列的产品声明不抄，那是他的产线，不是我的。
KO_OPENER = {
    "rental": ("렌탈 LED 사양", """안녕하세요, {contact}님.

{hook_ko}

저는 선전의 LED 디스플레이 제조업체에서 해외영업을 담당하는 Allen입니다.

렌탈용은 실내 P2.6-P3.9(600-800 nits), 실외 P3.9-P4.8(4,500-5,500 nits)의
다이캐스팅 캐비닛을 공급하며 전면·후면 유지보수가 가능합니다.

캐비닛 무게, 소비전력, 유지보수 방식을 정리한 사양서가 {company} 검토에 도움이 될까요?
"""),
    "install": ("고정형 LED 사양", """안녕하세요, {contact}님.

{hook_ko}

저는 선전의 LED 디스플레이 제조업체에서 해외영업을 담당하는 Allen입니다.

고정 설치용은 실내 P2-P3(600-800 nits), 실외 P4-P10(5,500-8,000 nits)이며
전면·후면 유지보수가 가능합니다.

캐비닛 무게, 소비전력, 유지보수 공간을 정리한 도면용 사양서가 {company}에 도움이 될까요?
"""),
    "outdoor": ("실외 LED 사양", """안녕하세요, {contact}님.

{hook_ko}

저는 선전의 LED 디스플레이 제조업체에서 해외영업을 담당하는 Allen입니다.

실외 고정형은 P4-P10, 5,500-8,000 nits이며 전면·후면 유지보수가 가능합니다.

시청 거리별 피치와 밝기 비교표가 {company}의 실외 프로젝트 검토에 도움이 될까요?
"""),
    "general": ("LED 패널 사양", """안녕하세요, {contact}님.

{hook_ko}

저는 선전의 LED 디스플레이 제조업체에서 해외영업을 담당하는 Allen입니다.

실내 P2-P3(600-800 nits), 렌탈 P2.6-P4.8 다이캐스팅, 실외 P4-P10(5,500-8,000 nits),
그리고 관제실·스튜디오용 P0.7부터의 미세 피치까지 가능합니다.

네 가지 제품군을 한눈에 볼 수 있는 비교표가 {company} 검토에 도움이 될까요?
"""),
}

KO_SECOND = {
    "rental": "렌탈 캐비닛 비교가 쉽도록 크기, 설치 방식, 최대·평균 소비전력, 전후면\n"
              "유지보수를 한 페이지에 정리할 수 있습니다.\n\n"
              "이 형식의 비교표가 {company}에 도움이 될까요?",
    "install": "고정 설치 도면에 필요한 캐비닛 크기와 무게, 최대·평균 소비전력,\n"
               "유지보수 공간을 표 하나로 정리할 수 있습니다.\n\n"
               "도면용 사양서가 {company}에 도움이 될까요?",
    "outdoor": "실외 제품을 검토할 때 필요한 시청 거리, 피치, 5,500-8,000 nits 밝기,\n"
               "전후면 유지보수 옵션을 한 표에서 비교할 수 있습니다.\n\n"
               "이 비교표가 {company}의 초기 현장 검토에 도움이 될까요?",
    "general": "미세 피치, 실내 상업용, 렌탈, 실외 제품의 밝기, 무게, 소비전력을\n"
               "한 페이지에서 비교할 수 있습니다.\n\n"
               "이 제품군 비교표가 {company}에 도움이 될까요?",
}

# The third letter is the same for everyone (docs/76 R2). It spends its one turn giving
# away the whole range, with no price in it: pricing stays Allen's (message_guard).
EN_LAST = """Hi {contact},

A compact reference for {company}: fine pitch from P0.7 for control rooms and studios,
P2-P3 indoor commercial at 600-800 nits, P2.6-P4.8 die-cast rental, and P4-P10 outdoor
at 5,500-8,000 nits.

Would the one-page range comparison be useful to keep with your supplier files?
"""

KO_LAST = """안녕하세요, {contact}님.

{company}에서 참고하실 수 있도록 제품 범위를 간단히 정리드립니다. 관제실·스튜디오용
P0.7부터의 미세 피치, 실내 상업용 P2-P3(600-800 nits),
렌탈용 P2.6-P4.8 다이캐스팅, 실외 P4-P10(5,500-8,000 nits)까지 가능합니다.

한 페이지로 정리한 제품군 비교표를 공급업체 자료로 보관하시면 도움이 될까요?
"""

# docs/75 R1: the schedule may never outrun the two-week frequency rule.
OFFSETS = (0, 14, 28)


def name_for(segment: str, korean: bool) -> str:
    return f"冷邮件 3 步跟进（{'韩语' if korean else '英语'}·{LABEL[segment]}）"


def steps_for(segment: str, korean: bool) -> list[tuple]:
    if korean:
        opener, second, last, sign = KO_OPENER, KO_SECOND, KO_LAST, KO_SIGN
        greeting = "안녕하세요, {contact}님.\n\n"
    else:
        opener, second, last, sign = EN_OPENER, EN_SECOND, EN_LAST, EN_SIGN
        greeting = "Hi {contact},\n\n"
    subject, body = opener[segment]
    follow = f"Re: {subject}"
    return [
        (0, OFFSETS[0], subject, body + "\n" + sign),
        (1, OFFSETS[1], follow, greeting + second[segment] + "\n\n" + sign),
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
