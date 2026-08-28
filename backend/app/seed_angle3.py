"""A third angle that puts the whole product line on the table (docs/74 R4).

`_switch_angle` had nowhere to go. Every enrollment it wanted to move was already on
angle two, so the fallback fired and 75 follow-ups parked in `quality_hold` — the same
standstill docs/67 had to rescue 110 letters from, reappearing for the same reason.

The first draft of this angle stopped selling and only asked who buys. Allen rejected it
outright — "还是要继续推销、提产品、提能力" — and the rule is broader than this file: a
letter may not dodge the product gate by declining to mention products. Writing around
the gate spares us the work, not the customer.

What makes it a third angle is what it asks for, not what it withholds:

    angle one    we manufacture LED panels — now describe your project   361 sent, 1 reply
    angle two    which cabinet are you running?                          sending
    angle three  here is the whole pitch range; say a word, get the sheet

Angle one wanted a project brief, angle two wanted their current kit. This one wants
nothing: every pitch in it traces to a row in the product library, and the reply it asks
for is a single word.
"""
from __future__ import annotations

import sys

from app.db import connect
from app.seed_angle2 import EN_SIGN, KO_SIGN, _seed

EN_NAME = "冷邮件 3 步跟进（英语·角度三）"
KO_NAME = "冷邮件 3 步跟进（韩语·角度三）"

EN_STEPS = [
    (0, 0, "{company} — P0.7 to P10, our own factory", """Hi {contact},

We build LED panels at our own factory in Shenzhen, so cabinets are cut to your size:

  fine pitch P0.7-P1.8 · indoor P2-P3 · rental P2.6-P4.8 · outdoor fixed P4-P10

{fit}

Which line is closest to your work? Say the word and the spec sheet goes out today.

""" + EN_SIGN),
    (1, 5, "Re: {company} — P0.7 to P10, our own factory", """Hi {contact},

Short version: fine pitch, rental and outdoor — we make all three ourselves, and we cut
cabinets to your size.

One line back and the sheet is with you today. Not your area? Point me at whoever
handles displays.

""" + EN_SIGN),
]

KO_STEPS = [
    (0, 0, "{company} — P0.7~P10, 자체 공장 생산", """안녕하세요, {contact}님.

저희는 선전 자체 공장에서 LED 패널을 직접 생산합니다. 캐비닛은 사이즈 맞춤 제작됩니다.

  파인피치 P0.7-P1.8 · 실내 P2-P3 · 렌탈 P2.6-P4.8 · 실외 고정 P4-P10

{fit_ko}

어느 라인이 가장 가까우신가요? 말씀만 주시면 사양서를 오늘 보내드리겠습니다.

""" + KO_SIGN),
    (1, 5, "Re: {company} — P0.7~P10, 자체 공장 생산", """안녕하세요, {contact}님.

간단히 말씀드리면 — 파인피치, 렌탈, 실외 전부 자체 생산하고 캐비닛은 사이즈 맞춤입니다.

한 줄만 주시면 오늘 사양서 보내드리겠습니다. 담당이 아니시면 디스플레이 담당자분만
알려주세요.

""" + KO_SIGN),
]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    apply_changes = "--apply" in sys.argv
    with connect("outreach.db") as conn:
        parked = conn.execute(
            "SELECT COUNT(*) FROM sequence_enrollments WHERE status='quality_hold'"
        ).fetchone()[0]
        print(f"停摆等角度三的入组：{parked} 个\n")
        for name, steps in ((EN_NAME, EN_STEPS), (KO_NAME, KO_STEPS)):
            print(f"=== {name} ===")
            for order, offset, subject, _body in steps:
                print(f"  第{order + 1}封 D+{offset}  {subject}")
        if not apply_changes:
            print("\n确认没问题就加 --apply 写入")
            return
        en = _seed(conn, EN_NAME, EN_STEPS)
        ko = _seed(conn, KO_NAME, KO_STEPS)
        conn.commit()
        print(f"\n已建序列：英语 #{en}，韩语 #{ko}")
        # A parked enrollment is `quality_hold` and `due_queue` reads only `active`,
        # so nothing would ever come back for these on its own.
        from app.agent import followup_decision
        print(f"从停摆里救回并放到角度三：{followup_decision.revive_parked(conn)} 个")


if __name__ == "__main__":
    main()
