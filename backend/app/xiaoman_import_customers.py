"""Merge the 489 Xiaoman customer records into the lead book (see `docs/55`).

Almost all of these are already in the book: the mail-log import brought them in from
email headers alone, so their company name is the email address itself. What Xiaoman has
and the mail log never did is what Allen typed himself — the real company name, the tag
he filed them under (工程商 / 租赁客户), the contact's job title, and the notes he wrote
into the names: (成交客户), （有回复), (已加微信).

So this is a field-filling job, not an acquisition job, and the matching and merge rules
come from `app.import_customers` rather than being written a second time.

Run:  python -m app.xiaoman_import_customers            # preview only
      python -m app.xiaoman_import_customers --apply    # write
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from app import repository as repo
from app.db import connect
from app.import_customers import _match, _usable
from app.xiaoman_import import _FREE_MAIL

SOURCE = Path("xiaoman_raw") / "customers.json"

# Allen's own handwriting, kept verbatim: the spec forbids widening these into synonyms.
_WON_NOTE = "成交"
_NOTE_PATTERN = re.compile(r"[（(]([^）)]{1,12})[）)]")


def _label(field) -> str:
    """Xiaoman wraps display values as {info_value, info_label}; take what it shows."""
    if isinstance(field, dict):
        return str(field.get("info_label") or field.get("info_value") or "").strip()
    return str(field or "").strip()


def _company_name(row: dict) -> str:
    """The company name with Allen's parenthetical notes stripped back out."""
    return _NOTE_PATTERN.sub("", row.get("name") or "").strip(" -_·")


def _notes(row: dict) -> list[str]:
    return [m.strip() for m in _NOTE_PATTERN.findall(row.get("name") or "") if m.strip()]


def _tags(row: dict) -> list[str]:
    return [t for t in (_label(t) for t in (row.get("cus_tag_info") or [])) if t]


# Xiaoman placeholders that look like data but are not (R7).
_PLACEHOLDER_TITLES = {"department", "staff", "--", "-", "other", "n/a"}
# A shared mailbox is not a person, whatever the mailbox is called.
_MAILBOX_NAMES = {"info", "sales", "admin", "contact", "office", "marketing", "support",
                  "export", "service", "mail", "webmaster", "hello", "inquiry"}
_MIN_PHONE_DIGITS = 8


def _phone(row: dict) -> str:
    """A dialable number, or nothing.

    Xiaoman's Korean rows carry truncated values (`+82 109445`) scraped by OKKI Leads.
    A broken number is worse than a blank one: it makes a lead look reachable.
    """
    candidates = []
    for entry in ((row.get("customer") or {}).get("tel_list_info") or []):
        value = entry.get("info_value") or {}
        if isinstance(value, dict) and value.get("tel"):
            candidates.append(str(value["tel"]))
    candidates.append(_label(row.get("tel_full_new_info")))
    for number in candidates:
        digits = re.sub(r"\D", "", number)
        if len(digits) >= _MIN_PHONE_DIGITS:
            return number
    return ""


def _title(contact: dict) -> str:
    post = (contact.get("post") or "").strip()
    return "" if post.lower() in _PLACEHOLDER_TITLES else post


def _contact_name(contact: dict) -> str:
    """A person's name — not the email's local part dressed up as one."""
    name = (contact.get("name") or "").strip()
    local = (contact.get("email") or "").split("@")[0].strip().lower()
    if name.lower() in (local, *_MAILBOX_NAMES):
        return ""
    return name


def load(path: Path = SOURCE) -> list[dict]:
    """Xiaoman rows reshaped into the lead-shaped dicts `import_customers` expects."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for entry in raw:
        if entry.get("ali_store_id"):
            continue  # R1: Alibaba buyer-identity records stay out
        contact = entry.get("customer") or {}
        notes = _notes(entry)
        tags = _tags(entry)
        detail = [f"小满标签：{'、'.join(tags)}"] if tags else []
        detail += [f"小满备注：{n}" for n in notes]
        if entry.get("origin_name"):
            detail.append(f"小满来源：{entry['origin_name']}")
        rows.append({
            "company_en": _company_name(entry),
            "contact_name": _contact_name(contact),
            "title": _title(contact),
            "email": (contact.get("email") or "").strip(),
            "phone": _phone(entry),
            "country": entry.get("country") or "",
            "city": entry.get("city") or "",
            "tags": "、".join(tags),
            "business": " · ".join(detail),
            "status": "成交" if any(_WON_NOTE in n for n in notes) else "",
            "_notes": notes,
        })
    return rows


def _match_lead(conn, row: dict) -> int | None:
    """The lead this row is about — by email, website, name, then company domain (R5).

    The domain step is what stops `orlando@acme.com` from becoming a second Acme when
    `sales@acme.com` is already in the book. It is only safe for company domains: two
    people on gmail are not colleagues.
    """
    hit = _match(conn, row)
    if hit is not None:
        return hit
    email = (row.get("email") or "").strip().lower()
    domain = email.split("@")[-1] if "@" in email else ""
    if not domain or domain in _FREE_MAIL:
        return None
    found = conn.execute(
        "SELECT no FROM leads WHERE lower(email) LIKE ? ORDER BY no LIMIT 1",
        (f"%@{domain}",)).fetchone()
    return found["no"] if found else None


def _is_cjk(text: str) -> bool:
    return any(ord(ch) > 0x2E80 for ch in text)


def _placeholder_name(current: str, email: str) -> bool:
    """True when the stored company name is the record's own email address (R2).

    That value was never observed; a previous import put it there because it had nothing
    else. Replacing it is not overwriting data, it is removing a placeholder.
    """
    return bool(current and email) and current.strip().lower() == email.strip().lower()


# Filled only when currently empty — 54-R2. `company_en` is handled separately by R2.
_FILLABLE = ("email", "phone", "country", "city", "contact_name", "title", "tags",
             "business")


def run(conn, rows: list[dict], apply_changes: bool) -> dict:
    stats = {"total": len(rows), "created": 0, "merged": 0, "skipped": 0,
             "renamed": 0, "tagged": 0, "won": 0, "local_name": 0,
             "same_company": 0}
    for row in rows:
        if not _usable(row):
            stats["skipped"] += 1
            continue
        existing = _match_lead(conn, row)
        if existing is None:
            stats["created"] += 1
            if apply_changes:
                no = repo.insert_lead(conn, {
                    "company_en": row["company_en"] or row["email"],
                    "country": row["country"], "city": row["city"],
                    "email": row["email"], "phone": row["phone"],
                    "business": row["business"],
                })
                repo.update_lead(conn, no, {
                    "stage": "won" if row["status"] else "contacted",
                    "contact_name": row["contact_name"], "title": row["title"],
                    "tags": row["tags"],
                })
            continue

        stats["merged"] += 1
        if _match(conn, row) is None:
            stats["same_company"] += 1
        current = conn.execute("SELECT * FROM leads WHERE no=?", (existing,)).fetchone()
        patch = {f: row[f] for f in _FILLABLE
                 if row.get(f) and not (current[f] if f in current.keys() else None)}
        if row["company_en"] and _placeholder_name(current["company_en"], current["email"]):
            patch["company_en"] = row["company_en"]
            stats["renamed"] += 1
        name = row["company_en"]
        # R8: if the real name just replaced the placeholder in company_en, it is already
        # recorded; writing it to company_local as well stores the same string twice.
        if (name and _is_cjk(name) and patch.get("company_en") != name
                and not _is_cjk(current["company_en"] or "")
                and not current["company_local"]):
            patch["company_local"] = name
            stats["local_name"] += 1
        if row["tags"] and not current["tags"]:
            stats["tagged"] += 1
        for note in row["_notes"]:
            existing_note = patch.get("business", current["business"] or "")
            if note not in existing_note:
                patch["business"] = f"{existing_note} · 小满备注：{note}".strip(" ·")
        if row["status"] and current["stage"] != "won":
            patch["stage"] = "won"
            stats["won"] += 1
        if patch and apply_changes:
            repo.update_lead(conn, existing, patch)
    return stats


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    apply_changes = "--apply" in sys.argv
    rows = load()
    with connect("outreach.db") as conn:
        stats = run(conn, rows, apply_changes)
        if apply_changes:
            conn.commit()
    head = "已写入" if apply_changes else "预览（没有写库）"
    print(f"=== {head} ===")
    print(f"小满 489 家，排除阿里买家身份后剩 {stats['total']} 家")
    print(f"  已在库、补字段：{stats['merged']} 家")
    print(f"    其中公司名从邮箱换成真名：{stats['renamed']} 家")
    print(f"    其中补上客户标签：{stats['tagged']} 家")
    print(f"    其中补上本地语言公司名：{stats['local_name']} 家")
    print(f"    其中靠公司域名认出、不再重复建档：{stats['same_company']} 家")
    print(f"    其中标记为成交：{stats['won']} 家")
    print(f"  新建：{stats['created']} 家")
    print(f"  没有可用信息、跳过：{stats['skipped']} 家")
    if not apply_changes:
        print("\n确认没问题就加 --apply 写入")


if __name__ == "__main__":
    main()
