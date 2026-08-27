"""A second angle, in English and Korean, and the parked follow-ups moved onto it (docs/67).

The first English angle sent 361 letters for one reply. Read it back and the reason is
not hard to find — every sentence is about us:

    We manufacture the panels behind that kind of work — indoor and outdoor,
    P1.86 through P10 — and supply integrators and rental companies directly.

Every LED factory in Shenzhen can send that. It also asks the reader to do the work:
"tell me the pitch and the size and I'll send specs" means opening a project file before
they can answer at all.

The second angle inverts both. It says something about *their* kind of work, using the
customer type the classifier now knows, and asks one question answerable in a line
without looking anything up — which cabinet they run today.

110 follow-ups sat in `quality_hold` doing nothing. Parking them was half a decision:
the system correctly saw the angle was not working and then stopped instead of changing
it. They move here.

Run:  python -m app.seed_angle2            # preview
      python -m app.seed_angle2 --apply
"""
from __future__ import annotations

import datetime as dt
import sys

from app.db import connect

EN_NAME = "冷邮件 3 步跟进（英语·角度二）"
KO_NAME = "冷邮件 3 步跟进（韩语·角度二）"

EN_SIGN = """Best regards,
Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
WhatsApp/WeChat: +86 135-7087-1001
Email: allen@maxcolorvisual.com"""

KO_SIGN = """Allen Ma
Shenzhen Maxcolor Visual Co., Ltd.
Kakaotalk / WeChat: +86 13570871001
Email: allen@maxcolorvisual.com"""

EN_STEPS = [
    (0, 0, "{company} — a question about your LED panels", """Hi {contact},

{hook}

{fit}

We build the panels for that kind of work in Shenzhen. Rather than send you a catalogue,
one question: what pitch and cabinet are you running now?

Tell me that and I can say straight whether we are worth talking to — sometimes the
honest answer is that what you already have is fine.

""" + EN_SIGN),
    (1, 4, "Re: {company} — a question about your LED panels", """Hi {contact},

Following up on my note. If it is easier, just reply with the cabinet brand you use —
that alone tells me whether our boxes would mix with your existing stock.

And if this is not your area, point me at whoever handles displays and I will stop
filling your inbox.

""" + EN_SIGN),
    (2, 7, "Re: {company} — a question about your LED panels", """Hi {contact},

Last note from me.

If LED panels are not on your plan, that is a completely fine answer and I will leave it
there. Whenever a project does come up — this year or in two — write to me and you will
get specs the same day, from someone who already knows what you run.

""" + EN_SIGN),
]

# Korea keeps Korean (docs/67 R1). Same angle, same question — not a translation of the
# old letter, which had the same problem the English one had.
KO_STEPS = [
    (0, 0, "{company} — 현재 사용 중인 LED 캐비닛 문의드립니다", """안녕하세요, {contact}님.

{hook}

{fit_ko}

저희는 선전에서 그런 현장에 들어가는 LED 패널을 직접 생산하고 있습니다.
카탈로그를 보내드리기 전에 한 가지만 여쭙고 싶습니다 — 현재 어떤 피치와 캐비닛을
사용하고 계신가요?

그것만 알려주시면 저희가 도움이 될지 아닐지 솔직하게 말씀드리겠습니다. 지금 쓰시는
것으로 충분하다는 답이 나오는 경우도 있습니다.

""" + KO_SIGN),
    (1, 4, "Re: {company} — 현재 사용 중인 LED 캐비닛 문의드립니다", """안녕하세요, {contact}님.

지난번 메일 관련해 다시 연락드립니다. 번거로우시면 사용 중인 캐비닛 브랜드만
알려주셔도 됩니다. 그것만으로도 저희 제품과 혼용이 가능한지 판단할 수 있습니다.

담당이 아니시라면 디스플레이 담당자분을 알려주시면 더 이상 메일 드리지 않겠습니다.

""" + KO_SIGN),
    (2, 7, "Re: {company} — 현재 사용 중인 LED 캐비닛 문의드립니다", """안녕하세요, {contact}님.

마지막 메일입니다.

지금 LED 패널 계획이 없으시다면 그것으로 충분한 답변입니다. 나중에 프로젝트가 생기실 때
언제든 연락 주시면, 이미 어떤 장비를 쓰시는지 아는 사람에게서 당일에 사양을 받아보실 수
있습니다.

""" + KO_SIGN),
]

KOREAN = ("south korea", "korea", "kr")


def _seed(conn, name: str, steps) -> int:
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


def parked(conn) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT e.id, e.lead_no, l.company_en, l.country"
        " FROM sequence_enrollments e JOIN leads l ON l.no = e.lead_no"
        " WHERE e.status='quality_hold'")]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    apply_changes = "--apply" in sys.argv
    with connect("outreach.db") as conn:
        rows = parked(conn)
        korean = [r for r in rows if str(r["country"] or "").lower() in KOREAN]
        english = [r for r in rows if r not in korean]
        print(f"挂起的跟进 {len(rows)} 个：韩语 {len(korean)}，英语 {len(english)}")
        print(f"新序列：{EN_NAME} / {KO_NAME}")
        print()
        print("--- 英语第一封 ---")
        print(EN_STEPS[0][3][:430])
        print()
        print("--- 韩语第一封 ---")
        print(KO_STEPS[0][3][:430])
        if not apply_changes:
            print("\n确认没问题就加 --apply 写入并把挂起的跟进转过来")
            return

        en_id = _seed(conn, EN_NAME, EN_STEPS)
        ko_id = _seed(conn, KO_NAME, KO_STEPS)
        today = dt.date.today().isoformat()
        for row in rows:
            target = ko_id if row in korean else en_id
            # Back to step 0: this is a new conversation opener, not the next line of
            # the old one.
            conn.execute(
                "UPDATE sequence_enrollments SET sequence_id=?, current_step=0,"
                " status='active', next_due_date=? WHERE id=?",
                (target, today, row["id"]))
        conn.commit()
        print(f"\n已写入。{len(rows)} 个跟进转到角度二，今天起可发。")


if __name__ == "__main__":
    main()
