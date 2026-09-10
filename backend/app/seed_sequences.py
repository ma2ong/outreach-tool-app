"""System-owned cold email copy for Rental / Install / General (docs/127).

The copy is intentionally evidence-first and restrained.  A first touch has one idea and
one easy question; it does not dump the catalogue or make static product claims that may
become stale.  Follow-ups earn another touch by adding a new useful angle instead of
saying "just checking in".

Outdoor is no longer a customer-type copy segment.  Existing Outdoor sequences are
historical records and are deliberately left in the database; ``seed_all`` simply stops
creating or routing new standard copy for that segment.

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

# Keep the old sequence-name labels for the three surviving rows.  The name is part of
# the seeder's identity key; changing it just to display the new English segment labels
# would create duplicate sequences and strand existing enrollments.
_SEQUENCE_NAME_LABEL = {
    "rental": "活动租赁",
    "install": "固定安装",
    "general": "中性版",
}

# --- English -----------------------------------------------------------------------

EN_OPENER = {
    "rental": ("Rental LED planning", """Hi {contact},

{hook}

This is Allen from an LED display manufacturer in Shenzhen.

For rental work, I'd rather start with how your team builds and services shows than send
a long product list.

If you are adding or refreshing rental LED stock, what requirement matters most on your
side?
"""),
    "install": ("LED project planning", """Hi {contact},

{hook}

This is Allen from an LED display manufacturer in Shenzhen.

For fixed-install work, I'd rather start from the project constraints than send a generic
product list.

If you have an active LED project, could you send the screen size and application?
"""),
    "general": ("LED project question", """Hi {contact},

{hook}

This is Allen from an LED display manufacturer in Shenzhen.

I'm not assuming whether your current LED work is mainly rental or fixed install.

Which is more relevant right now: rental inventory or a fixed-install project?
"""),
}

# A follow-up must contribute a new decision-useful angle.  English Install and General
# are currently single-touch by explicit policy, but their copy remains defined so a
# future cadence change does not fall back to generic chasing language.
EN_SECOND = {
    "rental": "One useful rental check is operational fit: cabinet format, service access, and how "
              "the panels fit your usual build. Which one matters most on your side?",
    "install": "For fixed-install projects, exact screen dimensions and service access can rule out "
               "options early. If you want me to narrow it, which of those is already fixed?",
    "general": "Screen size and application are enough to avoid sending irrelevant options. "
               "Which of those do you already have?",
}

EN_LAST = """Hi {contact},

A simple starting point is the project, not a catalogue. Screen size, application, and
whether it is rental or fixed install are enough for me to narrow what is relevant.

If useful, send whichever of those facts you already have.
"""

# --- Korean ------------------------------------------------------------------------

KO_OPENER = {
    "rental": ("렌탈 LED 재고 검토", """안녕하세요, {contact}님.

{hook_ko}

심천 LED 디스플레이 제조업체에서 해외영업을 담당하고 있는 Allen입니다.

렌탈 쪽은 긴 제품 리스트부터 보내기보다 실제 운용 방식과 유지보수 조건을 먼저 보는 편이
더 맞다고 생각합니다.

현재 렌탈 LED 재고를 추가하거나 교체하실 계획이 있다면, 가장 중요하게 보시는 조건이 어떤
부분인지 알려주실 수 있을까요?
"""),
    "install": ("LED 설치 프로젝트", """안녕하세요, {contact}님.

{hook_ko}

심천 LED 디스플레이 제조업체에서 해외영업을 담당하고 있는 Allen입니다.

고정 설치 프로젝트는 제품 리스트보다 현장 조건부터 보는 게 더 정확합니다.

현재 검토 중인 LED 프로젝트가 있다면 화면 크기와 설치 용도만 알려주실 수 있을까요?
"""),
    "general": ("LED 프로젝트 문의", """안녕하세요, {contact}님.

{hook_ko}

심천 LED 디스플레이 제조업체에서 해외영업을 담당하고 있는 Allen입니다.

현재 업무가 렌탈 위주인지 고정 설치 위주인지 제가 임의로 판단하지 않겠습니다.

지금 더 관련 있는 쪽이 렌탈 장비인지 고정 설치 프로젝트인지 알려주실 수 있을까요?
"""),
}

KO_SECOND = {
    "rental": "렌탈 제품은 실제 운용할 때 캐비닛 구성과 유지보수 방식이 중요하더라고요. "
              "평소 가장 중요하게 보시는 조건이 어떤 부분인가요?",
    "install": "고정 설치는 실제 화면 크기와 유지보수 방식이 정해지면 검토 범위를 많이 줄일 수 "
               "있습니다. 두 가지 중 지금 확정된 내용이 있을까요?",
    "general": "프로젝트가 아직 구체적이지 않아도 화면 크기와 설치 용도 정도면 불필요한 제품은 "
               "먼저 제외할 수 있습니다. 지금 확인된 내용이 있을까요?",
}

KO_LAST = """안녕하세요, {contact}님.

제품 목록부터 보내기보다 프로젝트 기준으로 보는 게 더 빠릅니다. 화면 크기, 설치 용도,
렌탈인지 고정 설치인지 정도만 알아도 관련 있는 쪽으로 범위를 줄일 수 있습니다.

나중에 필요하실 때 확인된 내용만 보내주시면 그 기준으로 정리해 드리겠습니다.
"""


# docs/75 R1: the schedule may never outrun the two-week frequency rule.
OFFSETS = (0, 14, 28)


# The English General and Install tracks remain single-touch by the existing contact
# policy.  This patch changes segmentation and copy, not send pressure.
SINGLE_TOUCH = {("general", False), ("install", False)}


def name_for(segment: str, korean: bool) -> str:
    steps = "单封" if (segment, korean) in SINGLE_TOUCH else " 3 步跟进"
    return f"冷邮件{steps}（{'韩语' if korean else '英语'}·{_SEQUENCE_NAME_LABEL[segment]}）"


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
    """Write repo-owned copy into this sequence, unless a person has edited it."""
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
    """Seed the three current segments in both languages.

    Legacy Outdoor sequence rows and their enrollments are not deleted or reclassified;
    they simply stop receiving new routing from ``copy_segments.segment_of``.
    """
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
            print(f"  {segment:9} {LABEL[segment]:7} {counts[segment]:4} 家")
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
