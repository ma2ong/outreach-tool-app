"""Store every phone number the way we would dial it (docs/83 R2).

The calling code used to be added in memory at send time, so the book held numbers Allen
could not dial from the number he was looking at, and a wrong one only announced itself
when a message failed. This writes the international form back.

Nothing is guessed. A row whose country we do not know, whose national part is the wrong
length, or whose range does not route from abroad is listed under 「补不了」 and left
exactly as it was — the lesson of `fix_invented_country_codes`, which existed to undo a
'+' that had been added to everything.

Run:  python -m app.backfill_phone_codes
      python -m app.backfill_phone_codes --apply
"""
from __future__ import annotations

import re
import sys

from app.db import connect
from app.phone_format import parts, book_form, international


def plan(conn) -> tuple[list[dict], list[dict]]:
    """(what would change, what holds a number we cannot show internationally).

    A row already written as +55… needs no change and is not a problem; listing it
    beside a row holding a date would make the second list unreadable, which is the
    only reason anyone opens it.
    """
    changes, stuck = [], []
    for row in conn.execute(
            "SELECT no, company_en, country, phone FROM leads"
            " WHERE phone IS NOT NULL AND TRIM(phone) != ''"):
        item = {"no": row["no"], "company_en": row["company_en"],
                "country": row["country"], "phone": row["phone"]}
        fixed = book_form(row["phone"], row["country"])
        if fixed is not None and fixed != row["phone"]:
            changes.append({**item, "fixed": fixed})
        current = fixed if fixed is not None else row["phone"]
        if any(international(part, row["country"]) is None
               for part in parts(current) if re.search(r"\d", part)):
            stuck.append(item)
    return changes, stuck


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    apply_changes = "--apply" in sys.argv
    with connect("outreach.db") as conn:
        changes, stuck = plan(conn)
        print(f"要补成国际格式的 {len(changes)} 家：")
        for c in changes[:25]:
            print(f"  #{c['no']:<5} {str(c['country'] or ''):12} {c['phone']!r} -> {c['fixed']!r}")
        if len(changes) > 25:
            print(f"  …… 另外 {len(changes) - 25} 家")
        print(f"\n补不了、原样保留的 {len(stuck)} 家：")
        for c in stuck[:15]:
            print(f"  #{c['no']:<5} {str(c['country'] or '(无国家)'):12} {c['phone']!r}")
        if len(stuck) > 15:
            print(f"  …… 另外 {len(stuck) - 15} 家")
        if not apply_changes:
            print("\n确认没问题就加 --apply 写入")
            return
        for c in changes:
            conn.execute("UPDATE leads SET phone=? WHERE no=?", (c["fixed"], c["no"]))
        conn.commit()
        print(f"\n已写入 {len(changes)} 家")


if __name__ == "__main__":
    main()
