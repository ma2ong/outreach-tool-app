"""Rewrite hooks that several companies share, using material already on the record.

A hook is the one line in a cold message that is about the recipient. 579 leads carried a
hook that at least one other lead had word for word, and 336 of them shared exactly
"Saw the rental work on your site." — because the generator took the first matched
keyword and stopped, and never looked at the city sitting in the next column.

To a person that reads as a generic opener. To a platform receiving a batch of DMs that
differ only in the handle, it reads as one message sent many times, which is the thing
`docs/52` R6 exists to prevent.

This rewrites only the collapsed ones and only from data already stored: the city, and
the second keyword the brief already quoted. Nothing is fetched, so it costs nothing and
cannot introduce a fact the site did not state. A lead whose hook is already unique is
left alone.

Run:  python -m app.refresh_hooks            # preview only
      python -m app.refresh_hooks --apply    # write the hooks
"""
from __future__ import annotations

import re
import sys
from collections import Counter

from app.brief import _place
from app.db import connect

DB = "outreach.db"

# "The site mentions "locação" (rental) and "eventos" (events)." — the glossed nouns are
# what the hook is allowed to say, and the brief already picked and vetted them.
_GLOSSED = re.compile(r'"[^"]+"\s*\(([^)]+)\)')
_PLAIN = re.compile(r'"([^"]+)"(?!\s*\()')
_HOOK_TAIL = " work on your site."
_HOOK_HEAD = "Saw the "


def _second_term(brief: str | None, first: str) -> str:
    """Another category this site named, if the brief kept one that the hook dropped."""
    text = str(brief or "")
    for term in [*_GLOSSED.findall(text), *_PLAIN.findall(text)]:
        term = term.strip()
        if not term or term.lower() == first.lower():
            continue
        # An overlapping pair says one thing twice ("signage and digital signage").
        if term.lower() in first.lower() or first.lower() in term.lower():
            continue
        return term
    return ""


def rewrite(hook: str, city: str | None, brief: str | None) -> str:
    """A more specific version of `hook`, or the original when there is nothing to add."""
    if not hook.startswith(_HOOK_HEAD) or not hook.endswith(_HOOK_TAIL):
        return hook  # a pitch-based hook is already the most distinctive kind
    first = hook[len(_HOOK_HEAD):-len(_HOOK_TAIL)]
    second = _second_term(brief, first)
    place = _place(city)
    subject = f"{first} and {second}" if second else first
    if place:
        return f"{_HOOK_HEAD}{subject} work you do around {place}."
    if second:
        return f"{_HOOK_HEAD}{subject}{_HOOK_TAIL}"
    return hook


def collisions(conn) -> list[dict]:
    """Leads whose hook is not theirs alone, with the rewrite each would get."""
    from app import hook_writer

    hook_writer.ensure_schema(conn)
    rows = conn.execute(
        "SELECT no, company_en, city, hook, brief, hook_quote FROM leads"
        " WHERE COALESCE(hook,'') != ''").fetchall()
    shared = {h for h, n in Counter(r["hook"] for r in rows).items() if n > 1}
    out = []
    for row in rows:
        if row["hook"] not in shared:
            continue
        # docs/93 R5：出处比「和别家撞车」更重要。这个改写器是从书里已有材料重写塌陷的
        # 通用句，它没有资格覆盖一句能追溯到客户官网原文的开场白。
        if str(row["hook_quote"] or "").strip():
            continue
        fresh = rewrite(row["hook"], row["city"], row["brief"])
        if fresh != row["hook"]:
            out.append({"no": row["no"], "company_en": row["company_en"],
                        "old": row["hook"], "new": fresh})
    return out


def main(apply: bool) -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = connect(DB)
    before = Counter(r["hook"] for r in conn.execute(
        "SELECT hook FROM leads WHERE COALESCE(hook,'') != ''"))
    shared_before = sum(n for n in before.values() if n > 1)

    changes = collisions(conn)
    for row in changes[:15]:
        print(f"#{row['no']:<5} {row['company_en'][:26]:26}")
        print(f"      旧: {row['old']}")
        print(f"      新: {row['new']}")
    if len(changes) > 15:
        print(f"... 另外 {len(changes) - 15} 家")

    after = Counter(before)
    for row in changes:
        after[row["old"]] -= 1
        after[row["new"]] += 1
    shared_after = sum(n for n in after.values() if n > 1)
    print(f"\n可改写 {len(changes)} 家；与别家撞车的客户 {shared_before} → {shared_after}")

    if not apply:
        print("预览模式，未写入。加 --apply 执行")
        return
    for row in changes:
        conn.execute("UPDATE leads SET hook=? WHERE no=? AND hook=?",
                     (row["new"], row["no"], row["old"]))
    conn.commit()
    print(f"已改写 {len(changes)} 家的开场白")


if __name__ == "__main__":
    main("--apply" in sys.argv)
