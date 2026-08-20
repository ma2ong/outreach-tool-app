"""Infer a contact's buying role from the job title we already scraped.

The readiness centre has been asking for decision-makers for weeks, and the data to
answer it was already sitting there: 28 contacts carry a title, and most of them say
CEO or 대표 in plain words. This reads those titles; it never guesses from a name, an
email address or a company.

Two rules keep it honest:

- A role Allen set by hand is never overwritten. Only contacts still on the default
  `other` are considered, so re-running this can correct its own past mistakes but
  cannot undo his.
- An unrecognised title stays `other`. "Sales" at a distributor is our counterpart, not
  necessarily the person who signs — guessing decision-maker there would put a
  confident label on a coin flip, and the whole point of the field is to be trusted.

Run:  python -m app.contact_roles            # preview only
      python -m app.contact_roles --apply    # write the roles
"""
from __future__ import annotations

import re
import sys

from app.db import connect

# Ordered: the first table whose word appears in the title wins, so "sales director"
# lands on sales rather than director.
ROLE_WORDS: list[tuple[str, tuple[str, ...]]] = [
    ("finance", (
        "cfo", "finance", "financial", "accounting", "accountant", "controller",
        "재무", "회계", "finanzas", "financeiro", "contabilidad",
    )),
    ("technical", (
        "cto", "engineer", "engineering", "technical", "technician", "technology",
        "기술", "엔지니어", "ingeniero", "ingeniería", "técnico", "tecnico",
    )),
    ("influencer", (
        "sales", "commercial", "business development", "marketing", "account manager",
        "rentals", "rental", "operations", "project manager",
        "영업", "마케팅", "ventas", "comercial", "vendas", "mercadeo",
    )),
    ("decision_maker", (
        "ceo", "coo", "owner", "owners", "founder", "founders", "co founder",
        "president", "chairman",
        "managing director", "general manager", "managing partner", "principal",
        "proprietor", "director", "partner", "head of", "vp", "vice president",
        "purchasing", "procurement", "buyer", "sourcing",
        "대표", "사장", "회장", "이사", "구매",
        "gerente general", "director general", "propietario", "dueño", "socio",
        "proprietário", "diretor", "sócio",
    )),
]

_NON_WORD = re.compile("[^a-z0-9]+")


def _padded(text: str) -> str:
    """Lowercased, punctuation flattened to single spaces, padded at both ends so a
    whole word can be tested by simple containment."""
    return " " + _NON_WORD.sub(" ", (text or "").lower()).strip() + " "


def _matches(word: str, padded_title: str, raw_title: str) -> bool:
    """Whole-word for Latin script, substring for CJK.

    Substring matching alone read "Director of Sales" as technical, because
    "dire(cto)r" contains "cto" — and "Coordinator" contains "coo". CJK has no word
    boundaries to anchor on, so 대표 and 구매 stay substring matches.
    """
    if not word.isascii():
        return word in raw_title
    return _padded(word) in padded_title


def role_for(title: str | None) -> str:
    """The role this title states, or 'other' when it does not state one."""
    raw = (title or "").strip().lower()
    if not raw:
        return "other"
    padded = _padded(raw)
    for role, words in ROLE_WORDS:
        if any(_matches(w, padded, raw) for w in words):
            return role
    return "other"


def candidates(conn) -> list[dict]:
    """Contacts with a title that are still on the default role."""
    return [dict(r) for r in conn.execute(
        "SELECT c.id, c.lead_no, c.name, c.title, c.role, l.company_en"
        " FROM contacts c JOIN leads l ON l.no=c.lead_no"
        " WHERE c.title IS NOT NULL AND c.title != '' AND c.role='other'"
        " ORDER BY c.id")]


def run(conn, apply: bool = False) -> list[dict]:
    rows = []
    for c in candidates(conn):
        role = role_for(c["title"])
        if role == "other":
            continue
        rows.append({**c, "new_role": role})
        if apply:
            conn.execute("UPDATE contacts SET role=? WHERE id=?", (role, c["id"]))
    if apply and rows:
        conn.commit()
    return rows


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    apply = "--apply" in sys.argv
    conn = connect("outreach.db")
    try:
        rows = run(conn, apply=apply)
        skipped = [c for c in candidates(conn) if role_for(c["title"]) == "other"]
    finally:
        conn.close()
    for r in rows:
        print(f"  {(r['name'] or '(无名)')[:22]:<22} {(r['title'] or '')[:28]:<28}"
              f" → {r['new_role']}   {r['company_en'][:22]}")
    if skipped:
        print("\n认不出、保持 other 的职位：")
        for c in skipped:
            print(f"  {(c['name'] or '(无名)')[:22]:<22} {c['title']}")
    print(f"\n可标记 {len(rows)} 位，" + ("已写入" if apply else "以上仅预览，加 --apply 才写入"))


if __name__ == "__main__":
    main()
