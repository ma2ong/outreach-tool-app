"""System-owned cold email copy for Rental / Install / General (docs/127).

The segment is chosen before the first letter from known customer evidence. Specialist
copy is used only for a clear Rental or Install company; mixed and uncertain companies
get General. Outdoor remains a project/application fact and has no copy family.

The copy itself follows one compact sales shape: use the lead's real hook when present,
state one relevant LED capability, then ask one low-friction question. This is a design-
time copy contract, not a new send gate; existing Message Guard and send controls remain
unchanged.

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

# No company-name token in subject/body. The hook is the specific evidence when one is
# available; an empty hook is allowed by the current first-touch policy. Product claims
# stay deliberately broad here so the letter does not turn into a catalogue assembled
# from assumptions about a prospect we have never spoken with.
EN_OPENER = {
    "rental": ("LED panels for rental and staging", """Hi {contact},

{hook}

I'm Allen in Shenzhen. We supply LED display panels for rental and staging work.

What pitch do you use most often in your rental inventory?
"""),
    "install": ("LED panels for fixed-install projects", """Hi {contact},

{hook}

I'm Allen in Shenzhen. We supply LED display panels for AV integrators and fixed-install projects.

What pitch are you working around on your next LED project?
"""),
    "general": ("LED display panels for project and rental work", """Hi {contact},

{hook}

I'm Allen in Shenzhen. We supply LED display panels to rental companies and AV installers.

Do you mainly handle rental work, fixed install, or both?
"""),
}

# Follow-ups do not repeat the catalogue or invent a new angle. One sentence of context,
# one question. English Install and General are intentionally single-touch below, but the
# entries still exist because Korean currently uses the three-step cadence.
EN_SECOND = {
    "rental": "Quick follow-up on rental LED: what pitch do you run most often?",
    "install": "Quick follow-up on fixed-install LED: what pitch are you specifying most often?",
    "general": "Quick follow-up: do you mainly handle rental work, fixed install, or both?",
}

KO_OPENER = {
    "rental": ("렌탈·무대용 LED 패널", """안녕하세요, {contact}님.

{hook_ko}

심천에서 LED 디스플레이 해외영업을 하고 있는 Allen입니다. 렌탈·무대용 LED 패널을 공급하고 있습니다.

렌탈 장비에서 가장 많이 쓰시는 피치는 어떤 규격인가요?
"""),
    "install": ("고정 설치 프로젝트용 LED 패널", """안녕하세요, {contact}님.

{hook_ko}

심천에서 LED 디스플레이 해외영업을 하고 있는 Allen입니다. AV 시공·고정 설치 프로젝트용 LED 패널을 공급하고 있습니다.

다음 프로젝트에서 검토 중인 피치는 어떤 규격인가요?
"""),
    "general": ("프로젝트·렌탈용 LED 패널", """안녕하세요, {contact}님.

{hook_ko}

심천에서 LED 디스플레이 해외영업을 하고 있는 Allen입니다. 렌탈 업체와 AV 시공업체에 LED 패널을 공급하고 있습니다.

주로 렌탈, 고정 설치, 아니면 둘 다 하시나요?
"""),
}

KO_SECOND = {
    "rental": "짧게 다시 연락드립니다. 렌탈 장비에서 가장 많이 쓰시는 피치는 어떤 규격인가요?",
    "install": "짧게 다시 연락드립니다. 고정 설치 프로젝트에서 가장 많이 쓰시는 피치는 어떤 규격인가요?",
    "general": "짧게 다시 연락드립니다. 주로 렌탈, 고정 설치, 아니면 둘 다 하시나요?",
}

# The final follow-up is deliberately shared. By this point inventing another segment-
# specific pitch adds maintenance and reads like a campaign. Ask one practical question
# instead; pricing remains Allen's.
EN_LAST = """Hi {contact},

One practical question for future LED jobs: what pitch comes up most often for you?
"""

KO_LAST = """안녕하세요, {contact}님.

한 가지만 여쭤보겠습니다. LED 프로젝트에서 가장 자주 쓰시는 피치는 어떤 규격인가요?
"""

# The schedule may never outrun the two-week frequency rule (docs/75 R1).
OFFSETS = (0, 14, 28)

# Existing product decision retained: English General and Install are one cold touch.
SINGLE_TOUCH = {("general", False), ("install", False)}


def name_for(segment: str, korean: bool) -> str:
    steps = "单封" if (segment, korean) in SINGLE_TOUCH else " 3 步跟进"
    return f"冷邮件{steps}（{'韩语' if korean else '英语'}·{LABEL[segment]}）"


def steps_for(segment: str, korean: bool) -> list[tuple]:
    if korean:
        opener, second, last, sign = KO_OPENER, KO_SECOND, KO_LAST, KO_SIGN
        greeting = "안녕하세요, {contact}님.\n\n"
    else:
        opener, second, last, sign = EN_OPENER, EN_SECOND, EN_LAST, EN_SIGN
        greeting = "Hi {contact},\n\n"
    subject, body = opener[segment]
    steps = [(0, OFFSETS[0], subject, body + "\n" + sign)]
    if (segment, korean) in SINGLE_TOUCH:
        return steps
    follow = f"Re: {subject}"
    steps.append((1, OFFSETS[1], follow, greeting + second[segment] + "\n\n" + sign))
    steps.append((2, OFFSETS[2], follow, last + "\n" + sign))
    return steps


def ensure_routing_columns(conn) -> None:
    """`segment` and `korean` say who a sequence is for (docs/86 R4)."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(sequences)")}
    if "segment" not in cols:
        conn.execute("ALTER TABLE sequences ADD COLUMN segment TEXT")
    if "korean" not in cols:
        conn.execute("ALTER TABLE sequences ADD COLUMN korean INTEGER")
    conn.commit()


def seed(conn, name: str, steps, *, segment: str | None = None,
         korean: bool | None = None) -> int:
    """Write repo-owned copy unless a person edited this sequence in the UI."""
    from app.sequence_edit import edited_sequences

    ensure_routing_columns(conn)
    row = conn.execute("SELECT id FROM sequences WHERE name=?", (name,)).fetchone()
    if row:
        seq_id = row["id"]
        if seq_id in edited_sequences(conn):
            return seq_id
        conn.execute("DELETE FROM sequence_steps WHERE sequence_id=?", (seq_id,))
    else:
        seq_id = conn.execute(
            "INSERT INTO sequences(name, channel) VALUES (?, 'email')", (name,)).lastrowid
    if segment is not None:
        conn.execute("UPDATE sequences SET segment=?, korean=? WHERE id=?",
                     (segment, int(bool(korean)), seq_id))
    for order, offset, subject, body in steps:
        conn.execute(
            "INSERT INTO sequence_steps(sequence_id, step_order, day_offset, subject, body)"
            " VALUES (?,?,?,?,?)", (seq_id, order, offset, subject, body))
    return seq_id


def close_orphaned_enrollments(conn) -> int:
    """Complete anyone waiting on a step that no longer exists."""
    cur = conn.execute(
        "UPDATE sequence_enrollments SET status='completed'"
        " WHERE status='active' AND NOT EXISTS ("
        "   SELECT 1 FROM sequence_steps st"
        "   WHERE st.sequence_id = sequence_enrollments.sequence_id"
        "     AND st.step_order = sequence_enrollments.current_step)")
    return cur.rowcount


def seed_all(conn) -> dict[tuple[str, bool], int]:
    """Seed the three system segments in both languages."""
    out = {}
    for korean in (False, True):
        for segment in SEGMENTS:
            out[(segment, korean)] = seed(
                conn, name_for(segment, korean), steps_for(segment, korean),
                segment=segment, korean=korean)
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
