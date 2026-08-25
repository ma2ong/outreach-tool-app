"""Undo the phone numbers that enrich gave an invented country code.

`extract_phones` used to prefix every number it found with '+', including local ones
written as `tel:877.773.4346`. The book therefore holds numbers like '+8777734346':
undialable, and read back by `screening` as a country the company is not in.

A number is repaired only when its digits start with no calling code we know — that is
proof the '+' was invented rather than read. '+1...' and every real code are left alone,
because there the '+' may well be genuine.

Run:  python -m app.fix_invented_country_codes            # preview only
      python -m app.fix_invented_country_codes --apply    # write the numbers
"""
from __future__ import annotations

import sys

from app import screening
from app.db import connect

DB = "outreach.db"


def is_invented(phone: str | None) -> bool:
    """True when the leading '+' cannot belong to any calling code, incl. NANP '1'."""
    raw = (phone or "").strip()
    if not raw.startswith("+"):
        return False
    digits = "".join(ch for ch in raw if ch.isdigit())
    if digits.startswith("1"):
        return False
    return not any(digits.startswith(code) for code in screening._CODES_BY_LEN)


def local_form(phone: str) -> str:
    """'+7472624770' -> '747-262-4770'. Ten digits is North America; anything else
    keeps its digits unseparated rather than being grouped by guesswork."""
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return digits


def repairs(conn) -> list[dict]:
    out = []
    for row in conn.execute(
            "SELECT no, company_en, country, phone FROM leads WHERE phone LIKE '+%'"):
        if is_invented(row["phone"]):
            out.append({"no": row["no"], "company_en": row["company_en"],
                        "phone": row["phone"], "fixed": local_form(row["phone"])})
    return out


def suspects(conn) -> list[dict]:
    """Numbers whose invented '+' cannot be proven, only suspected.

    A Houston number stored as '+3468378628' reads as Spain (+34), and no rule
    separates it from a real Spanish number: '+82 2 510-2000' is a genuine Korean
    line with the same shape. So these are reported for a human to look at, never
    rewritten — a wrong number costs a call, a wrongly rewritten one costs the lead.
    """
    out = []
    for row in conn.execute(
            "SELECT no, company_en, country, phone FROM leads"
            " WHERE phone LIKE '+%' AND COALESCE(country,'') != ''"):
        from_phone = screening._country_from_phone(row["phone"])
        if from_phone and from_phone != row["country"]:
            out.append({"no": row["no"], "company_en": row["company_en"],
                        "country": row["country"], "phone": row["phone"],
                        "reads_as": from_phone})
    return out


def main(apply: bool) -> None:
    # A Chinese line printed to a GBK console raises, and the repair below would never
    # run — the failure mode this script hit on its first real invocation.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = connect(DB)
    found = repairs(conn)
    for row in found:
        print(f"#{row['no']:<5} {row['company_en'][:34]:<34} {row['phone']} -> {row['fixed']}")
    print(f"\n{len(found)} 个号码带着编造的国家码")
    review = suspects(conn)
    if review:
        print(f"\n另有 {len(review)} 条电话与记录国家不符，需人工确认（不自动改）：")
        for row in review:
            print(f"#{row['no']:<5} {row['company_en'][:30]:<30} 记录 {row['country']:<12}"
                  f" 电话 {row['phone']} 读作 {row['reads_as']}")
    if not apply:
        print("预览模式，未写入。加 --apply 执行")
        return
    for row in found:
        conn.execute("UPDATE leads SET phone=? WHERE no=? AND phone=?",
                     (row["fixed"], row["no"], row["phone"]))
        conn.execute("UPDATE contacts SET phone=? WHERE lead_no=? AND phone=?",
                     (row["fixed"], row["no"], row["phone"]))
    conn.commit()
    print(f"已修正 {len(found)} 个号码")


if __name__ == "__main__":
    main("--apply" in sys.argv)
