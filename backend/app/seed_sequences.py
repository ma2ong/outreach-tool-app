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

EN_OPENER = {
    "rental": ("{company} — which cabinet are you running?", """Hi {contact},

{hook}

We build the panels in Shenzhen — {fit}. Rental here is P2.6-P4.8, die-cast, indoor and
outdoor.

What cabinet are you on now? If ours won't mix with your stock I'll say so and leave it
there.
"""),
    "install": ("{company} — panels for your next fixed install", """Hi {contact},

{hook}

We build the panels in Shenzhen — {fit}. For fixed work that's P2-P3 indoor and P4-P10
outdoor, front or rear service.

What are you speccing next? Tell me the size and I'll send the sheet with weight and
power, so it drops straight into your drawing.
"""),
    "outdoor": ("{company} — P4-P10 outdoor, 5,500-8,000 nits", """Hi {contact},

{hook}

We build outdoor LED in Shenzhen — {fit}. P4-P10, 5,500-8,000 nits, front-serviceable.

What size and viewing distance are you working with? One line back and I'll send the
sheet for that pitch.
"""),
    "general": ("{company} — which cabinet are you running?", """Hi {contact},

{hook}

We build LED panels in Shenzhen — {fit}.

What pitch and cabinet are you on now? If ours won't mix with your stock I'll say so and
leave it there.
"""),
}

EN_SECOND = {
    "rental": "Just the brand of cabinet you use is enough — that tells me whether our\npanels will mix with your stock.",
    "install": "Even a rough size and pitch is enough — that tells me whether we're worth\nputting on your vendor list.",
    "outdoor": "Even the screen size is enough — that tells me which pitch and brightness\nyou'd be comparing.",
    "general": "Just the brand of cabinet you use is enough — that tells me whether we're\nworth your time.",
}

# --- Korean ------------------------------------------------------------------------

KO_OPENER = {
    "rental": ("{company} — 현재 어떤 캐비닛 쓰고 계신가요?", """안녕하세요, {contact}님.

{hook_ko}

저희는 선전에서 LED 패널을 직접 만듭니다 — {fit_ko}. 렌탈은 P2.6-P4.8, 다이캐스팅
캐비닛으로 실내외 모두 됩니다.

지금 어떤 캐비닛 쓰고 계신가요? 기존 장비와 안 맞으면 솔직히 말씀드리고 더 연락드리지
않겠습니다.
"""),
    "install": ("{company} — 다음 시공 건 패널 문의", """안녕하세요, {contact}님.

{hook_ko}

저희는 선전에서 LED 패널을 직접 만듭니다 — {fit_ko}. 고정 설치는 실내 P2-P3, 실외
P4-P10, 전면·후면 유지보수 모두 됩니다.

다음 건은 어떤 사양 보고 계신가요? 크기만 알려주시면 무게와 소비전력까지 넣은 사양서를
보내드리겠습니다. 도면에 그대로 들어갑니다.
"""),
    "outdoor": ("{company} — 실외 P4-P10, 5,500-8,000 nits", """안녕하세요, {contact}님.

{hook_ko}

저희는 선전에서 실외 LED를 직접 만듭니다 — {fit_ko}. P4-P10, 5,500-8,000 nits,
전면 유지보수 가능합니다.

크기와 시청 거리가 어떻게 되나요? 한 줄만 주시면 해당 피치 사양서를 보내드리겠습니다.
"""),
    "general": ("{company} — 현재 어떤 캐비닛 쓰고 계신가요?", """안녕하세요, {contact}님.

{hook_ko}

저희는 선전에서 LED 패널을 직접 만듭니다 — {fit_ko}.

지금 어떤 피치와 캐비닛을 쓰고 계신가요? 저희 것이 안 맞으면 솔직히 말씀드리고 더
연락드리지 않겠습니다.
"""),
}

KO_SECOND = {
    "rental": "쓰시는 캐비닛 브랜드만 알려주셔도 됩니다. 기존 장비와 맞는지 바로 판단됩니다.",
    "install": "대략적인 크기와 피치만으로도 충분합니다. 협력업체 목록에 넣을 만한지 판단됩니다.",
    "outdoor": "화면 크기만 알려주셔도 됩니다. 어떤 피치와 밝기를 비교하실지 나옵니다.",
    "general": "쓰시는 캐비닛 브랜드만 알려주셔도 충분합니다.",
}

# The third letter is the same for everyone (docs/76 R2).
EN_LAST = """Hi {contact},

Last note. If panels aren't on your plan, that's a fine answer.

Whenever one comes up, write to me — you'll get specs the same day.
"""

KO_LAST = """안녕하세요, {contact}님.

마지막 메일입니다. 지금 계획이 없으시면 그것으로 충분한 답변입니다.

나중에 프로젝트가 생기시면 연락 주세요. 당일에 사양 보내드리겠습니다.
"""

EN_HANDOFF = "\n\nNot your area? Point me at whoever handles displays and I'll stop here.\n\n"
KO_HANDOFF = "\n\n담당이 아니시면 디스플레이 담당자분만 알려주세요.\n\n"

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
