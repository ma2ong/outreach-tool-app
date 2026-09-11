"""Cold email sequences for the three outbound customer segments.

Rental and Install receive specialised copy only when the routing evidence is clear.
Everything mixed or uncertain receives General. Outdoor remains a product/use case, not
a customer segment.

The opener follows one commercial pattern: who Allen is, the smallest relevant product
range, then one low-friction thing the prospect can send back. It deliberately avoids a
catalogue dump, pricing, unsupported claims and mail-merge language.

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

# Three distinct openers, not three versions of the same catalogue. Rental talks about
# stock/cabinet fit, Install talks about specification/drawing input, and General asks for
# whichever single clue is easiest for the prospect to give us.
EN_OPENER = {
    "rental": ("Rental LED: P2.6-P4.8 die-cast", """{greeting}

{hook}

This is Allen from an LED display manufacturer in Shenzhen.

For rental projects, we offer P2.604, P2.976, P3.91 and P4.8 for both indoor and outdoor use,
with die-cast cabinets and front/rear service options.

If you have a project coming up, send me the pitch or specs you need. I can recommend
the suitable configuration and prepare a detailed quotation for you.
"""),
    "install": ("Fixed-install LED: P0.6-P10, front/rear service", """{greeting}

{hook}

This is Allen from an LED display manufacturer in Shenzhen.

For fixed-install projects, we cover P0.6-P4 indoor and P2.5-P10 outdoor, with front or
rear service options.

If you're specifying a project, send me the pitch, screen size or other requirements.
I can recommend the suitable configuration and prepare a detailed quotation for you.
"""),
    "general": ("LED display range: P0.6-P10", """{greeting}

{hook}

This is Allen from an LED display manufacturer in Shenzhen.

We cover fine pitch P0.6-P1.8, indoor P2-P4, rental P2.604 / P2.976 / P3.91 / P4.8
and outdoor fixed P2.5-P10.

If LED is relevant to your work, send me the application, pitch, screen size or specs you
need. I can recommend the suitable option and prepare a detailed quotation for you.
"""),
}

EN_SECOND = {
    "rental": "Just following up — if you tell me the pitch or specs you need, I can "
              "recommend a suitable rental configuration and prepare a detailed quotation.",
    "install": "If a fixed-install project comes up, send me the pitch, screen size or "
               "requirements and I can recommend a suitable configuration and prepare a quotation.",
    "general": "If LED comes up in your pipeline, send me the application, pitch, size or "
               "specs you need and I can recommend the suitable option and prepare a quotation.",
}

# --- Korean ------------------------------------------------------------------------

KO_OPENER = {
    "rental": ("렌탈 LED: P2.6-P4.8 다이캐스팅", """{greeting}

{hook_ko}

심천 LED 디스플레이 제조업체의 Allen입니다.

렌탈용은 실내·실외 모두 P2.604 / P2.976 / P3.91 / P4.8 제품을 공급하고 있습니다.
다이캐스팅 캐비닛을 사용하며 전·후면 유지보수가 가능합니다.

필요하신 피치나 사양을 알려주시면 맞는 제품으로 추천드리고 상세 견적도 보내드리겠습니다.
"""),
    "install": ("고정 설치 LED: 실내 P0.6-P4 / 실외 P2.5-P10", """{greeting}

{hook_ko}

심천 LED 디스플레이 제조업체의 Allen입니다.

고정 설치용은 실내 P0.6-P4, 실외 P2.5-P10 제품을 공급하고 있습니다.
전·후면 유지보수 방식도 선택 가능합니다.

검토 중인 프로젝트가 있으면 피치, 화면 크기 또는 필요한 사양을 알려주세요.
맞는 제품으로 추천드리고 상세 견적도 보내드리겠습니다.
"""),
    "general": ("LED 디스플레이: P0.6-P10", """{greeting}

{hook_ko}

심천 LED 디스플레이 제조업체의 Allen입니다.

파인피치 P0.6-P1.8, 실내 P2-P4, 렌탈 P2.604 / P2.976 / P3.91 / P4.8,
실외 고정형 P2.5-P10까지 다양한 LED 제품을 공급하고 있습니다.

사용 용도나 피치, 화면 크기 또는 필요한 사양을 알려주시면 맞는 제품으로 추천드리고
상세 견적도 보내드리겠습니다.
"""),
}

KO_SECOND = {
    "rental": "혹시 렌탈용 LED 검토 중이시면 필요한 피치나 사양을 알려주세요. "
              "맞는 제품으로 추천드리고 상세 견적도 보내드리겠습니다.",
    "install": "고정 설치 건이 있으시면 피치, 화면 크기 또는 필요한 사양을 알려주세요. "
               "맞는 제품으로 추천드리고 상세 견적도 보내드리겠습니다.",
    "general": "LED 관련 건이 생기시면 용도, 피치, 화면 크기 또는 필요한 사양을 알려주세요. "
               "맞는 제품으로 추천드리고 상세 견적도 보내드리겠습니다.",
}

# Shared final reference: by this point the segment-specific angle has already done its
# work. Keep this useful and easy to file rather than turning it into a goodbye message.
EN_LAST = """{greeting}

One last reference for later: fine pitch P0.6-P1.8, indoor P2-P4, rental P2.604 /
P2.976 / P3.91 / P4.8, and outdoor fixed P2.5-P10.

Whenever a project comes up, send me the pitch, screen size or specs you need. I can
recommend a suitable configuration and prepare a detailed quotation for you.
"""

KO_LAST = """{greeting}

나중에 참고하시기 쉽게 제품 범위만 간단히 남깁니다. 파인피치 P0.6-P1.8, 실내 P2-P4,
렌탈 P2.604 / P2.976 / P3.91 / P4.8, 실외 고정형 P2.5-P10 제품을 공급하고 있습니다.

프로젝트 생기시면 피치, 화면 크기 또는 필요한 사양을 보내주세요. 맞는 제품으로
추천드리고 상세 견적도 보내드리겠습니다.
"""

# Never outrun the two-week contact-frequency rule.
OFFSETS = (0, 14, 28)

# Preserve the existing cadence decision: English General and Install are single-touch;
# Rental and Korean sequences retain the two follow-ups.
SINGLE_TOUCH = {("general", False), ("install", False)}


def name_for(segment: str, korean: bool) -> str:
    steps = "单封" if (segment, korean) in SINGLE_TOUCH else " 3 步跟进"
    return f"冷邮件{steps}（{'韩语' if korean else '英语'}·{LABEL[segment]}）"


def steps_for(segment: str, korean: bool) -> list[tuple]:
    if korean:
        opener, second, last, sign = KO_OPENER, KO_SECOND, KO_LAST, KO_SIGN
    else:
        opener, second, last, sign = EN_OPENER, EN_SECOND, EN_LAST, EN_SIGN
    greeting = "{greeting}\n\n"
    subject, body = opener[segment]
    steps = [(0, OFFSETS[0], subject, body + "\n" + sign)]
    if (segment, korean) in SINGLE_TOUCH:
        return steps
    follow = f"Re: {subject}"
    steps.append((1, OFFSETS[1], follow, greeting + second[segment] + "\n\n" + sign))
    steps.append((2, OFFSETS[2], follow, last + "\n" + sign))
    return steps


def ensure_routing_columns(conn) -> None:
    """`segment` and `korean` say who a sequence is for."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(sequences)")}
    if "segment" not in cols:
        conn.execute("ALTER TABLE sequences ADD COLUMN segment TEXT")
    if "korean" not in cols:
        conn.execute("ALTER TABLE sequences ADD COLUMN korean INTEGER")
    conn.commit()


def seed(conn, name: str, steps, *, segment: str | None = None,
         korean: bool | None = None) -> int:
    """Write the repo's copy into this sequence, unless a person has edited it."""
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
    """Every segment in both languages; returns {(segment, korean): sequence_id}."""
    out = {}
    for korean in (False, True):
        for segment in SEGMENTS:
            out[(segment, korean)] = seed(
                conn, name_for(segment, korean), steps_for(segment, korean),
                segment=segment, korean=korean)
    close_orphaned_enrollments(conn)
    conn.commit()
    from app import sequence_routing
    sequence_routing.seed_declared_routes(conn)
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
