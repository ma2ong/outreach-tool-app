"""Repair leads whose company_en is a page title rather than a company.

`enrich.extract_company_name` refuses generic titles now, but records imported before
that guard still carry names like "Contact" and "Page not found". They are not junk
records — every one of them has a real website and real contacts — so the fix is a
rename, never a delete.

Two passes per lead: read the site for its actual name, and fall back to the domain if
the site will not say. A lead called after its own domain is honest; one called
"Contact" looks like a real answer and is not.

Run:  python -m app.fix_junk_names            # preview only
      python -m app.fix_junk_names --apply    # write the names
"""
from __future__ import annotations

import re
import sys

from app.db import connect
from app.enrich import extract_company_name
from app.jina import fetch
from app.sales_intelligence import _junk_company_name

_STRIP_WWW = re.compile(r"^www\.", re.I)
_SCHEME = re.compile(r"^https?://", re.I)


def domain_of(website: str | None) -> str:
    host = _STRIP_WWW.sub("", _SCHEME.sub("", (website or "").strip())).split("/")[0]
    return host.strip().lower()


def name_from_domain(website: str | None) -> str:
    """Last resort. 'blipbillboards.com' -> 'Blipbillboards'. Ugly beats misleading."""
    host = domain_of(website)
    if not host:
        return ""
    label = host.split(".")[0].replace("-", " ").replace("_", " ").strip()
    return " ".join(w.capitalize() for w in label.split()) if label else ""


# A company name is a name. Half the titles read back were marketing lines —
# "Self-Serve Digital Billboard Advertising Platform" for blipbillboards.com — and a
# tagline in the company column misleads exactly the way "Contact" does. Anything
# longer than a name gets dropped in favour of the domain.
MAX_NAME_WORDS = 4
MAX_NAME_CHARS = 40


def looks_like_a_name(value: str) -> bool:
    text = (value or "").strip()
    if not text or len(text) > MAX_NAME_CHARS:
        return False
    return len(text.split()) <= MAX_NAME_WORDS


def candidates(conn) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT no, company_en, website, country FROM leads ORDER BY no")
        if _junk_company_name(r["company_en"])]


def resolve(lead: dict, fetch_fn=fetch) -> tuple[str, str]:
    """(new name, where it came from). Empty name means leave this one alone."""
    host = domain_of(lead.get("website"))
    if host:
        try:
            found = extract_company_name(fetch_fn(f"https://{host}"))
        except Exception:  # noqa: BLE001 — a dead or shielded site falls back, not fails
            found = None
        if found and looks_like_a_name(found):
            return found.strip(), "官网标题"
    fallback = name_from_domain(lead.get("website"))
    return (fallback, "域名") if fallback else ("", "")


def run(conn, apply: bool = False, fetch_fn=fetch) -> list[dict]:
    rows = []
    for lead in candidates(conn):
        new_name, source = resolve(lead, fetch_fn)
        rows.append({**lead, "new_name": new_name, "source": source})
        if not apply or not new_name or new_name == lead["company_en"]:
            continue
        conn.execute("UPDATE leads SET company_en=? WHERE no=?", (new_name, lead["no"]))
        # The old value stays readable: a rename nobody can trace is its own problem.
        conn.execute(
            "INSERT INTO notes(lead_no, created_at, text) VALUES (?, datetime('now'), ?)",
            (lead["no"], f"公司名修复：「{lead['company_en']}」→「{new_name}」（来源：{source}）"))
        conn.commit()
    return rows


def main() -> None:
    try:  # the Windows console is not UTF-8 by default and this output is Chinese
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    apply = "--apply" in sys.argv
    conn = connect("outreach.db")
    try:
        rows = run(conn, apply=apply)
    finally:
        conn.close()
    if not rows:
        print("没有需要修复的公司名")
        return
    for r in rows:
        arrow = f"→ {r['new_name']}（{r['source']}）" if r["new_name"] else "→ 无法确定，跳过"
        print(f"#{r['no']:>4} {r['company_en'][:30]:<30} {arrow}")
    print(f"\n共 {len(rows)} 条，"
          + ("已写入" if apply else "以上仅预览，加 --apply 才写入"))


if __name__ == "__main__":
    main()
