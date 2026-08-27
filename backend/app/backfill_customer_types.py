"""Write the classifier's verdict into the customer type column (docs/64).

The DMs going out today say "Saw the rental and staging work you do around Houston",
which means the system already decided what these companies do. The 客户类型 column was
blank for them anyway, because the decision was only ever stored in the classifier's own
words — `icp:rental`, 191 of them.

This translates what is already known into Allen's vocabulary. It reads nothing new and
decides nothing new: a lead with no classifier verdict stays blank, and a lead whose type
he set stays exactly as he set it.

Run:  python -m app.backfill_customer_types            # preview only
      python -m app.backfill_customer_types --apply    # write
"""
from __future__ import annotations

import sys
from collections import Counter

from app import customer_types
from app.db import connect


def plan(conn) -> list[tuple[int, str, str]]:
    """(lead_no, company, type to add) for every lead the classifier can speak for."""
    out = []
    for row in conn.execute(
            "SELECT no, company_en, tags, types_edited_at FROM leads"):
        derived = customer_types.derive(row["tags"], row["types_edited_at"])
        if derived:
            out.append((row["no"], row["company_en"] or "", derived))
    return out


def apply(conn, rows: list[tuple[int, str, str]]) -> int:
    for no, _company, derived in rows:
        current = conn.execute("SELECT tags FROM leads WHERE no=?", (no,)).fetchone()["tags"]
        tags = customer_types.split_tags(current)
        # In front, so the human-readable type is what the column shows first.
        conn.execute("UPDATE leads SET tags=? WHERE no=?",
                     (",".join([derived, *tags]), no))
    conn.commit()
    return len(rows)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    apply_changes = "--apply" in sys.argv
    with connect("outreach.db") as conn:
        rows = plan(conn)
        counts = Counter(t for _no, _c, t in rows)
        total = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        already = sum(1 for r in conn.execute("SELECT tags FROM leads")
                      if customer_types.customer_types(r["tags"]))
        print(f"客户库 {total} 家，已有客户类型 {already} 家")
        print(f"可以从分类器判断补上的：{len(rows)} 家")
        for name, n in counts.most_common():
            print(f"    {n:5} {name}")
        print(f"补完之后有类型的：{already + len(rows)} 家")
        print()
        for no, company, derived in rows[:8]:
            print(f"    #{no:5} {company[:30]:32} -> {derived}")
        if len(rows) > 8:
            print(f"    …… 其余 {len(rows) - 8} 家")
        if apply_changes:
            print(f"\n已写入 {apply(conn, rows)} 家")
        else:
            print("\n确认没问题就加 --apply 写入")


if __name__ == "__main__":
    main()
