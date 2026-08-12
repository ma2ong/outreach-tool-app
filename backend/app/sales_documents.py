"""Formal quotations and order fulfilment for LED display projects."""
from __future__ import annotations

import datetime as dt
import html
import sqlite3
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


QUOTE_STATUSES = ("draft", "sent", "accepted", "rejected", "expired")
ORDER_STATUSES = (
    "confirmed", "deposit", "production", "inspection", "shipped", "completed", "cancelled",
)
PRICING_UNITS = ("sqm", "unit")

SCHEMA = """
CREATE TABLE IF NOT EXISTS quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quote_no TEXT NOT NULL UNIQUE,
    lead_no INTEGER NOT NULL,
    opportunity_id INTEGER,
    contact_id INTEGER,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    currency TEXT NOT NULL DEFAULT 'USD',
    incoterm TEXT,
    destination TEXT,
    valid_until TEXT,
    payment_terms TEXT,
    lead_time TEXT,
    warranty TEXT,
    subtotal REAL NOT NULL DEFAULT 0,
    shipping REAL NOT NULL DEFAULT 0,
    discount REAL NOT NULL DEFAULT 0,
    total REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    sent_at TEXT,
    accepted_at TEXT,
    FOREIGN KEY(lead_no) REFERENCES leads(no) ON DELETE CASCADE,
    FOREIGN KEY(opportunity_id) REFERENCES opportunities(id) ON DELETE SET NULL,
    FOREIGN KEY(contact_id) REFERENCES contacts(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS quote_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quote_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    model TEXT,
    pixel_pitch TEXT,
    width_m REAL,
    height_m REAL,
    quantity INTEGER NOT NULL,
    pricing_unit TEXT NOT NULL,
    unit_price REAL NOT NULL,
    area_sqm REAL NOT NULL DEFAULT 0,
    line_total REAL NOT NULL,
    note TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(quote_id) REFERENCES quotes(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no TEXT NOT NULL UNIQUE,
    quote_id INTEGER NOT NULL UNIQUE,
    lead_no INTEGER NOT NULL,
    opportunity_id INTEGER,
    contact_id INTEGER,
    status TEXT NOT NULL DEFAULT 'confirmed',
    currency TEXT NOT NULL DEFAULT 'USD',
    total REAL NOT NULL,
    deposit_amount REAL NOT NULL DEFAULT 0,
    paid_amount REAL NOT NULL DEFAULT 0,
    balance REAL NOT NULL,
    expected_ship_date TEXT,
    shipped_at TEXT,
    tracking_no TEXT,
    note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(quote_id) REFERENCES quotes(id) ON DELETE RESTRICT,
    FOREIGN KEY(lead_no) REFERENCES leads(no) ON DELETE CASCADE,
    FOREIGN KEY(opportunity_id) REFERENCES opportunities(id) ON DELETE SET NULL,
    FOREIGN KEY(contact_id) REFERENCES contacts(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_quotes_lead ON quotes(lead_no, created_at);
CREATE INDEX IF NOT EXISTS idx_quotes_opportunity ON quotes(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_quotes_status ON quotes(status);
CREATE INDEX IF NOT EXISTS idx_quote_items_quote ON quote_items(quote_id, sort_order);
CREATE INDEX IF NOT EXISTS idx_orders_lead ON orders(lead_no, created_at);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
"""

QUOTE_FIELDS = {
    "title", "opportunity_id", "contact_id", "currency", "incoterm", "destination",
    "valid_until", "payment_terms", "lead_time", "warranty", "shipping", "discount",
}
ORDER_FIELDS = {
    "status", "deposit_amount", "paid_amount", "expected_ship_date", "shipped_at",
    "tracking_no", "note",
}
CENT = Decimal("0.01")


class SalesDocumentValidation(ValueError):
    pass


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def _text(value) -> str | None:
    if value is None:
        return None
    return str(value).strip() or None


def _date(value, field: str) -> str | None:
    value = _text(value)
    if value is None:
        return None
    try:
        return dt.date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise SalesDocumentValidation(f"{field} 必须是 YYYY-MM-DD") from exc


def _decimal(value, field: str, *, positive: bool = False) -> Decimal:
    try:
        number = Decimal(str(value if value not in (None, "") else 0))
    except (InvalidOperation, ValueError) as exc:
        raise SalesDocumentValidation(f"{field} 必须是数字") from exc
    if not number.is_finite():
        raise SalesDocumentValidation(f"{field} 必须是有限数字")
    if number < 0 or (positive and number <= 0):
        suffix = "大于 0" if positive else "不能为负数"
        raise SalesDocumentValidation(f"{field} {suffix}")
    return number.quantize(CENT, rounding=ROUND_HALF_UP)


def _money(value: Decimal) -> float:
    return float(value.quantize(CENT, rounding=ROUND_HALF_UP))


def ensure_schema(conn: sqlite3.Connection) -> None:
    # Referenced tables are optional modules in old databases, so create them first.
    from app.contacts import ensure_schema as ensure_contact_schema
    from app.opportunities import ensure_schema as ensure_opportunity_schema

    ensure_contact_schema(conn)
    ensure_opportunity_schema(conn)
    conn.executescript(SCHEMA)
    conn.commit()


def _number(conn: sqlite3.Connection, prefix: str, table: str, column: str) -> str:
    month = dt.date.today().strftime("%Y%m")
    stem = f"{prefix}-{month}-"
    row = conn.execute(
        f"SELECT {column} FROM {table} WHERE {column} LIKE ? ORDER BY {column} DESC LIMIT 1",
        (stem + "%",),
    ).fetchone()
    sequence = int(row[column].rsplit("-", 1)[-1]) + 1 if row else 1
    return f"{stem}{sequence:04d}"


def _validate_refs(conn: sqlite3.Connection, lead_no: int, opportunity_id, contact_id) -> tuple[int | None, int | None]:
    if conn.execute("SELECT 1 FROM leads WHERE no=?", (lead_no,)).fetchone() is None:
        raise SalesDocumentValidation("客户不存在")
    opportunity_id = int(opportunity_id) if opportunity_id not in (None, "") else None
    contact_id = int(contact_id) if contact_id not in (None, "") else None
    if opportunity_id is not None:
        row = conn.execute("SELECT lead_no, stage FROM opportunities WHERE id=?", (opportunity_id,)).fetchone()
        if row is None or row["lead_no"] != lead_no:
            raise SalesDocumentValidation("商机不属于所选客户")
        if row["stage"] in ("won", "lost"):
            raise SalesDocumentValidation("已关闭的商机不能新建报价")
    if contact_id is not None:
        row = conn.execute("SELECT lead_no FROM contacts WHERE id=?", (contact_id,)).fetchone()
        if row is None or row["lead_no"] != lead_no:
            raise SalesDocumentValidation("联系人不属于所选客户")
    else:
        row = conn.execute(
            "SELECT id FROM contacts WHERE lead_no=? AND is_primary=1 LIMIT 1", (lead_no,)
        ).fetchone()
        contact_id = row["id"] if row else None
    return opportunity_id, contact_id


def _clean_quote(data: dict, *, partial: bool = False) -> dict:
    clean = {key: value for key, value in data.items() if key in QUOTE_FIELDS}
    for field in ("title", "currency", "incoterm", "destination", "payment_terms", "lead_time", "warranty"):
        if field in clean:
            clean[field] = _text(clean[field])
    if not partial and not clean.get("title"):
        raise SalesDocumentValidation("项目名称不能为空")
    if "title" in clean and not clean["title"]:
        raise SalesDocumentValidation("项目名称不能为空")
    if "currency" in clean:
        clean["currency"] = (clean["currency"] or "USD").upper()
        if len(clean["currency"]) != 3:
            raise SalesDocumentValidation("币种必须使用 3 位代码，例如 USD")
    if "valid_until" in clean:
        clean["valid_until"] = _date(clean["valid_until"], "有效期")
    for field, label in (("shipping", "运费"), ("discount", "折扣")):
        if field in clean:
            clean[field] = _money(_decimal(clean[field], label))
    return clean


def _clean_item(item: dict, sort_order: int) -> dict:
    description = _text(item.get("description"))
    model = _text(item.get("model"))
    if not description and not model:
        raise SalesDocumentValidation(f"第 {sort_order + 1} 条明细需要描述或型号")
    quantity_raw = item.get("quantity", 1)
    try:
        quantity = int(quantity_raw)
    except (TypeError, ValueError) as exc:
        raise SalesDocumentValidation("数量必须是整数") from exc
    if quantity < 1 or str(quantity_raw).strip() not in (str(quantity), f"{quantity}.0"):
        raise SalesDocumentValidation("数量必须是大于 0 的整数")
    pricing_unit = _text(item.get("pricing_unit")) or "sqm"
    if pricing_unit not in PRICING_UNITS:
        raise SalesDocumentValidation("计价单位只能是 sqm 或 unit")
    unit_price = _decimal(item.get("unit_price"), "单价", positive=True)
    width = _decimal(item.get("width_m"), "宽度", positive=True) if item.get("width_m") not in (None, "") else None
    height = _decimal(item.get("height_m"), "高度", positive=True) if item.get("height_m") not in (None, "") else None
    if pricing_unit == "sqm" and (width is None or height is None):
        raise SalesDocumentValidation("按平方米计价时必须填写宽度和高度")
    area = (width * height * quantity).quantize(CENT, rounding=ROUND_HALF_UP) if width and height else Decimal("0")
    line_total = (area * unit_price if pricing_unit == "sqm" else unit_price * quantity).quantize(
        CENT, rounding=ROUND_HALF_UP
    )
    return {
        "description": description or model,
        "model": model,
        "pixel_pitch": _text(item.get("pixel_pitch")),
        "width_m": float(width) if width is not None else None,
        "height_m": float(height) if height is not None else None,
        "quantity": quantity,
        "pricing_unit": pricing_unit,
        "unit_price": _money(unit_price),
        "area_sqm": _money(area),
        "line_total": _money(line_total),
        "note": _text(item.get("note")),
        "sort_order": sort_order,
    }


def _clean_items(items: list[dict]) -> tuple[list[dict], float]:
    if not items:
        raise SalesDocumentValidation("报价至少需要一条产品明细")
    clean = [_clean_item(item, index) for index, item in enumerate(items)]
    subtotal = sum((Decimal(str(item["line_total"])) for item in clean), Decimal("0"))
    return clean, _money(subtotal)


def _insert_items(conn: sqlite3.Connection, quote_id: int, items: list[dict]) -> None:
    fields = (
        "description", "model", "pixel_pitch", "width_m", "height_m", "quantity",
        "pricing_unit", "unit_price", "area_sqm", "line_total", "note", "sort_order",
    )
    for item in items:
        conn.execute(
            f"INSERT INTO quote_items(quote_id,{','.join(fields)})"
            f" VALUES ({','.join('?' * (len(fields) + 1))})",
            [quote_id, *(item[field] for field in fields)],
        )


def _total(subtotal: float, shipping: float, discount: float) -> float:
    value = Decimal(str(subtotal)) + Decimal(str(shipping)) - Decimal(str(discount))
    if value < 0:
        raise SalesDocumentValidation("折扣不能超过商品小计与运费之和")
    return _money(value)


def create_quote(conn: sqlite3.Connection, lead_no: int, data: dict, items: list[dict]) -> dict:
    ensure_schema(conn)
    clean = _clean_quote(data)
    opportunity_id, contact_id = _validate_refs(
        conn, lead_no, clean.get("opportunity_id"), clean.get("contact_id")
    )
    clean["opportunity_id"] = opportunity_id
    clean["contact_id"] = contact_id
    clean.setdefault("currency", "USD")
    clean.setdefault("shipping", 0.0)
    clean.setdefault("discount", 0.0)
    item_rows, subtotal = _clean_items(items)
    total = _total(subtotal, clean["shipping"], clean["discount"])
    now = _now()
    conn.execute("BEGIN IMMEDIATE")
    try:
        quote_no = _number(conn, "MCV", "quotes", "quote_no")
        fields = [*clean.keys(), "quote_no", "lead_no", "subtotal", "total", "created_at", "updated_at"]
        values = [*clean.values(), quote_no, lead_no, subtotal, total, now, now]
        cur = conn.execute(
            f"INSERT INTO quotes({','.join(fields)}) VALUES ({','.join('?' * len(fields))})", values
        )
        _insert_items(conn, cur.lastrowid, item_rows)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return get_quote(conn, cur.lastrowid)


def _quote_row(conn: sqlite3.Connection, quote_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT q.*, l.company_en, l.company_local, l.country, l.website,"
        " o.title opportunity_title, c.name contact_name, c.title contact_title,"
        " c.email contact_email, c.phone contact_phone"
        " FROM quotes q JOIN leads l ON l.no=q.lead_no"
        " LEFT JOIN opportunities o ON o.id=q.opportunity_id"
        " LEFT JOIN contacts c ON c.id=q.contact_id WHERE q.id=?",
        (quote_id,),
    ).fetchone()


def get_quote(conn: sqlite3.Connection, quote_id: int) -> dict | None:
    ensure_schema(conn)
    row = _quote_row(conn, quote_id)
    if row is None:
        return None
    result = dict(row)
    result["items"] = [dict(item) for item in conn.execute(
        "SELECT * FROM quote_items WHERE quote_id=? ORDER BY sort_order, id", (quote_id,)
    )]
    order = conn.execute("SELECT id, order_no, status FROM orders WHERE quote_id=?", (quote_id,)).fetchone()
    result["order"] = dict(order) if order else None
    return result


def list_quotes(conn: sqlite3.Connection, *, status: str | None = None,
                lead_no: int | None = None, opportunity_id: int | None = None) -> list[dict]:
    ensure_schema(conn)
    sql = (
        "SELECT q.*, l.company_en, l.country, o.title opportunity_title,"
        " c.name contact_name, ord.id order_id, ord.order_no, ord.status order_status"
        " FROM quotes q JOIN leads l ON l.no=q.lead_no"
        " LEFT JOIN opportunities o ON o.id=q.opportunity_id"
        " LEFT JOIN contacts c ON c.id=q.contact_id"
        " LEFT JOIN orders ord ON ord.quote_id=q.id"
    )
    where: list[str] = []
    params: list = []
    if status:
        if status not in QUOTE_STATUSES:
            raise SalesDocumentValidation("未知报价状态")
        where.append("q.status=?")
        params.append(status)
    if lead_no is not None:
        where.append("q.lead_no=?")
        params.append(lead_no)
    if opportunity_id is not None:
        where.append("q.opportunity_id=?")
        params.append(opportunity_id)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY q.created_at DESC, q.id DESC"
    return [dict(row) for row in conn.execute(sql, params)]


def update_quote(conn: sqlite3.Connection, quote_id: int, data: dict,
                 items: list[dict] | None = None) -> dict | None:
    ensure_schema(conn)
    current = get_quote(conn, quote_id)
    if current is None:
        return None
    if current["status"] != "draft":
        raise SalesDocumentValidation("只有草稿报价可以编辑")
    clean = _clean_quote(data, partial=True)
    opportunity_id = clean.get("opportunity_id", current["opportunity_id"])
    contact_id = clean.get("contact_id", current["contact_id"])
    opportunity_id, contact_id = _validate_refs(conn, current["lead_no"], opportunity_id, contact_id)
    if "opportunity_id" in clean:
        clean["opportunity_id"] = opportunity_id
    if "contact_id" in clean:
        clean["contact_id"] = contact_id
    item_rows, subtotal = (
        _clean_items(items) if items is not None
        else (current["items"], float(current["subtotal"]))
    )
    shipping = float(clean.get("shipping", current["shipping"]))
    discount = float(clean.get("discount", current["discount"]))
    clean.update({"subtotal": subtotal, "total": _total(subtotal, shipping, discount), "updated_at": _now()})
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            f"UPDATE quotes SET {', '.join(f'{key}=?' for key in clean)} WHERE id=?",
            [*clean.values(), quote_id],
        )
        if items is not None:
            conn.execute("DELETE FROM quote_items WHERE quote_id=?", (quote_id,))
            _insert_items(conn, quote_id, item_rows)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return get_quote(conn, quote_id)


_QUOTE_TRANSITIONS = {
    "draft": {"sent", "rejected"},
    "sent": {"accepted", "rejected", "expired"},
    "accepted": set(),
    "rejected": set(),
    "expired": set(),
}


def set_quote_status(conn: sqlite3.Connection, quote_id: int, status: str) -> dict | None:
    ensure_schema(conn)
    current = get_quote(conn, quote_id)
    if current is None:
        return None
    if status not in QUOTE_STATUSES:
        raise SalesDocumentValidation("未知报价状态")
    if status == current["status"]:
        return current
    if status not in _QUOTE_TRANSITIONS[current["status"]]:
        raise SalesDocumentValidation(f"报价不能从 {current['status']} 变为 {status}")
    if status == "sent" and (not current["items"] or current["total"] <= 0):
        raise SalesDocumentValidation("发送前必须有有效明细且总额大于 0")
    if status == "sent" and current["opportunity_id"] is not None:
        # Schema setup commits, so it must run before our atomic sales update.
        from app import activities
        activities.ensure_schema(conn)
    now = _now()
    fields: dict[str, str] = {"status": status, "updated_at": now}
    if status == "sent":
        fields["sent_at"] = now
    if status == "accepted":
        fields["accepted_at"] = now
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            f"UPDATE quotes SET {', '.join(f'{key}=?' for key in fields)} WHERE id=?",
            [*fields.values(), quote_id],
        )
        if status == "sent" and current["opportunity_id"] is not None:
            opportunity = conn.execute(
                "SELECT * FROM opportunities WHERE id=?", (current["opportunity_id"],)
            ).fetchone()
            if opportunity is None or opportunity["stage"] in ("won", "lost"):
                raise SalesDocumentValidation("关联商机已关闭，不能发送该报价")
            due = (dt.date.today() + dt.timedelta(days=3)).isoformat()
            action = f"跟进报价 {current['quote_no']}"
            conn.execute(
                "UPDATE opportunities SET stage='quoted', amount=?, currency=?, probability=60,"
                " next_action=?, next_action_date=?, updated_at=?, last_activity_at=? WHERE id=?",
                (current["total"], current["currency"], action, due, now, now,
                 current["opportunity_id"]),
            )
            conn.execute(
                "UPDATE leads SET stage='negotiating' WHERE no=?"
                " AND COALESCE(stage, 'new') NOT IN ('won','lost')",
                (current["lead_no"],),
            )
            activities._upsert_source(
                conn, lead_no=current["lead_no"], opportunity_id=current["opportunity_id"],
                source="opportunity", source_ref=f"opportunity:{current['opportunity_id']}",
                type="task", title=action, due_at=due, priority="normal",
                note=opportunity["title"],
            )
            activities._sync_lead(conn, current["lead_no"])
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return get_quote(conn, quote_id)


def create_order(conn: sqlite3.Connection, quote_id: int) -> dict:
    ensure_schema(conn)
    quote = get_quote(conn, quote_id)
    if quote is None:
        raise SalesDocumentValidation("报价不存在")
    if quote["status"] != "accepted":
        raise SalesDocumentValidation("只有已接受报价可以转为订单")
    if quote["order"]:
        raise SalesDocumentValidation("该报价已经生成订单")
    if quote["opportunity_id"] is not None:
        from app import activities
        activities.ensure_schema(conn)
    now = _now()
    conn.execute("BEGIN IMMEDIATE")
    try:
        order_no = _number(conn, "MCO", "orders", "order_no")
        cur = conn.execute(
            "INSERT INTO orders(order_no, quote_id, lead_no, opportunity_id, contact_id,"
            " currency, total, balance, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (order_no, quote_id, quote["lead_no"], quote["opportunity_id"], quote["contact_id"],
             quote["currency"], quote["total"], quote["total"], now, now),
        )
        if quote["opportunity_id"] is not None:
            opportunity = conn.execute(
                "SELECT * FROM opportunities WHERE id=?", (quote["opportunity_id"],)
            ).fetchone()
            if opportunity is None or opportunity["stage"] == "lost":
                raise SalesDocumentValidation("关联商机不可成交")
            conn.execute(
                "UPDATE opportunities SET stage='won', amount=?, currency=?, probability=100,"
                " updated_at=?, last_activity_at=? WHERE id=?",
                (quote["total"], quote["currency"], now, now, quote["opportunity_id"]),
            )
            conn.execute("UPDATE leads SET stage='won' WHERE no=?", (quote["lead_no"],))
            conn.execute(
                "UPDATE activities SET status='cancelled', completed_at=NULL, updated_at=?"
                " WHERE source='opportunity' AND source_ref=? AND status='open'",
                (now, f"opportunity:{quote['opportunity_id']}"),
            )
            activities._sync_lead(conn, quote["lead_no"])
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return get_order(conn, cur.lastrowid)


def _order_row(conn: sqlite3.Connection, order_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT ord.*, q.quote_no, q.title, l.company_en, l.country,"
        " o.title opportunity_title, c.name contact_name"
        " FROM orders ord JOIN quotes q ON q.id=ord.quote_id"
        " JOIN leads l ON l.no=ord.lead_no"
        " LEFT JOIN opportunities o ON o.id=ord.opportunity_id"
        " LEFT JOIN contacts c ON c.id=ord.contact_id WHERE ord.id=?",
        (order_id,),
    ).fetchone()


def get_order(conn: sqlite3.Connection, order_id: int) -> dict | None:
    ensure_schema(conn)
    row = _order_row(conn, order_id)
    return dict(row) if row else None


def list_orders(conn: sqlite3.Connection, *, status: str | None = None,
                lead_no: int | None = None) -> list[dict]:
    ensure_schema(conn)
    sql = (
        "SELECT ord.*, q.quote_no, q.title, l.company_en, l.country,"
        " o.title opportunity_title, c.name contact_name"
        " FROM orders ord JOIN quotes q ON q.id=ord.quote_id"
        " JOIN leads l ON l.no=ord.lead_no"
        " LEFT JOIN opportunities o ON o.id=ord.opportunity_id"
        " LEFT JOIN contacts c ON c.id=ord.contact_id"
    )
    where: list[str] = []
    params: list = []
    if status:
        if status not in ORDER_STATUSES:
            raise SalesDocumentValidation("未知订单状态")
        where.append("ord.status=?")
        params.append(status)
    if lead_no is not None:
        where.append("ord.lead_no=?")
        params.append(lead_no)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY ord.created_at DESC, ord.id DESC"
    return [dict(row) for row in conn.execute(sql, params)]


def _validate_order_status(current: str, target: str, paid: float, balance: float) -> None:
    if target not in ORDER_STATUSES:
        raise SalesDocumentValidation("未知订单状态")
    if target == current:
        return
    if current in ("completed", "cancelled"):
        raise SalesDocumentValidation("已完成或已取消订单不能再变更状态")
    if target == "cancelled":
        if current in ("shipped", "completed"):
            raise SalesDocumentValidation("已发货订单不能直接取消")
        return
    if target == "cancelled" or current == "cancelled":
        raise SalesDocumentValidation("订单状态流转不合法")
    current_index = ORDER_STATUSES.index(current)
    target_index = ORDER_STATUSES.index(target)
    if target_index <= current_index or target_index >= ORDER_STATUSES.index("cancelled"):
        raise SalesDocumentValidation("订单状态只能向前推进")
    if target == "deposit" and paid <= 0:
        raise SalesDocumentValidation("标记已收定金前请填写已收款金额")
    if target == "completed" and balance > 0:
        raise SalesDocumentValidation("订单收齐尾款后才能完成")


def update_order(conn: sqlite3.Connection, order_id: int, data: dict) -> dict | None:
    ensure_schema(conn)
    current = get_order(conn, order_id)
    if current is None:
        return None
    clean = {key: value for key, value in data.items() if key in ORDER_FIELDS}
    for field in ("tracking_no", "note"):
        if field in clean:
            clean[field] = _text(clean[field])
    for field, label in (("deposit_amount", "定金"), ("paid_amount", "已收款")):
        if field in clean:
            clean[field] = _money(_decimal(clean[field], label))
    for field, label in (("expected_ship_date", "预计发货日"), ("shipped_at", "实际发货日")):
        if field in clean:
            clean[field] = _date(clean[field], label)
    deposit = float(clean.get("deposit_amount", current["deposit_amount"]))
    paid = float(clean.get("paid_amount", current["paid_amount"]))
    total = float(current["total"])
    if deposit > total:
        raise SalesDocumentValidation("定金不能超过订单总额")
    if paid > total:
        raise SalesDocumentValidation("已收款不能超过订单总额")
    balance = _money(Decimal(str(total)) - Decimal(str(paid)))
    target = clean.get("status", current["status"])
    _validate_order_status(current["status"], target, paid, balance)
    if target == "shipped" and not clean.get("shipped_at") and not current["shipped_at"]:
        clean["shipped_at"] = dt.date.today().isoformat()
    clean.update({"balance": balance, "updated_at": _now()})
    conn.execute(
        f"UPDATE orders SET {', '.join(f'{key}=?' for key in clean)} WHERE id=?",
        [*clean.values(), order_id],
    )
    conn.commit()
    return get_order(conn, order_id)


def print_quote_html(conn: sqlite3.Connection, quote_id: int) -> str | None:
    quote = get_quote(conn, quote_id)
    if quote is None:
        return None

    def esc(value) -> str:
        return html.escape(str(value or "—"), quote=True)

    def amount(value) -> str:
        return f"{quote['currency']} {float(value or 0):,.2f}"

    def item_meta(item) -> str:
        values = [value for value in (item["model"], item["pixel_pitch"], item["note"]) if value]
        return f"<small>{'<br>'.join(esc(value) for value in values)}</small>" if values else ""

    rows = "".join(
        "<tr>"
        f"<td>{index}</td><td><b>{esc(item['description'])}</b>{item_meta(item)}</td>"
        f"<td>{esc(item['width_m'])} × {esc(item['height_m'])} m</td>"
        f"<td>{item['quantity']}</td><td>{esc(item['pricing_unit'])}</td>"
        f"<td>{amount(item['unit_price'])}</td><td>{amount(item['line_total'])}</td></tr>"
        for index, item in enumerate(quote["items"], 1)
    )
    terms = [
        ("Incoterm", quote["incoterm"]), ("Destination", quote["destination"]),
        ("Payment terms", quote["payment_terms"]), ("Lead time", quote["lead_time"]),
        ("Warranty", quote["warranty"]), ("Valid until", quote["valid_until"]),
    ]
    terms_html = "".join(f"<div><b>{esc(label)}</b><span>{esc(value)}</span></div>" for label, value in terms)
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{esc(quote['quote_no'])}</title>
<style>
body{{font:14px Arial,sans-serif;color:#172033;margin:0;background:#eef2f7}}main{{max-width:980px;margin:24px auto;background:white;padding:42px;box-shadow:0 8px 30px #0002}}
header{{display:flex;justify-content:space-between;border-bottom:3px solid #155eef;padding-bottom:18px}}h1{{margin:0;color:#155eef}}h2{{margin:4px 0 0;font-size:16px}}.meta{{text-align:right;line-height:1.7}}.parties{{display:grid;grid-template-columns:1fr 1fr;gap:30px;margin:28px 0}}.label{{font-size:11px;color:#667085;text-transform:uppercase}}table{{width:100%;border-collapse:collapse}}th{{background:#f2f4f7;text-align:left}}th,td{{padding:11px;border-bottom:1px solid #d0d5dd}}td small{{display:block;color:#667085;margin-top:4px}}.totals{{width:360px;margin:18px 0 24px auto}}.totals div,.terms div{{display:flex;justify-content:space-between;padding:7px 0}}.grand{{font-size:19px;border-top:2px solid #172033}}.terms{{border-top:1px solid #d0d5dd;padding-top:12px}}footer{{margin-top:35px;color:#667085;font-size:12px}}button{{position:fixed;right:20px;top:20px;padding:10px 16px}}@media print{{body{{background:white}}main{{margin:0;box-shadow:none;max-width:none}}button{{display:none}}}}
</style></head><body><button onclick="window.print()">Print / Save PDF</button><main>
<header><div><h1>MCVISUAL</h1><h2>Shenzhen Maxcolor Visual Co., Ltd.</h2></div><div class="meta"><b>QUOTATION</b><br>{esc(quote['quote_no'])}<br>Status: {esc(quote['status']).upper()}<br>Date: {esc(str(quote['created_at'])[:10])}</div></header>
<section class="parties"><div><div class="label">Quotation for</div><h2>{esc(quote['company_en'])}</h2>{esc(quote['country'])}<br>{esc(quote['website'])}</div><div><div class="label">Contact / Project</div><h2>{esc(quote['contact_name'])}</h2>{esc(quote['contact_title'])}<br>{esc(quote['contact_email'])}<br><b>{esc(quote['title'])}</b></div></section>
<table><thead><tr><th>#</th><th>Description</th><th>Size</th><th>Qty</th><th>Price by</th><th>Unit price</th><th>Amount</th></tr></thead><tbody>{rows}</tbody></table>
<section class="totals"><div><span>Subtotal</span><b>{amount(quote['subtotal'])}</b></div><div><span>Shipping</span><b>{amount(quote['shipping'])}</b></div><div><span>Discount</span><b>- {amount(quote['discount'])}</b></div><div class="grand"><span>Total</span><b>{amount(quote['total'])}</b></div></section>
<section class="terms">{terms_html}</section><footer>This quotation is generated from the current approved sales record. Bank details and final technical drawings should be confirmed before payment.</footer>
</main></body></html>"""
