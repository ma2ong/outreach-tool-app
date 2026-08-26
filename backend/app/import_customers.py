"""Bring in customers Allen already worked, without treating them as strangers.

The system writes a first cold email to every untouched lead each morning, opening with
"Saw the rental work you do around Houston. We manufacture LED panels." Importing a
customer he quoted in 2023 as *untouched* means that mail goes out tomorrow, and from
their side it reads as a supplier who has forgotten who they are. That is worse than
never having written: a stranger is merely unknown, this erases a relationship.

So the hard part here is not reading a spreadsheet. It is that every judgement call
leans the safe way (see `docs/54`):

- unknown contact history means *already contacted*, never *fresh lead*
- an existing record wins over an imported one, except where the field is empty
- a column we cannot identify is preserved as a note, not guessed into a field

Run:  python -m app.import_customers <file.xlsx|file.csv>            # preview only
      python -m app.import_customers <file.xlsx|file.csv> --apply    # write
"""
from __future__ import annotations

import csv
import datetime as dt
import sys
from pathlib import Path

from app import repository as repo
from app.db import connect

DB = "outreach.db"

# Xiaoman's export columns are chosen at export time and may be in either language, so
# match on meaning rather than on an exact sheet.
_HEADERS: dict[str, tuple[str, ...]] = {
    "company_en": ("公司名称", "客户名称", "公司名", "客户", "company", "company name",
                   "customer", "customer name", "account", "account name"),
    "contact_name": ("联系人", "联系人姓名", "客户联系人", "contact", "contact name",
                     "contact person", "name"),
    "email": ("邮箱", "邮件", "电子邮箱", "联系邮箱", "email", "e-mail", "mail"),
    "phone": ("电话", "手机", "联系电话", "手机号", "phone", "tel", "telephone", "mobile",
              "whatsapp"),
    "website": ("网站", "官网", "公司网站", "website", "web", "site", "url", "homepage"),
    "country": ("国家", "国家地区", "country", "nation"),
    "city": ("城市", "地区", "city", "region", "province", "state"),
    "status": ("状态", "客户状态", "阶段", "客户阶段", "跟进状态", "status", "stage"),
    "last_contact": ("最后联系时间", "最后跟进时间", "最近联系", "跟进时间", "联系日期",
                     "last contact", "last contacted", "last follow up", "last activity"),
    "business": ("备注", "客户备注", "说明", "描述", "note", "notes", "remark", "remarks",
                 "description"),
}
_BY_HEADER = {alias: field for field, aliases in _HEADERS.items() for alias in aliases}

# Words a CRM uses for the end of a relationship, in either direction.
_WON = ("成交", "已成交", "赢单", "签约", "won", "closed won", "customer")
_LOST = ("丢单", "输单", "失败", "已流失", "lost", "closed lost")
_BLOCKED = ("黑名单", "拒绝", "不再联系", "blacklist", "do not contact", "dnc", "unsubscribed")


def _key(header: str) -> str:
    return str(header or "").strip().lower().replace("_", "").replace(" ", "")


def map_rows(rows: list[dict]) -> list[dict]:
    """Turn sheet rows into lead-shaped dicts, keeping what we could not identify.

    An unrecognised column is not dropped and not guessed at: it goes into the notes
    field, where it stays readable without pretending to be structured data.
    """
    lookup = {_key(alias): field for alias, field in _BY_HEADER.items()}
    mapped: list[dict] = []
    for row in rows:
        out: dict[str, str] = {}
        extras: list[str] = []
        for header, value in row.items():
            text = str(value).strip() if value is not None else ""
            if not text:
                continue
            field = lookup.get(_key(header))
            if field == "business":
                extras.append(text)
            elif field:
                out.setdefault(field, text)
            else:
                extras.append(f"{str(header).strip()}：{text}")
        if extras:
            out["business"] = " · ".join(extras)
        mapped.append(out)
    return mapped


def _match(conn, row: dict) -> int | None:
    """An existing lead this row is about, by email, then website, then company name."""
    from app.dedupe import normalize_website

    email = (row.get("email") or "").strip().lower()
    if email:
        hit = conn.execute("SELECT no FROM leads WHERE lower(email)=?", (email,)).fetchone()
        if hit:
            return hit["no"]
    site = normalize_website(row.get("website") or "")
    if site:
        hit = conn.execute(
            "SELECT no FROM leads WHERE lower(replace(replace(website,'https://',''),"
            "'http://','')) LIKE ?", (f"{site}%",)).fetchone()
        if hit:
            return hit["no"]
    company = (row.get("company_en") or "").strip().lower()
    if company:
        hit = conn.execute(
            "SELECT no FROM leads WHERE lower(company_en)=?", (company,)).fetchone()
        if hit:
            return hit["no"]
    return None


def _usable(row: dict) -> bool:
    """A customer needs a name or a way to reach them; a note on its own is neither."""
    return bool((row.get("company_en") or "").strip()
                or (row.get("email") or "").strip()
                or (row.get("phone") or "").strip())


def _relationship(row: dict) -> tuple[str, bool]:
    """(stage, do_not_contact) read from whatever the CRM called the status column."""
    text = (row.get("status") or "").strip().lower()
    if any(word in text for word in _BLOCKED):
        return "lost", True
    if any(word in text for word in _WON):
        return "won", False
    if any(word in text for word in _LOST):
        return "lost", False
    return "contacted", False


def preview(conn, rows: list[dict]) -> dict:
    """What an import would do, without doing any of it."""
    created = merged = skipped = 0
    for row in rows:
        if not _usable(row):
            skipped += 1
        elif _match(conn, row) is not None:
            merged += 1
        else:
            created += 1
    return {"created": created, "merged": merged, "skipped": skipped, "total": len(rows)}


_FILLABLE = ("email", "phone", "website", "country", "city", "contact_name", "business")


def apply(conn, rows: list[dict], today: dt.date | None = None) -> dict:
    """Write the rows in. Existing records win; imported customers count as contacted."""
    today = today or dt.date.today()
    created = merged = skipped = 0
    for row in rows:
        if not _usable(row):
            skipped += 1
            continue
        stage, blocked = _relationship(row)
        contacted_on = (row.get("last_contact") or "").strip()
        existing = _match(conn, row)
        if existing is not None:
            # Only fill blanks. The CRM export may be years old, while this record may
            # have been read off the company's own site last month.
            current = conn.execute("SELECT * FROM leads WHERE no=?", (existing,)).fetchone()
            patch = {field: row[field] for field in _FILLABLE
                     if row.get(field) and not (current[field] if field in current.keys() else None)}
            if blocked and not current["do_not_contact"]:
                patch["do_not_contact"] = 1
            if patch:
                repo.update_lead(conn, existing, patch)
            merged += 1
            no = existing
        else:
            no = repo.insert_lead(conn, {
                "company_en": row.get("company_en") or row.get("email") or row.get("phone"),
                "country": row.get("country"), "city": row.get("city"),
                "email": row.get("email"), "phone": row.get("phone"),
                "website": row.get("website"), "business": row.get("business"),
            })
            # stage / contact_name / do_not_contact are not insertable columns; they go
            # through the edit path, which is also the one that stamps provenance.
            repo.update_lead(conn, no, {
                "stage": stage, "contact_name": row.get("contact_name"),
                "do_not_contact": 1 if blocked else 0,
            })
            created += 1

        # The relationship has to land in `outreach`: send eligibility, the sequences and
        # the daily report all read that table, so a stage on `leads` alone would still
        # let a cold sequence pick this customer up.
        for channel, address in (("email", row.get("email")), ("whatsapp", row.get("phone"))):
            if not address:
                continue
            conn.execute(
                "INSERT INTO outreach(lead_no, channel, status, touch_count, message_sent_date)"
                " VALUES (?, ?, 'messaged', 1, ?)"
                " ON CONFLICT(lead_no, channel) DO UPDATE SET"
                "   status=CASE WHEN outreach.status IN ('prospect','') THEN 'messaged'"
                "               ELSE outreach.status END",
                (no, channel, contacted_on or today.isoformat()))
        if not contacted_on:
            # Recording today as the contact date would be inventing a fact (spec 45).
            repo.add_note(conn, no, f"从小满 CRM 导入（日期未知，按导入日 {today.isoformat()} 计）"
                                    "：这是一位已开发过的客户，不会再收到首封开发信。")
        else:
            repo.add_note(conn, no, f"从小满 CRM 导入，最后联系 {contacted_on}")
    conn.commit()
    return {"created": created, "merged": merged, "skipped": skipped, "total": len(rows)}


def read_file(path: str) -> list[dict]:
    """Rows from a .csv or .xlsx export, headers as written."""
    source = Path(path)
    if source.suffix.lower() in (".xlsx", ".xlsm"):
        from openpyxl import load_workbook

        book = load_workbook(source, read_only=True, data_only=True)
        sheet = book.active
        rows = sheet.iter_rows(values_only=True)
        headers = [str(h).strip() if h is not None else "" for h in next(rows, [])]
        return [dict(zip(headers, values)) for values in rows]
    with source.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main(path: str, apply_it: bool) -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = map_rows(read_file(path))
    conn = connect(DB)
    plan = preview(conn, rows)
    print(f"读到 {plan['total']} 行：新建 {plan['created']}，"
          f"补充已有 {plan['merged']}，跳过 {plan['skipped']}（没有公司名也没有联系方式）")
    for row in rows[:5]:
        named = "，".join(f"{k}={v}" for k, v in row.items() if k != "business")
        print(f"  · {named[:110]}")
    print("\n所有导入的客户都会标记为「已触达」，不会再收到首封开发信。")
    if not apply_it:
        print("预览模式，未写入。加 --apply 执行")
        return
    result = apply(conn, rows)
    print(f"已导入：新建 {result['created']}，补充 {result['merged']}，跳过 {result['skipped']}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("用法：python -m app.import_customers <文件> [--apply]")
    else:
        main(args[0], "--apply" in sys.argv)
