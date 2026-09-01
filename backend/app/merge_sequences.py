"""Move every enrollment onto the sequence written for that company (docs/76).

Two rounds of consolidation live here. The first folded the angle sequences back into one
per language when docs/75 deleted angle switching. This one splits that single sequence
again — but along a different seam: not by which copy failed, by which kind of customer
the company is.

An enrollment moves to its segment's sequence and keeps its step, because the segments
share a step structure (opener, one nudge, one close) and a company two letters into the
conversation should not be started over. Where the lead is already enrolled in its target
sequence, the duplicate is dropped: `UNIQUE(lead_no, sequence_id)` will not hold two, and
the one with more history is the one that is real.

Old sequences left with no enrollments are deleted; ones that still hold history stay,
so nothing about what a company actually received is lost.

Run:  python -m app.merge_sequences            # preview
      python -m app.merge_sequences --apply
"""
from __future__ import annotations

import sys

from app import copy_segments
from app.db import connect
from app.seed_sequences import close_orphaned_enrollments, name_for, seed_all

# Furthest along wins when a lead sits on both.
RANK = {"replied": 5, "completed": 4, "stopped": 4, "active": 3, "blocked": 1}


def _korean(country: str | None) -> bool:
    return str(country or "").strip().lower() in {
        "south korea", "korea", "republic of korea", "대한민국",
    }


def plan(conn) -> list[dict]:
    """What would move, without touching anything."""
    # A target sequence that does not exist yet still counts as a move: --apply seeds
    # them first, and a preview reporting "0 to move" because nothing is seeded yet is a
    # false all-clear, not an answer.
    target: dict[str, int | None] = {
        name_for(segment, korean): None
        for korean in (False, True) for segment in copy_segments.SEGMENTS}
    for row in conn.execute("SELECT id, name FROM sequences"):
        target[row["name"]] = row["id"]
    out = []
    for row in conn.execute(
            "SELECT e.id, e.lead_no, e.sequence_id, e.current_step, e.status,"
            "       l.country, l.tags, l.target_fit, l.business, l.hook, l.brief"
            "  FROM sequence_enrollments e JOIN leads l ON l.no = e.lead_no"
            " WHERE e.sequence_id IN (SELECT id FROM sequences WHERE channel='email')"):
        lead = dict(row)
        segment = copy_segments.segment_of(lead)
        name = name_for(segment, _korean(row["country"]))
        if name not in target:
            continue
        want = target[name]
        if want is not None and want == row["sequence_id"]:
            continue
        clash = None if want is None else conn.execute(
            "SELECT current_step, status FROM sequence_enrollments"
            " WHERE lead_no=? AND sequence_id=?", (row["lead_no"], want)).fetchone()
        out.append({
            "enrollment_id": row["id"], "lead_no": row["lead_no"],
            "to": want, "to_name": name,
            "segment": segment, "status": row["status"],
            "drop": clash is not None
                    and (RANK.get(clash["status"], 0), clash["current_step"] or 0)
                        >= (RANK.get(row["status"], 0), row["current_step"] or 0),
        })
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    apply_changes = "--apply" in sys.argv
    with connect("outreach.db") as conn:
        if apply_changes:
            seed_all(conn)          # the target sequences must exist before anything moves
        moves = plan(conn)
        assert not apply_changes or all(m["to"] is not None for m in moves)
        keep = [m for m in moves if not m["drop"]]
        drop = [m for m in moves if m["drop"]]
        by_segment: dict[str, int] = {}
        for move in keep:
            by_segment[move["segment"]] = by_segment.get(move["segment"], 0) + 1
        print(f"要重新归位的入组 {len(moves)} 个：迁移 {len(keep)}，因重复丢弃 {len(drop)}")
        for segment, n in sorted(by_segment.items(), key=lambda kv: -kv[1]):
            print(f"  {segment:9} {copy_segments.LABEL[segment]:6} {n}")
        if not apply_changes:
            print("\n确认没问题就加 --apply 写入")
            return
        for move in keep:
            conn.execute("UPDATE sequence_enrollments SET sequence_id=? WHERE id=?",
                         (move["to"], move["enrollment_id"]))
        for move in drop:
            conn.execute("DELETE FROM sequence_enrollments WHERE id=?",
                         (move["enrollment_id"],))
        # Enrollments whose lead was deleted. They can never send — `due_queue` joins
        # `leads` — but they sit in the pipeline forever and make every count wrong.
        orphans = conn.execute(
            "DELETE FROM sequence_enrollments WHERE lead_no NOT IN"
            " (SELECT no FROM leads)").rowcount
        # Only sequences nothing points at any more; anything still holding history stays.
        empty = conn.execute(
            "DELETE FROM sequences WHERE channel='email'"
            "   AND id NOT IN (SELECT DISTINCT sequence_id FROM sequence_enrollments)"
            "   AND name NOT IN (%s)"
            % ",".join("?" * (len(copy_segments.SEGMENTS) * 2)),
            [name_for(s, k) for k in (False, True) for s in copy_segments.SEGMENTS],
        ).rowcount
        conn.execute("DELETE FROM sequence_steps WHERE sequence_id NOT IN"
                     " (SELECT id FROM sequences)")
        # After the move, not before: a company two letters into a three-letter
        # sequence that lands on a one-letter one is now parked past the end, and
        # the due queue joins on step_order — it would read "active" and never send.
        closed = close_orphaned_enrollments(conn)
        conn.commit()
        print(f"\n已迁移 {len(keep)}，丢弃重复 {len(drop)}，删除空序列 {empty} 条")
        print(f"移动后已无后续步骤、标记完成 {closed} 个")


if __name__ == "__main__":
    main()
