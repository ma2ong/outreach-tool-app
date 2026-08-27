"""A second angle, in English and Korean, and the parked follow-ups moved onto it (docs/67).

The first English angle sent 361 letters for one reply. Read it back and the reason is
not hard to find — every sentence is about us:

    We manufacture the panels behind that kind of work — indoor and outdoor,
    P1.86 through P10 — and supply integrators and rental companies directly.

Every LED factory in Shenzhen can send that. It also asks the reader to do the work:
"tell me the pitch and the size and I'll send specs" means opening a project file before
they can answer at all.

The second angle inverts both, and is short. A stranger does not read five paragraphs —
the first draft of this angle was better written and still too long, so it says one true
thing about their kind of work and asks one question answerable in a line.

110 follow-ups sat in `quality_hold` doing nothing. Parking was half a decision: the
system correctly saw the angle was not working and then stopped instead of changing it.
They move here.

Run:  python -m app.seed_angle2            # preview
      python -m app.seed_angle2 --apply
"""
from __future__ import annotations

import datetime as dt
import sys

from app.db import connect

EN_NAME = "冷邮件 3 步跟进（英语·角度二）"
KO_NAME = "冷邮件 3 步跟进（韩语·角度二）"

EN_SIGN = """Allen Ma · Shenzhen Maxcolor Visual
WhatsApp/WeChat +86 135-7087-1001"""

KO_SIGN = """Allen Ma · Shenzhen Maxcolor Visual
Kakaotalk / WeChat +86 13570871001"""

EN_STEPS = [
    (0, 0, "{company} — which cabinet are you running?", """Hi {contact},

{hook}

We build LED panels in Shenzhen — {fit}.

What pitch and cabinet are you on now? If ours won't mix with your stock I'll say so and
leave it there.

""" + EN_SIGN),
    (1, 4, "Re: {company} — which cabinet are you running?", """Hi {contact},

Just the brand of cabinet you use is enough — that tells me whether we're worth your
time.

Not your area? Point me at whoever handles displays and I'll stop here.

""" + EN_SIGN),
    (2, 7, "Re: {company} — which cabinet are you running?", """Hi {contact},

Last note. If panels aren't on your plan, that's a fine answer.

Whenever one comes up, write to me — you'll get specs the same day.

""" + EN_SIGN),
]

# Korea keeps Korean (docs/67 R1), including the opener: {hook_ko} says the same line in
# Korean rather than dropping an English sentence into a Korean letter.
KO_STEPS = [
    (0, 0, "{company} — 현재 어떤 캐비닛 쓰고 계신가요?", """안녕하세요, {contact}님.

{hook_ko}

저희는 선전에서 LED 패널을 직접 만듭니다 — {fit_ko}.

지금 어떤 피치와 캐비닛을 쓰고 계신가요? 저희 것이 안 맞으면 솔직히 말씀드리고
더 연락드리지 않겠습니다.

""" + KO_SIGN),
    (1, 4, "Re: {company} — 현재 어떤 캐비닛 쓰고 계신가요?", """안녕하세요, {contact}님.

쓰시는 캐비닛 브랜드만 알려주셔도 충분합니다. 그것만으로 저희가 도움이 될지 판단됩니다.

담당이 아니시면 디스플레이 담당자분만 알려주세요. 여기서 그만 연락드리겠습니다.

""" + KO_SIGN),
    (2, 7, "Re: {company} — 현재 어떤 캐비닛 쓰고 계신가요?", """안녕하세요, {contact}님.

마지막 메일입니다. 지금 계획이 없으시면 그것으로 충분한 답변입니다.

나중에 프로젝트가 생기시면 연락 주세요. 당일에 사양 보내드리겠습니다.

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
        print(f"挂起的跟进 {len(rows)} 个：韩语 {len(korean)}，英语 {len(rows) - len(korean)}")
        print()
        print("--- 英语第一封 ---")
        print(EN_STEPS[0][3])
        print()
        print("--- 韩语第一封 ---")
        print(KO_STEPS[0][3])
        if not apply_changes:
            print("\n确认没问题就加 --apply 写入")
            return

        en_id = _seed(conn, EN_NAME, EN_STEPS)
        ko_id = _seed(conn, KO_NAME, KO_STEPS)
        today = dt.date.today().isoformat()
        for row in rows:
            # Back to step 0: a new opener, not the next line of the old conversation.
            conn.execute(
                "UPDATE sequence_enrollments SET sequence_id=?, current_step=0,"
                " status='active', next_due_date=? WHERE id=?",
                (ko_id if row in korean else en_id, today, row["id"]))
        conn.commit()
        print(f"\n已写入。{len(rows)} 个跟进转到角度二。")


if __name__ == "__main__":
    main()
