"""Multiple people per customer company with one explicit primary send target."""
import datetime as dt
import re
import sqlite3


ROLES = ("decision_maker", "influencer", "technical", "finance", "other")
FIELDS = {"name", "title", "email", "phone", "linkedin", "role", "email_status", "note"}
LEAD_FIELDS = ("contact_name", "title", "email", "phone", "linkedin", "email_status")

SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_no INTEGER NOT NULL,
    name TEXT,
    title TEXT,
    email TEXT,
    phone TEXT,
    linkedin TEXT,
    role TEXT NOT NULL DEFAULT 'other',
    is_primary INTEGER NOT NULL DEFAULT 0,
    email_status TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(lead_no) REFERENCES leads(no) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_contacts_lead ON contacts(lead_no, is_primary);
CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_contacts_phone ON contacts(phone);
CREATE UNIQUE INDEX IF NOT EXISTS idx_contacts_lead_email
    ON contacts(lead_no, lower(email)) WHERE email IS NOT NULL AND email != '';
CREATE UNIQUE INDEX IF NOT EXISTS idx_contacts_one_primary
    ON contacts(lead_no) WHERE is_primary=1;
"""


class ContactValidation(ValueError):
    pass


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def _text(value) -> str | None:
    if value is None:
        return None
    return str(value).strip() or None


def _email(value) -> str | None:
    value = _text(value)
    if value and ("@" not in value or value.startswith("@") or value.endswith("@")):
        raise ContactValidation("邮箱格式不正确")
    return value.lower() if value else None


def _validate(data: dict, *, partial: bool = False) -> dict:
    clean = {k: v for k, v in data.items() if k in FIELDS}
    for field in ("name", "title", "phone", "linkedin", "note"):
        if field in clean:
            clean[field] = _text(clean[field])
    if "email" in clean:
        clean["email"] = _email(clean["email"])
    if "role" in clean:
        clean["role"] = clean["role"] or "other"
        if clean["role"] not in ROLES:
            raise ContactValidation("未知联系人角色")
    if not partial and not any(clean.get(k) for k in ("name", "email", "phone", "linkedin")):
        raise ContactValidation("姓名、邮箱、电话或 LinkedIn 至少填写一项")
    return clean


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def _check_lead(conn: sqlite3.Connection, lead_no: int) -> None:
    if conn.execute("SELECT 1 FROM leads WHERE no=?", (lead_no,)).fetchone() is None:
        raise ContactValidation("客户不存在")


def _sync_lead(conn: sqlite3.Connection, lead_no: int) -> None:
    row = conn.execute(
        "SELECT name, title, email, phone, linkedin, email_status FROM contacts"
        " WHERE lead_no=? AND is_primary=1 LIMIT 1",
        (lead_no,),
    ).fetchone()
    values = [row[k] if row else None for k in
              ("name", "title", "email", "phone", "linkedin", "email_status")]
    conn.execute(
        "UPDATE leads SET contact_name=?, title=?, email=?, phone=?, linkedin=?, email_status=?"
        " WHERE no=?",
        [*values, lead_no],
    )


def sync_lead(conn: sqlite3.Connection, lead_no: int) -> None:
    ensure_schema(conn)
    _sync_lead(conn, lead_no)
    conn.commit()


def _with_company(conn: sqlite3.Connection, contact_id: int) -> dict | None:
    row = conn.execute(
        "SELECT c.*, l.company_en, l.country FROM contacts c"
        " JOIN leads l ON l.no=c.lead_no WHERE c.id=?",
        (contact_id,),
    ).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["is_primary"] = bool(data["is_primary"])
    return data


def get(conn: sqlite3.Connection, contact_id: int) -> dict | None:
    ensure_schema(conn)
    return _with_company(conn, contact_id)


def list_all(conn: sqlite3.Connection, lead_no: int | None = None) -> list[dict]:
    ensure_schema(conn)
    sql = (
        "SELECT c.*, l.company_en, l.country FROM contacts c"
        " JOIN leads l ON l.no=c.lead_no"
    )
    params: list = []
    if lead_no is not None:
        sql += " WHERE c.lead_no=?"
        params.append(lead_no)
    sql += " ORDER BY c.is_primary DESC, c.id"
    result = []
    for row in conn.execute(sql, params):
        data = dict(row)
        data["is_primary"] = bool(data["is_primary"])
        result.append(data)
    return result


def stats(conn: sqlite3.Connection) -> dict:
    ensure_schema(conn)
    row = conn.execute(
        "SELECT COUNT(*) total_contacts, COUNT(DISTINCT lead_no) companies_with_contacts,"
        " SUM(CASE WHEN COALESCE(name, '') != '' THEN 1 ELSE 0 END) named_contacts,"
        " SUM(CASE WHEN role='decision_maker' THEN 1 ELSE 0 END) decision_makers"
        " FROM contacts"
    ).fetchone()
    total_companies = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    return {
        "total_contacts": int(row["total_contacts"] or 0),
        "companies_with_contacts": int(row["companies_with_contacts"] or 0),
        "companies_without_contacts": max(0, total_companies - int(row["companies_with_contacts"] or 0)),
        "named_contacts": int(row["named_contacts"] or 0),
        "decision_makers": int(row["decision_makers"] or 0),
    }


def create(conn: sqlite3.Connection, lead_no: int, data: dict,
           *, is_primary: bool = False, source: str = "manual") -> dict:
    ensure_schema(conn)
    _check_lead(conn, lead_no)
    clean = _validate(data)
    make_primary = is_primary or conn.execute(
        "SELECT 1 FROM contacts WHERE lead_no=?", (lead_no,)).fetchone() is None
    if make_primary:
        conn.execute("UPDATE contacts SET is_primary=0, updated_at=? WHERE lead_no=?",
                     (_now(), lead_no))
    now = _now()
    cols = ["lead_no", *clean.keys(), "is_primary", "source", "created_at", "updated_at"]
    values = [lead_no, *clean.values(), int(make_primary), source, now, now]
    try:
        cur = conn.execute(
            f"INSERT INTO contacts({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
            values,
        )
    except sqlite3.IntegrityError as exc:
        raise ContactValidation("这家公司已存在相同邮箱的联系人") from exc
    if make_primary:
        _sync_lead(conn, lead_no)
    conn.commit()
    return _with_company(conn, cur.lastrowid)


def update(conn: sqlite3.Connection, contact_id: int, data: dict) -> dict | None:
    ensure_schema(conn)
    current = _with_company(conn, contact_id)
    if current is None:
        return None
    clean = _validate(data, partial=True)
    if not clean:
        return current
    clean["updated_at"] = _now()
    try:
        conn.execute(
            f"UPDATE contacts SET {', '.join(f'{k}=?' for k in clean)} WHERE id=?",
            [*clean.values(), contact_id],
        )
    except sqlite3.IntegrityError as exc:
        raise ContactValidation("这家公司已存在相同邮箱的联系人") from exc
    if current["is_primary"]:
        _sync_lead(conn, current["lead_no"])
    conn.commit()
    return _with_company(conn, contact_id)


def set_primary(conn: sqlite3.Connection, contact_id: int) -> dict | None:
    ensure_schema(conn)
    current = _with_company(conn, contact_id)
    if current is None:
        return None
    now = _now()
    conn.execute(
        "UPDATE contacts SET is_primary=0, updated_at=? WHERE lead_no=? AND is_primary=1",
        (now, current["lead_no"]),
    )
    conn.execute(
        "UPDATE contacts SET is_primary=1, updated_at=? WHERE id=?", (now, contact_id))
    _sync_lead(conn, current["lead_no"])
    conn.commit()
    return _with_company(conn, contact_id)


def delete(conn: sqlite3.Connection, contact_id: int) -> bool:
    ensure_schema(conn)
    current = _with_company(conn, contact_id)
    if current is None:
        return False
    conn.execute("UPDATE inbox_messages SET contact_id=NULL WHERE contact_id=?", (contact_id,))
    conn.execute("DELETE FROM contacts WHERE id=?", (contact_id,))
    if current["is_primary"]:
        replacement = conn.execute(
            "SELECT id FROM contacts WHERE lead_no=? ORDER BY id LIMIT 1",
            (current["lead_no"],),
        ).fetchone()
        if replacement:
            conn.execute("UPDATE contacts SET is_primary=1, updated_at=? WHERE id=?",
                         (_now(), replacement["id"]))
        _sync_lead(conn, current["lead_no"])
    conn.commit()
    return True


def _migrate_lead(conn: sqlite3.Connection, lead_no: int) -> bool:
    if conn.execute("SELECT 1 FROM contacts WHERE lead_no=?", (lead_no,)).fetchone():
        return False
    lead = conn.execute(
        "SELECT contact_name, title, email, phone, linkedin, email_status"
        " FROM leads WHERE no=?",
        (lead_no,),
    ).fetchone()
    if lead is None or not any(lead[k] for k in ("contact_name", "email", "phone", "linkedin")):
        return False
    now = _now()
    conn.execute(
        "INSERT INTO contacts(lead_no, name, title, email, phone, linkedin, role,"
        " is_primary, email_status, source, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, 'other', 1, ?, 'legacy', ?, ?)",
        (lead_no, _text(lead["contact_name"]), _text(lead["title"]),
         _text(lead["email"]).lower() if _text(lead["email"]) else None,
         _text(lead["phone"]), _text(lead["linkedin"]), lead["email_status"], now, now),
    )
    _sync_lead(conn, lead_no)
    return True


def migrate_lead(conn: sqlite3.Connection, lead_no: int) -> bool:
    ensure_schema(conn)
    created = _migrate_lead(conn, lead_no)
    conn.commit()
    return created


def migrate_existing(conn: sqlite3.Connection) -> dict:
    ensure_schema(conn)
    created = 0
    for row in conn.execute("SELECT no FROM leads ORDER BY no").fetchall():
        created += int(_migrate_lead(conn, row["no"]))
    # Attribute historical inbox rows when the sender exactly matches one contact.
    for row in conn.execute(
        "SELECT id, lead_no, from_addr FROM inbox_messages"
        " WHERE contact_id IS NULL AND COALESCE(from_addr, '') != ''"
    ).fetchall():
        contact = find_email(conn, row["from_addr"], lead_no=row["lead_no"])
        if contact:
            conn.execute("UPDATE inbox_messages SET contact_id=? WHERE id=?",
                         (contact["id"], row["id"]))
    conn.commit()
    return {"created": created}


def upsert_primary_from_lead(conn: sqlite3.Connection, lead_no: int) -> None:
    ensure_schema(conn)
    lead = conn.execute(
        "SELECT contact_name, title, email, phone, linkedin, email_status"
        " FROM leads WHERE no=?", (lead_no,)
    ).fetchone()
    if lead is None:
        return
    primary = conn.execute(
        "SELECT id FROM contacts WHERE lead_no=? AND is_primary=1", (lead_no,)
    ).fetchone()
    data = {
        "name": lead["contact_name"], "title": lead["title"], "email": lead["email"],
        "phone": lead["phone"], "linkedin": lead["linkedin"],
        "email_status": lead["email_status"],
    }
    if primary:
        update(conn, primary["id"], data)
    elif any(data[k] for k in ("name", "email", "phone", "linkedin")):
        create(conn, lead_no, data, is_primary=True, source="legacy")


def sync_primary_email_status(conn: sqlite3.Connection, lead_no: int, status: str | None) -> None:
    ensure_schema(conn)
    conn.execute(
        "UPDATE contacts SET email_status=?, updated_at=?"
        " WHERE lead_no=? AND is_primary=1",
        (status, _now(), lead_no),
    )


def find_email(conn: sqlite3.Connection, email: str,
               lead_no: int | None = None) -> dict | None:
    ensure_schema(conn)
    value = (email or "").strip().lower()
    if not value:
        return None
    sql = "SELECT * FROM contacts WHERE lower(email)=?"
    params: list = [value]
    if lead_no is not None:
        sql += " AND lead_no=?"
        params.append(lead_no)
    rows = conn.execute(sql, params).fetchall()
    if len(rows) != 1:
        return None
    return dict(rows[0])


def email_leads(conn: sqlite3.Connection) -> dict[str, int]:
    ensure_schema(conn)
    candidates: dict[str, set[int]] = {}
    for row in conn.execute(
        "SELECT lead_no, email FROM contacts WHERE COALESCE(email, '') != ''"
    ):
        candidates.setdefault(row["email"].strip().lower(), set()).add(row["lead_no"])
    # Compatibility for a DB being used before its migration has run.
    for row in conn.execute("SELECT no, email FROM leads WHERE COALESCE(email, '') != ''"):
        candidates.setdefault(row["email"].strip().lower(), set()).add(row["no"])
    return {email: next(iter(leads)) for email, leads in candidates.items() if len(leads) == 1}


def _phone(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def phone_leads(conn: sqlite3.Connection, min_digits: int = 8) -> dict[str, int]:
    ensure_schema(conn)
    candidates: dict[str, set[int]] = {}
    for row in conn.execute(
        "SELECT lead_no, phone FROM contacts WHERE COALESCE(phone, '') != ''"
    ):
        digits = _phone(row["phone"])
        if len(digits) >= min_digits:
            candidates.setdefault(digits, set()).add(row["lead_no"])
    for row in conn.execute("SELECT no, phone FROM leads WHERE COALESCE(phone, '') != ''"):
        digits = _phone(row["phone"])
        if len(digits) >= min_digits:
            candidates.setdefault(digits, set()).add(row["no"])
    return {phone: next(iter(leads)) for phone, leads in candidates.items() if len(leads) == 1}


def find_phone(conn: sqlite3.Connection, value: str, lead_no: int) -> dict | None:
    ensure_schema(conn)
    digits = _phone(value)
    if len(digits) < 8:
        return None
    matches = []
    for row in conn.execute(
        "SELECT * FROM contacts WHERE lead_no=? AND COALESCE(phone, '') != ''", (lead_no,)
    ):
        stored = _phone(row["phone"])
        if stored == digits or stored.endswith(digits[-8:]) or digits.endswith(stored[-8:]):
            matches.append(row)
    return dict(matches[0]) if len(matches) == 1 else None


def merge_lead_contacts(conn: sqlite3.Connection, keep: int, duplicate: int) -> None:
    ensure_schema(conn)
    # Dedupe is also used by scripts/tests before the startup migration. Adopt both
    # legacy rows first so syncing the keeper cannot erase contact fields that were
    # just filled from the duplicate lead.
    migrate_lead(conn, keep)
    migrate_lead(conn, duplicate)
    keep_primary = conn.execute(
        "SELECT * FROM contacts WHERE lead_no=? AND is_primary=1", (keep,)
    ).fetchone()
    rows = conn.execute("SELECT * FROM contacts WHERE lead_no=? ORDER BY id", (duplicate,)).fetchall()
    for row in rows:
        existing = None
        if row["email"]:
            existing = conn.execute(
                "SELECT * FROM contacts WHERE lead_no=? AND lower(email)=lower(?)",
                (keep, row["email"]),
            ).fetchone()
        if existing:
            updates = {}
            for field in ("name", "title", "phone", "linkedin", "role", "email_status", "note"):
                if not existing[field] and row[field]:
                    updates[field] = row[field]
            if updates:
                updates["updated_at"] = _now()
                conn.execute(
                    f"UPDATE contacts SET {', '.join(f'{k}=?' for k in updates)} WHERE id=?",
                    [*updates.values(), existing["id"]],
                )
            conn.execute("UPDATE inbox_messages SET contact_id=? WHERE contact_id=?",
                         (existing["id"], row["id"]))
            # Formal documents keep the exact addressee when duplicate companies merge.
            if conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='quotes'"
            ).fetchone():
                conn.execute("UPDATE quotes SET contact_id=? WHERE contact_id=?",
                             (existing["id"], row["id"]))
                conn.execute("UPDATE orders SET contact_id=? WHERE contact_id=?",
                             (existing["id"], row["id"]))
            conn.execute("DELETE FROM contacts WHERE id=?", (row["id"],))
            continue
        if row["is_primary"] and keep_primary:
            keeper_reachable = bool(keep_primary["email"] or keep_primary["phone"])
            duplicate_reachable = bool(row["email"] or row["phone"])
            if not keeper_reachable and duplicate_reachable:
                conn.execute("UPDATE contacts SET is_primary=0 WHERE id=?", (keep_primary["id"],))
                keep_primary = row
            else:
                conn.execute("UPDATE contacts SET is_primary=0 WHERE id=?", (row["id"],))
        conn.execute("UPDATE contacts SET lead_no=?, updated_at=? WHERE id=?",
                     (keep, _now(), row["id"]))
        if row["is_primary"] and not keep_primary:
            keep_primary = row
    if keep_primary is None:
        first = conn.execute("SELECT id FROM contacts WHERE lead_no=? ORDER BY id LIMIT 1", (keep,)).fetchone()
        if first:
            conn.execute("UPDATE contacts SET is_primary=1 WHERE id=?", (first["id"],))
    _sync_lead(conn, keep)
    conn.commit()
