"""A third angle that stops selling and asks who buys (docs/74 R4).

`_switch_angle` had nowhere to go. Every enrollment it wanted to move was already on
angle two, so the fallback fired and 75 follow-ups parked in `quality_hold` — the same
standstill docs/67 had to rescue 110 letters from, reappearing for the same reason.

The angle had to differ in kind, not in wording:

    angle one    we manufacture LED panels, tell me about your project   361 sent, 1 reply
    angle two    which cabinet are you running?                          sending
    angle three  two letters, no reply — I think I have the wrong person

It makes no product claim, no capability claim and no case claim, so it cannot trip the
case gate, the product gate or docs/45. That is not a convenience: after two unanswered
letters the most likely explanation is not that the pitch was wrong but that it reached
somebody who does not buy displays, and this letter addresses exactly that. It is the
writing half of the same job `decision_maker_radar` does by reading public pages.

Run:  python -m app.seed_angle3            # preview
      python -m app.seed_angle3 --apply
"""
from __future__ import annotations

import sys

from app.db import connect
from app.seed_angle2 import EN_SIGN, KO_SIGN, _seed

EN_NAME = "冷邮件 3 步跟进（英语·角度三）"
KO_NAME = "冷邮件 3 步跟进（韩语·角度三）"

EN_STEPS = [
    (0, 0, "{company} — wrong person?", """Hi {contact},

I've written twice about LED displays and heard nothing, which usually means I'm writing
to the wrong desk.

Who handles display purchasing at {company}? One name and I'll take it from there —
and stop writing to you.

""" + EN_SIGN),
    (1, 5, "Re: {company} — wrong person?", """Hi {contact},

Still just after a name — whoever specs or buys the screens.

If that's nobody, say so and I'll close the file.

""" + EN_SIGN),
]

KO_STEPS = [
    (0, 0, "{company} — 담당자가 다른 분이신가요?", """안녕하세요, {contact}님.

LED 디스플레이 관련해서 두 번 메일 드렸는데 회신이 없어서요. 보통은 담당이 아닌 분께
보냈다는 뜻이더라고요.

{company}에서 디스플레이 구매는 어느 분이 담당하시나요? 성함만 알려주시면
그분께 연락드리고, {contact}님께는 더 이상 메일 드리지 않겠습니다.

""" + KO_SIGN),
    (1, 5, "Re: {company} — 담당자가 다른 분이신가요?", """안녕하세요, {contact}님.

성함만 알려주시면 됩니다 — 화면 사양이나 구매를 보시는 분이요.

해당하는 분이 안 계시면 그렇게 말씀해 주세요. 여기서 정리하겠습니다.

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
