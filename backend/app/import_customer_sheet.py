"""Bring in the customer sheet Allen keeps by hand.

`客户资料表.xlsx` is not a CRM export. `import_customers` (docs/54) reads 小满's export,
where every row is a customer he already worked, and it marks the lot as contacted. Most
rows in *this* sheet are the opposite: companies he researched and has never written to.
Running them through that importer would lock 236 leads out of the cold queue for good,
so this is a second reader with the opposite default (docs/118).

What the sheet says, it says in Chinese prose in a 备注 column — including the two
instructions that must never be got wrong: 只入库不联系, and "write from my own gmail and
do not name the company". Both end in `do_not_contact=1`; the second one also lands in the
import report, because the thing it asks for is something the sender cannot do.

Run:  python -m app.import_customer_sheet "客户资料表 .xlsx"           # preview only
      python -m app.import_customer_sheet "客户资料表 .xlsx" --apply   # write
"""
from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

from app import blocklist, contacts as contacts_mod, repository as repo
from app.db import connect
from app.dedupe import normalize_website

DB = "outreach.db"

# His own mailbox appears in the 备注 of five rows as an instruction about how to write to
# them. It is never a customer address (docs/118 R2).
ALLEN_MAILBOX = "allenma2ong@gmail.com"

_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9][A-Za-z0-9.\-]*\.[A-Za-z]{2,}")
_HANGUL = re.compile(r"[가-힣]")
_URL = re.compile(r"https?://[^\s,，、;；)]+")
_LATIN = re.compile(r"[A-Za-z]")

# The instruction words, read in this order: a row that says 继续联系 means it, even when
# the same sentence also says 成交客户 (docs/118 R1).
_KEEP_CONTACTING = ("继续联系",)
_DO_NOT_CONTACT = ("只入库不联系", "成交客户", "我的合作客户", "合作客户")

_SHEET = "《客户资料表》"


def _text(value) -> str:
    return "" if value is None else str(value).strip()


def read_sheet(path: str) -> list[dict]:
    """Rows of the first sheet, keyed by header. Unlabelled columns keep their position."""
    from openpyxl import load_workbook

    book = load_workbook(Path(path), read_only=True, data_only=True)
    rows = book.worksheets[0].iter_rows(values_only=True)
    headers = [_text(h) or f"col{i}" for i, h in enumerate(next(rows, []))]
    out = []
    for values in rows:
        row = {headers[i]: _text(v) for i, v in enumerate(values) if i < len(headers)}
        if any(row.values()):
            out.append(row)
    return out


def _emails(*texts: str) -> list[str]:
    seen: list[str] = []
    for text in texts:
        for hit in _EMAIL.findall(text or ""):
            address = hit.strip(" '\"<>.,;").lower()
            if address != ALLEN_MAILBOX and address not in seen:
                seen.append(address)
    return seen


def _social(*texts: str) -> dict:
    """instagram / facebook / linkedin handles out of whatever links the row carries."""
    from app.quick_add import BadUrl, parse_url

    found: dict[str, str] = {}
    for text in texts:
        for url in _URL.findall(text or ""):
            try:
                fields = parse_url(url)
            except BadUrl:
                continue
            for key, value in fields.items():
                if key != "website":
                    found.setdefault(key, value)
    return found


def _instruction(*texts: str) -> tuple[bool, str]:
    """(do_not_contact, the sentence that says so) — 继续联系 wins over every other word."""
    joined = " ".join(t for t in texts if t)
    if any(word in joined for word in _KEEP_CONTACTING):
        return False, ""
    if ALLEN_MAILBOX in joined:
        return True, "备注要求用 Allen 私人邮箱、且不署公司名 —— 自动发送做不到，留给手工处理"
    for word in _DO_NOT_CONTACT:
        if word in joined:
            return True, f"备注写着「{word}」"
    return False, ""


def _names(company: str, short: str) -> tuple[str, str | None]:
    """(company_en, company_local). Korean names live in company_local (docs/118 R5)."""
    # 「(주)컴텔싸인_成交客户」 — the instruction was written into the name. Strip it, or the
    # Korean letter opens by calling them 成交客户.
    company = re.sub(r"[（(_\s]*成交客户[)）]*\s*$", "", company).strip(" _")
    short = "" if "@" in short else short
    if _HANGUL.search(company):
        english = short if _LATIN.search(short) else ""
        return (english or company), company
    return company, (short if _HANGUL.search(short) else None)


def parse_row(row: dict) -> dict | None:
    """One sheet row as a lead-shaped record, or None when there is nothing to file."""
    company = _text(row.get("公司名称"))
    short = _text(row.get("公司简称"))
    remark = _text(row.get("备注"))
    contact_remark = _text(row.get("联系人备注"))

    emails = _emails(_text(row.get("联系人邮箱")), contact_remark, short)
    company_en, company_local = _names(company, short)
    if not company_en and not emails:
        return None

    blocked, reason = _instruction(remark, contact_remark, company)
    country_cell = _text(row.get("国家地区"))
    social = _social(_text(row.get("Facebook")), _text(row.get("instagram")), contact_remark)
    for key, cell in (("facebook", "Facebook"), ("instagram", "instagram")):
        raw = _text(row.get(cell))
        if raw and key not in social and "://" not in raw:
            social[key] = raw.split("：")[-1].strip()

    # Everything the sheet says that no field can hold. Guessing a Korean street address
    # into `city` would be inventing structure; the note keeps it readable (docs/118 R6).
    lines = []
    for label, value in (("备注", remark), ("联系人备注", contact_remark),
                         ("地址", _text(row.get("col18")) or _text(row.get("详细地址"))),
                         ("小满", _text(row.get("col16"))),
                         ("是否取得联系", _text(row.get("是否取得联系"))),
                         ("原国家地区", country_cell if "/" in country_cell else "")):
        if value:
            lines.append(f"{label}：{value}")

    return {
        "company_en": company_en or emails[0],
        "company_local": company_local,
        "country": country_cell.split("/")[0],
        "website": _text(row.get("公司网址")),
        "email": emails[0] if emails else "",
        "emails": emails,
        "phone": _text(row.get("联系人电话")) or _text(row.get("座机")),
        "contact_name": _text(row.get("联系人昵称")),
        "tags": _text(row.get("标签")).replace("，", ",").replace(" ", ""),
        "instagram": social.get("instagram", ""),
        "facebook": social.get("facebook", ""),
        "linkedin": social.get("linkedin", "") or _text(row.get("LinkedIn")),
        # 是 and 否 both mean he already wrote to them; 否 is "wrote, never got through"
        # (docs/118 R3). Only an empty cell is a stranger.
        "contacted": bool(_text(row.get("是否取得联系"))),
        "do_not_contact": blocked,
        "block_reason": reason,
        "note": "\n".join(lines),
    }


def _match(conn, record: dict) -> int | None:
    """The lead this row is about: by email, then website, then company name."""
    for address in record["emails"]:
        hit = conn.execute("SELECT no FROM leads WHERE lower(email)=?", (address,)).fetchone()
        if hit:
            return hit["no"]
        hit = conn.execute("SELECT lead_no FROM contacts WHERE lower(email)=?",
                           (address,)).fetchone()
        if hit:
            return hit["lead_no"]
    site = normalize_website(record["website"])
    if site:
        hit = conn.execute(
            "SELECT no FROM leads WHERE lower(replace(replace(website,'https://',''),"
            "'http://','')) LIKE ?", (f"{site}%",)).fetchone()
        if hit:
            return hit["no"]
    for name in (record["company_en"], record["company_local"]):
        if name:
            hit = conn.execute(
                "SELECT no FROM leads WHERE lower(company_en)=? OR lower(company_local)=?",
                (name.lower(), name.lower())).fetchone()
            if hit:
                return hit["no"]
    return None


_FILLABLE = ("company_local", "country", "website", "email", "phone", "contact_name",
             "instagram", "facebook", "linkedin", "tags")


def _fill_blanks(conn, no: int, record: dict) -> list[str]:
    """Only where the book has nothing. His sheet is older than the site we read (R4)."""
    current = conn.execute("SELECT * FROM leads WHERE no=?", (no,)).fetchone()
    patch = {field: record[field] for field in _FILLABLE
             if record.get(field) and not (current[field] if field in current.keys() else None)}
    if record["do_not_contact"] and not current["do_not_contact"]:
        patch["do_not_contact"] = 1
    if patch:
        repo.update_lead(conn, no, patch)
    return sorted(patch)


def _add_note(conn, no: int, text: str) -> bool:
    """Idempotent: the sheet gets re-imported, and a duplicate note is manual cleanup."""
    if not text:
        return False
    if conn.execute("SELECT 1 FROM notes WHERE lead_no=? AND text=?", (no, text)).fetchone():
        return False
    repo.add_note(conn, no, text)
    return True


def _file_contacts(conn, no: int, record: dict) -> int:
    """Every address is a person. The first is the primary; the rest are secondaries, which
    the daily send never writes to on its own (docs/114)."""
    # The lead's own address has to exist as a contact first. Otherwise the sheet's first
    # address becomes this company's *primary* contact, and the primary is synced back
    # onto the lead — quietly replacing an email R4 says we must not touch.
    contacts_mod.migrate_lead(conn, no)
    added = 0
    for index, address in enumerate(record["emails"]):
        if conn.execute("SELECT 1 FROM contacts WHERE lead_no=? AND lower(email)=?",
                        (no, address)).fetchone():
            continue
        data: dict = {"email": address}
        if index == 0:
            data["name"] = record["contact_name"] or None
            data["phone"] = record["phone"] or None
        try:
            contacts_mod.create(conn, no, data, source="manual")
            added += 1
        except (contacts_mod.ContactValidation, contacts_mod.ContactAddressTaken):
            continue
    return added


def _mark_contacted(conn, no: int, record: dict, today: dt.date) -> None:
    """Already written to means no first cold email, whichever channel it went out on."""
    for channel, address in (("email", record["email"]), ("whatsapp", record["phone"])):
        if not address:
            continue
        conn.execute(
            "INSERT INTO outreach(lead_no, channel, status, touch_count, message_sent_date)"
            " VALUES (?, ?, 'messaged', 1, ?)"
            " ON CONFLICT(lead_no, channel) DO UPDATE SET"
            "   status=CASE WHEN outreach.status IN ('prospect','') THEN 'messaged'"
            "               ELSE outreach.status END",
            (no, channel, today.isoformat()))


def plan(conn, records: list[dict]) -> dict:
    """What an import would do, without doing any of it."""
    contacts_mod.ensure_schema(conn)
    created = merged = 0
    for record in records:
        if _match(conn, record) is None:
            created += 1
        else:
            merged += 1
    return {
        "total": len(records), "created": created, "merged": merged,
        "do_not_contact": sum(1 for r in records if r["do_not_contact"]),
        "already_contacted": sum(1 for r in records if r["contacted"]),
        "manual_only": [r["company_en"] for r in records if ALLEN_MAILBOX in r["note"]],
    }


def apply(conn, records: list[dict], today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    contacts_mod.ensure_schema(conn)
    result = {"created": 0, "merged": 0, "blocked": 0, "notes": 0, "contacts": 0,
              "do_not_contact": 0, "skipped_domains": []}
    for record in records:
        no = _match(conn, record)
        if no is None:
            try:
                no = repo.insert_lead(conn, {
                    "company_en": record["company_en"],
                    "company_local": record["company_local"],
                    "country": record["country"], "website": record["website"],
                    "email": record["email"], "phone": record["phone"],
                    "instagram": record["instagram"], "facebook": record["facebook"],
                    "linkedin": record["linkedin"],
                })
            except blocklist.BlockedLead:
                # The domain is on the never-collect-again list. Someone put it there on
                # purpose; a spreadsheet is not a reason to overrule that.
                result["blocked"] += 1
                result["skipped_domains"].append(record["company_en"])
                continue
            repo.update_lead(conn, no, {
                "contact_name": record["contact_name"], "tags": record["tags"],
                "do_not_contact": 1 if record["do_not_contact"] else 0,
                "stage": "contacted" if record["contacted"] else "new",
            })
            result["created"] += 1
        else:
            _fill_blanks(conn, no, record)
            result["merged"] += 1
        if record["do_not_contact"]:
            result["do_not_contact"] += 1
        result["contacts"] += _file_contacts(conn, no, record)
        if record["contacted"]:
            _mark_contacted(conn, no, record, today)
        head = f"从{_SHEET}导入（{today.isoformat()}）"
        if record["block_reason"]:
            head += f"，只入库不联系：{record['block_reason']}"
        if _add_note(conn, no, head + ("\n" + record["note"] if record["note"] else "")):
            result["notes"] += 1
    conn.commit()
    return result


def main(path: str, apply_it: bool) -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = read_sheet(path)
    records = [r for r in (parse_row(row) for row in rows) if r]
    conn = connect(DB)
    summary = plan(conn, records)
    print(f"读到 {len(rows)} 行，可用 {summary['total']} 条：新建 {summary['created']}，"
          f"补充已有 {summary['merged']}")
    print(f"其中 标为不再联系 {summary['do_not_contact']} 条，"
          f"已开发过（不再发首封）{summary['already_contacted']} 条")
    if summary["manual_only"]:
        print("\n以下备注要求用你的私人邮箱、且不暴露公司名 —— 系统做不到，已标为不联系，请手工处理：")
        for name in summary["manual_only"]:
            print(f"  · {name}")
    if not apply_it:
        print("\n预览模式，未写入。加 --apply 执行")
        return
    done = apply(conn, records)
    print(f"\n写入完成：新建 {done['created']}，补充 {done['merged']}，"
          f"新增联系人 {done['contacts']}，写备注 {done['notes']}，"
          f"标为不再联系 {done['do_not_contact']}")
    if done["blocked"]:
        print(f"跳过 {done['blocked']} 条（域名在永不再收录名单里）："
              + "、".join(done["skipped_domains"]))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--apply"]
    if not args:
        print("用法：python -m app.import_customer_sheet <客户资料表.xlsx> [--apply]")
        raise SystemExit(2)
    main(args[0], "--apply" in sys.argv)
