"""Give every lead an opener, from the material the book already holds (docs/85).

Allen took the company name out of the subject and the body, which was right — a name
in front of the product line is the mark of a mail merge. The cost showed up in
`message_guard`: it counted the company name as a personalisation clue, so first letters
held as impersonal went from 88 to 382 of 1,008. Those 382 have no hook, and without the
name there is nothing in the letter that belongs to them.

380 of them do have a `business` line, written by a person: "LED display & digital
signage solutions", "Outdoor LED screen (since 2004)". That is enough to open with, and
it costs no fetching — `brief.build()` reads a page, this reads the book.

Two constraints shape everything below. The vocabulary can only use terms
`personalize._HOOK_GLOSS_KO` knows, because an unglossed term makes the whole Korean
opener disappear. And the sentence can only take a shape `personalize.hook_ko` matches,
for the same reason.

Run:  python -m app.backfill_hooks
      python -m app.backfill_hooks --apply
"""
from __future__ import annotations

import re
import sys

from app.brief import _place
from app.db import connect

# docs/85 R3. Allen's own v2 line with 贵司 in place of the name, per his instruction:
# 如果正文要说到对方的公司名时可以说，贵司或者你们公司来代替即可.
GENERIC_HOOK = ("I came across your company while looking at LED and AV companies in "
                "your market.")
GENERIC_HOOK_KO = "귀사 관련 내용을 확인하다가 연락드렸습니다."

# Business text -> the term the opener will use. Every value is a key in
# `personalize._HOOK_GLOSS_KO`; a term missing from that table silently empties the
# Korean opener, so this list is checked against it by a test rather than by trust.
# Specific before general: "digital signage" must win over "signage", and a company that
# says both rental and events should read as both rather than twice as one.
_CATEGORY = (
    (r"digital signage|디지털 사이니지", "digital signage"),
    (r"\bOOH\b|out-?of-?home|billboard|옥외\s*광고|광고판", "billboard"),
    (r"\bsignage\b|\bsigns?\b|사이니지", "signage"),
    # An advertising screen is a 전광판. "outdoor advertising" would read the word
    # outdoor into a company that never said it.
    (r"advertis|광고", "LED signage"),
    (r"\brental\b|\brent\b|aluguel|alquiler|렌탈|임대", "rental"),
    (r"\bevent|stage|concert|festival|touring|행사|무대|공연", "events"),
    (r"integrat|\bAV\b|audio.?visual|시스템\s*통합", "AV integration"),
    (r"install|\bfixed\b|시공|설치", "installation"),
    (r"distribut|import|trading|유통|수입", "distribution"),
    (r"wholesale|도매", "wholesale"),
    (r"video ?wall|media ?wall|미디어\s*월|비디오\s*월", "media wall"),
    (r"panel sales|screen sales|판매", "panel sales"),
    (r"led (?:display|screen|panel|sign)|display (?:design|manufact|solution)"
     r"|디스플레이|스크린|패널", "LED panels"),
)
_CATEGORY_RE = tuple((re.compile(p, re.I), term) for p, term in _CATEGORY)


def categories(text: str | None) -> list[str]:
    """Up to two terms this company's own description supports, most specific first.

    Two, not one: "rental and events" already separates most of the companies that
    "rental" alone lumped together, and a hook every competitor also gets is, to a
    platform reading a batch, one identical message (docs/78).
    """
    raw = str(text or "")
    if not raw.strip():
        return []
    found: list[str] = []
    for pattern, term in _CATEGORY_RE:
        if len(found) == 2:
            break
        if not pattern.search(raw):
            continue
        # "signage and digital signage" says one thing twice.
        if any(term in kept or kept in term for kept in found):
            continue
        found.append(term)
    return found


def _join(terms: list[str]) -> str:
    return terms[0] if len(terms) == 1 else " and ".join(terms)


def hook_for(lead: dict) -> str:
    """The opener this lead's own record supports, or the generic one (docs/85 R3).

    Never empty: a lead we know nothing about is a lead Allen has decided to write to
    anyway (docs/80 R2), and the deliberate generic line is how the guard tells that
    apart from a record nobody looked at.
    """
    terms = categories(lead.get("business"))
    if not terms:
        return GENERIC_HOOK
    what = _join(terms)
    # Some rows carry the country in the city column. "around Brazil" is not a thing a
    # person writes, and it is the one part of the sentence that claims local knowledge.
    place = _place(lead.get("city"))
    if place and place.strip().lower() == str(lead.get("country") or "").strip().lower():
        place = ""
    if place:
        return f"Saw the {what} work you do around {place}."
    if str(lead.get("website") or "").strip():
        return f"Saw the {what} work on your site."
    return f"Saw the {what} work you do."


def plan(conn) -> list[dict]:
    """What would be written, for the leads that have no opener at all."""
    out = []
    for row in conn.execute(
            "SELECT no, company_en, country, city, website, business FROM leads"
            " WHERE COALESCE(hook, '') = ''"):
        lead = dict(row)
        out.append({**lead, "hook": hook_for(lead)})
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    apply_changes = "--apply" in sys.argv
    with connect("outreach.db") as conn:
        rows = plan(conn)
        built = [r for r in rows if r["hook"] != GENERIC_HOOK]
        generic = [r for r in rows if r["hook"] == GENERIC_HOOK]
        print(f"没有开场白的 {len(rows)} 家：从业务描述写出 {len(built)}，"
              f"没材料、用通用版 {len(generic)}")
        print()
        for r in built[:20]:
            print(f"  #{r['no']:<5} {str(r['company_en'])[:22]:24} {r['hook']}")
        if len(built) > 20:
            print(f"  …… 另外 {len(built) - 20} 家")
        print(f"\n通用版（韩国读韩文版）的 {len(generic)} 家：")
        for r in generic[:8]:
            print(f"  #{r['no']:<5} {str(r['company_en'])[:22]:24} "
                  f"business={str(r['business'] or '')[:40]!r}")
        if not apply_changes:
            print("\n确认没问题就加 --apply 写入")
            return
        for r in rows:
            conn.execute("UPDATE leads SET hook=? WHERE no=?", (r["hook"], r["no"]))
        conn.commit()
        print(f"\n已写入 {len(rows)} 家")


if __name__ == "__main__":
    main()
