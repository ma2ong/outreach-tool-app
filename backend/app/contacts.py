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

-- docs/114：同一个人的其它信箱和号码。主地址仍在 contacts 上，这里只放附加的。
CREATE TABLE IF NOT EXISTS contact_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    value TEXT NOT NULL,
    status TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(contact_id) REFERENCES contacts(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_contact_channels_contact
    ON contact_channels(contact_id, kind);
CREATE INDEX IF NOT EXISTS idx_contact_channels_value
    ON contact_channels(value COLLATE NOCASE);
"""


class ContactValidation(ValueError):
    pass


class ContactConflict(ContactValidation):
    """这个地址已经属于同一家公司的另一个联系人（docs/114 R3）。"""

    def __init__(self, message: str, contact_id: int, contact_name: str | None):
        super().__init__(message)
        self.contact_id = contact_id
        self.contact_name = contact_name


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
    data["channels"] = _channels(conn, contact_id)
    return data


def _channels(conn: sqlite3.Connection, contact_id: int) -> list[dict]:
    return [dict(row) for row in conn.execute(
        "SELECT id, contact_id, kind, value, status FROM contact_channels"
        " WHERE contact_id=? ORDER BY id", (contact_id,))]


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
        data["channels"] = _channels(conn, data["id"])
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


# docs/114：一个人的第二个信箱、第二个号码。主地址仍是 contacts.email / contacts.phone
# ——发信、报价单抬头、`leads` 同步全部走它；这里放的是「还能从哪认出他、还该抄送谁」。
KINDS = ("email", "phone")


def _channel_value(kind: str, value) -> str:
    if kind not in KINDS:
        raise ContactValidation("联系方式只能是邮箱或电话")
    if kind == "email":
        clean = _email(value)
    else:
        clean = _text(value)
        if clean and len(_phone(clean)) < 8:
            raise ContactValidation("电话号码位数不足")
    if not clean:
        raise ContactValidation("请填写要添加的联系方式")
    return clean


def _same(kind: str, a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    if kind == "email":
        return a.strip().lower() == b.strip().lower()
    return _phone(a) == _phone(b)


def _claim(conn: sqlite3.Connection, contact: dict, kind: str, value: str,
           *, ignore: int | None = None) -> None:
    """这家公司里还没人用这个地址——用了的话说出是谁（docs/114 R3）。

    合并时传 `ignore`：被并掉的那个人还在库里，他自己的地址不算「已被占用」。
    """
    own = contact["email"] if kind == "email" else contact["phone"]
    if _same(kind, own, value):
        raise ContactValidation("这已经是该联系人的默认联系方式")
    for row in conn.execute(
        "SELECT c.id, c.name, c.email, c.phone FROM contacts c WHERE c.lead_no=?",
        (contact["lead_no"],),
    ).fetchall():
        held = row["email"] if kind == "email" else row["phone"]
        if not _same(kind, held, value) or row["id"] == ignore:
            continue
        if row["id"] == contact["id"]:
            raise ContactValidation("这已经是该联系人的默认联系方式")
        raise ContactConflict("这家公司已存在使用该联系方式的联系人", row["id"], row["name"])
    for row in conn.execute(
        "SELECT ch.value, ch.contact_id, c.name FROM contact_channels ch"
        " JOIN contacts c ON c.id=ch.contact_id"
        " WHERE c.lead_no=? AND ch.kind=?", (contact["lead_no"], kind),
    ).fetchall():
        if not _same(kind, row["value"], value) or row["contact_id"] == ignore:
            continue
        if row["contact_id"] == contact["id"]:
            raise ContactValidation("该联系方式已经在这个联系人下面了")
        raise ContactConflict("这家公司已存在使用该联系方式的联系人", row["contact_id"], row["name"])


def add_channel(conn: sqlite3.Connection, contact_id: int, kind: str, value) -> dict:
    ensure_schema(conn)
    contact = _with_company(conn, contact_id)
    if contact is None:
        raise ContactValidation("联系人不存在")
    clean = _channel_value(kind, value)
    _claim(conn, contact, kind, clean)
    now = _now()
    cur = conn.execute(
        "INSERT INTO contact_channels(contact_id, kind, value, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?)", (contact_id, kind, clean, now, now))
    conn.commit()
    return {"id": cur.lastrowid, "contact_id": contact_id, "kind": kind,
            "value": clean, "status": None}


def delete_channel(conn: sqlite3.Connection, channel_id: int) -> bool:
    ensure_schema(conn)
    cur = conn.execute("DELETE FROM contact_channels WHERE id=?", (channel_id,))
    conn.commit()
    return cur.rowcount > 0


def promote_channel(conn: sqlite3.Connection, channel_id: int) -> dict | None:
    """和默认联系方式对调。改的是发信地址，所以这是一个显式动作，不是加地址的副作用。"""
    ensure_schema(conn)
    row = conn.execute(
        "SELECT * FROM contact_channels WHERE id=?", (channel_id,)).fetchone()
    if row is None:
        return None
    contact = _with_company(conn, row["contact_id"])
    if contact is None:
        return None
    field = "email" if row["kind"] == "email" else "phone"
    demoted = contact[field]
    now = _now()
    conn.execute(f"UPDATE contacts SET {field}=?, updated_at=? WHERE id=?",
                 (row["value"], now, contact["id"]))
    if row["kind"] == "email":
        # 状态跟着地址走：降下去的那个带着自己的退信状态，升上来的接管联系人这一栏。
        conn.execute("UPDATE contacts SET email_status=? WHERE id=?",
                     (row["status"], contact["id"]))
    if demoted:
        conn.execute(
            "UPDATE contact_channels SET value=?, status=?, updated_at=? WHERE id=?",
            (demoted, contact["email_status"] if row["kind"] == "email" else None,
             now, channel_id))
    else:
        conn.execute("DELETE FROM contact_channels WHERE id=?", (channel_id,))
    if contact["is_primary"]:
        _sync_lead(conn, contact["lead_no"])
    conn.commit()
    return _with_company(conn, contact["id"])


def fold_into(conn: sqlite3.Connection, keep_id: int, duplicate_id: int) -> dict | None:
    """把 duplicate 这个人整个并进 keep：地址变成附加地址，历史改挂过去（docs/114 R4）。"""
    ensure_schema(conn)
    keep = _with_company(conn, keep_id)
    duplicate = conn.execute("SELECT * FROM contacts WHERE id=?", (duplicate_id,)).fetchone()
    if keep is None or duplicate is None:
        return None
    if keep_id == duplicate_id:
        raise ContactValidation("不能把联系人并进它自己")
    if keep["lead_no"] != duplicate["lead_no"]:
        raise ContactValidation("只能合并同一家公司下的联系人")
    if duplicate["is_primary"]:
        raise ContactValidation("主要联系人不能被合并掉，请先把主要联系人设成另一位")
    now = _now()
    # 空缺才填，不覆盖已经确认过的信息。
    fill = {f: duplicate[f] for f in ("name", "title", "linkedin", "note")
            if not keep[f] and duplicate[f]}
    if fill:
        fill["updated_at"] = now
        conn.execute(f"UPDATE contacts SET {', '.join(f'{k}=?' for k in fill)} WHERE id=?",
                     [*fill.values(), keep_id])
        keep = _with_company(conn, keep_id)
    for kind, value, status in (("email", duplicate["email"], duplicate["email_status"]),
                                ("phone", duplicate["phone"], None)):
        if not value:
            continue
        try:
            _claim(conn, keep, kind, value, ignore=duplicate_id)
        except ContactValidation:
            continue  # 同一个地址两边都有：留 keep 的那一份就够了。
        conn.execute(
            "INSERT INTO contact_channels(contact_id, kind, value, status, created_at,"
            " updated_at) VALUES (?, ?, ?, ?, ?, ?)", (keep_id, kind, value, status, now, now))
    for row in conn.execute(
        "SELECT kind, value, status FROM contact_channels WHERE contact_id=? ORDER BY id",
        (duplicate_id,),
    ).fetchall():
        try:
            _claim(conn, keep, row["kind"], row["value"], ignore=duplicate_id)
        except ContactValidation:
            continue
        conn.execute(
            "INSERT INTO contact_channels(contact_id, kind, value, status, created_at,"
            " updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (keep_id, row["kind"], row["value"], row["status"], now, now))
    _fold_into(conn, keep_id, duplicate)
    conn.commit()
    return _with_company(conn, keep_id)


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
    # docs/114：默认信箱和附加信箱一起找，同一个人只算一次。
    sql = (
        "SELECT c.* FROM contacts c WHERE lower(c.email)=?"
        " UNION SELECT c.* FROM contacts c JOIN contact_channels ch ON ch.contact_id=c.id"
        " WHERE ch.kind='email' AND lower(ch.value)=?"
    )
    params: list = [value, value]
    if lead_no is not None:
        sql = (
            "SELECT c.* FROM contacts c WHERE lower(c.email)=? AND c.lead_no=?"
            " UNION SELECT c.* FROM contacts c JOIN contact_channels ch ON ch.contact_id=c.id"
            " WHERE ch.kind='email' AND lower(ch.value)=? AND c.lead_no=?"
        )
        params = [value, lead_no, value, lead_no]
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
    for row in conn.execute(
        "SELECT c.lead_no, ch.value FROM contact_channels ch"
        " JOIN contacts c ON c.id=ch.contact_id WHERE ch.kind='email'"
    ):
        candidates.setdefault(row["value"].strip().lower(), set()).add(row["lead_no"])
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
    for row in conn.execute(
        "SELECT c.lead_no, ch.value FROM contact_channels ch"
        " JOIN contacts c ON c.id=ch.contact_id WHERE ch.kind='phone'"
    ):
        digits = _phone(row["value"])
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
    matches: dict[int, sqlite3.Row] = {}
    for row in conn.execute(
        "SELECT c.*, c.phone AS number FROM contacts c"
        " WHERE c.lead_no=? AND COALESCE(c.phone, '') != ''"
        " UNION ALL"
        " SELECT c.*, ch.value AS number FROM contacts c"
        " JOIN contact_channels ch ON ch.contact_id=c.id"
        " WHERE c.lead_no=? AND ch.kind='phone'", (lead_no, lead_no)
    ):
        stored = _phone(row["number"])
        if not stored:
            continue
        if stored == digits or stored.endswith(digits[-8:]) or digits.endswith(stored[-8:]):
            matches[row["id"]] = row
    if len(matches) != 1:
        return None
    return dict(next(iter(matches.values())))


def _fold_into(conn: sqlite3.Connection, target_id: int, row: sqlite3.Row) -> None:
    """Point everything that referenced `row` at `target_id`, then drop `row`."""
    conn.execute("UPDATE inbox_messages SET contact_id=? WHERE contact_id=?",
                 (target_id, row["id"]))
    # docs/114：提案上的收件人也要跟着走，否则删掉的联系人会在提案里留一个悬空 id。
    if conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='agent_proposals'"
    ).fetchone():
        conn.execute("UPDATE agent_proposals SET contact_id=? WHERE contact_id=?",
                     (target_id, row["id"]))
    # Formal documents keep the exact addressee when duplicate companies merge.
    if conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='quotes'"
    ).fetchone():
        conn.execute("UPDATE quotes SET contact_id=? WHERE contact_id=?",
                     (target_id, row["id"]))
        conn.execute("UPDATE orders SET contact_id=? WHERE contact_id=?",
                     (target_id, row["id"]))
    conn.execute("DELETE FROM contacts WHERE id=?", (row["id"],))


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
            _fold_into(conn, existing["id"], row)
            continue
        if row["is_primary"] and keep_primary:
            keeper_reachable = bool(keep_primary["email"] or keep_primary["phone"])
            duplicate_reachable = bool(row["email"] or row["phone"])
            if not keeper_reachable and duplicate_reachable:
                conn.execute("UPDATE contacts SET is_primary=0 WHERE id=?", (keep_primary["id"],))
                keep_primary = row
            else:
                # Both are reachable, but often on different channels: one row carries
                # the number, the other the address. Demoting one used to end with
                # `_sync_lead` writing the demoted channel back onto the lead as NULL —
                # merging two records of the same Korean company left it with no email
                # at all, which quietly removes it from every email path. Only blanks
                # are filled, so nothing the keeper already knew is overwritten.
                fill = {f: row[f] for f in
                        ("name", "title", "email", "phone", "linkedin", "email_status", "note")
                        if not keep_primary[f] and row[f]}
                if fill:
                    fill["updated_at"] = _now()
                    conn.execute(
                        f"UPDATE contacts SET {', '.join(f'{k}=?' for k in fill)} WHERE id=?",
                        [*fill.values(), keep_primary["id"]])
                    keep_primary = conn.execute(
                        "SELECT * FROM contacts WHERE id=?", (keep_primary["id"],)).fetchone()
                # Taking its address makes it the same address, which is the case the
                # branch above already handles: fold the row away rather than move a
                # now-colliding copy across.
                if row["email"] and (keep_primary["email"] or "").lower() == row["email"].lower():
                    _fold_into(conn, keep_primary["id"], row)
                    continue
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


# docs/95：同一家公司别的信箱，抄送在同一封信里。
#
# Allen 09-03 的两条：找到的具名邮箱**不替换** `leads.email`（不知道哪个信箱后面真的
# 坐着人，两个都发），但也不另发一封 —— 同一家公司收到两封几乎一样的冷邮件，比只收到
# 一封更像群发。所以是一封信、两个收件人，占一个额度、留一条发信记录，日限额、退信
# 抑制、免打扰全部原样生效。
#
# 地址只能来自这家公司自己的页面（docs/89）。这里不猜任何地址：库里已有的联系人是
# `decision_maker_radar` 从官网上读到的，猜出来的地址从来进不了这张表。
MAX_CC = 2


def also_reach(conn: sqlite3.Connection, lead_no: int, primary: str | None) -> list[str]:
    """这家公司另外还该抄送的地址，按录入顺序，最多两个。"""
    # 这张表在老库和测试库里可能还没建起来。少一张表不该被发信循环那个宽 except
    # 吞成「这封信发失败了」—— 那正是 23 个测试一起变红的原因。
    ensure_schema(conn)
    main = (primary or "").strip().lower()
    out: list[str] = []
    # docs/114：同一个人的第二个信箱和别人的信箱一样该抄送 —— 把两行并成一个人之前
    # 它就在这份名单里，并完之后不该消失。
    rows = conn.execute(
        "SELECT email AS addr, is_primary, id FROM contacts"
        " WHERE lead_no=? AND COALESCE(email,'')<>''"
        " AND COALESCE(email_status,'') != 'invalid'"
        " UNION ALL"
        " SELECT ch.value AS addr, c.is_primary, c.id FROM contact_channels ch"
        " JOIN contacts c ON c.id=ch.contact_id"
        " WHERE c.lead_no=? AND ch.kind='email'"
        " AND COALESCE(ch.status,'') != 'invalid'"
        " ORDER BY is_primary DESC, id",
        (lead_no, lead_no)).fetchall()
    for row in rows:
        addr = (row["addr"] or "").strip()
        low = addr.lower()
        if not low or low == main or low in {o.lower() for o in out}:
            continue
        out.append(addr)
        if len(out) >= MAX_CC:
            break
    return out
