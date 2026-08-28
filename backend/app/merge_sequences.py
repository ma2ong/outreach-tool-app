"""Fold the angle sequences back into one per language (docs/75 R4).

Angle switching is gone, so the sequences it switched between should not survive it —
leaving them would mean a lead's history is spread over three rows that no longer mean
anything, and the next person to read the pipeline would have to reconstruct why.

Everything moves onto the language's single sequence. Where a lead is enrolled on both
(it was moved between angles at some point) the further-along enrollment wins and the
duplicate is dropped, because `UNIQUE(lead_no, sequence_id)` will not hold two and the
one that got more letters is the one whose history is real.

`quality_hold` becomes `active`: it was the parking state for "ran out of angles", and
there are no angles to run out of. What decides their next send now is the two-week
cooldown, like everything else.

Run:  python -m app.merge_sequences            # preview
      python -m app.merge_sequences --apply
"""
from __future__ import annotations

import sys

from app.db import connect
from app.seed_angle2 import EN_NAME, KO_NAME

# Angle sequence name -> the single sequence it folds into.
FOLD = {
    "冷邮件 3 步跟进（英语·角度二）": EN_NAME,
    "冷邮件 3 步跟进（英语·角度三）": EN_NAME,
    "冷邮件 3 步跟进（韩语·角度二）": KO_NAME,
    "冷邮件 3 步跟进（韩语·角度三）": KO_NAME,
}
# Furthest along wins when a lead sits on both.
RANK = {"replied": 5, "completed": 4, "active": 3, "quality_hold": 2, "blocked": 1}


def _id(conn, name: str) -> int | None:
    row = conn.execute("SELECT id FROM sequences WHERE name=?", (name,)).fetchone()
    return row["id"] if row else None


def plan(conn) -> list[dict]:
    out = []
    for old_name, new_name in FOLD.items():
        old, new = _id(conn, old_name), _id(conn, new_name)
        if old is None or new is None or old == new:
            continue
        rows = conn.execute(
            "SELECT id, lead_no, current_step, status FROM sequence_enrollments"
            " WHERE sequence_id=?", (old,)).fetchall()
        for row in rows:
            clash = conn.execute(
                "SELECT id, current_step, status FROM sequence_enrollments"
                " WHERE lead_no=? AND sequence_id=?", (row["lead_no"], new)).fetchone()
            out.append({
                "enrollment_id": row["id"], "lead_no": row["lead_no"],
                "from": old_name, "to": new_name, "status": row["status"],
                "drop": clash is not None and (
                    RANK.get(clash["status"], 0), clash["current_step"] or 0)
                    >= (RANK.get(row["status"], 0), row["current_step"] or 0),
            })
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    apply_changes = "--apply" in sys.argv
    with connect("outreach.db") as conn:
        moves = plan(conn)
        keep = [m for m in moves if not m["drop"]]
        drop = [m for m in moves if m["drop"]]
        print(f"要并入的入组 {len(moves)} 个：迁移 {len(keep)}，因重复丢弃 {len(drop)}")
        for name in FOLD:
            n = sum(1 for m in moves if m["from"] == name)
            print(f"  {name:34} {n}")
        if not apply_changes:
            print("\n确认没问题就加 --apply 写入")
            return
        for move in keep:
            conn.execute(
                "UPDATE sequence_enrollments SET sequence_id=(SELECT id FROM sequences"
                " WHERE name=?), status=CASE WHEN status='quality_hold' THEN 'active'"
                " ELSE status END WHERE id=?", (move["to"], move["enrollment_id"]))
        for move in drop:
            conn.execute("DELETE FROM sequence_enrollments WHERE id=?",
                         (move["enrollment_id"],))
        for old_name in FOLD:
            old = _id(conn, old_name)
            if old is None:
                continue
            conn.execute("DELETE FROM sequence_steps WHERE sequence_id=?", (old,))
            conn.execute("DELETE FROM sequences WHERE id=?", (old,))
        # Nothing parks any more, so nothing should still be parked.
        conn.execute("UPDATE sequence_enrollments SET status='active'"
                     " WHERE status='quality_hold'")
        conn.commit()
        print(f"\n已迁移 {len(keep)}，丢弃重复 {len(drop)}，删除 {len(FOLD)} 条角度序列")


if __name__ == "__main__":
    main()
