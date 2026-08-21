"""LED project opportunities and pipeline hygiene.

An account can have multiple projects, so deal fields intentionally live in a
separate table instead of bloating the lead record.
"""
import datetime as dt
import sqlite3


STAGE_PROBABILITY = {
    "qualified": 20,
    "requirements": 40,
    "quoted": 60,
    "negotiation": 80,
    "won": 100,
    "lost": 0,
}
OPEN_STAGES = tuple(k for k in STAGE_PROBABILITY if k not in ("won", "lost"))
STALE_DAYS = {"qualified": 7, "requirements": 10, "quoted": 7, "negotiation": 5}

# Additive discovery columns. Keeping these on the opportunity makes the facts available
# to every existing API/agent path without creating a second project truth.
QUALIFICATION_COLUMNS = {
    "viewing_distance_m": "REAL",
    "brightness_nits": "INTEGER",
    "refresh_rate_hz": "INTEGER",
    "maintenance_access": "TEXT",
    "cabinet_size": "TEXT",
    "control_system": "TEXT",
    "installation_type": "TEXT",
    "project_timing": "TEXT",
    "budget_range": "TEXT",
    "decision_process": "TEXT",
    "technical_notes": "TEXT",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_no INTEGER NOT NULL,
    title TEXT NOT NULL,
    stage TEXT NOT NULL DEFAULT 'qualified',
    amount REAL,
    currency TEXT NOT NULL DEFAULT 'USD',
    probability INTEGER NOT NULL DEFAULT 20,
    expected_close_date TEXT,
    next_action TEXT,
    next_action_date TEXT,
    use_case TEXT,
    indoor_outdoor TEXT,
    width_m REAL,
    height_m REAL,
    quantity INTEGER NOT NULL DEFAULT 1,
    pixel_pitch TEXT,
    destination TEXT,
    incoterm TEXT,
    competitor TEXT,
    loss_reason TEXT,
    viewing_distance_m REAL,
    brightness_nits INTEGER,
    refresh_rate_hz INTEGER,
    maintenance_access TEXT,
    cabinet_size TEXT,
    control_system TEXT,
    installation_type TEXT,
    project_timing TEXT,
    budget_range TEXT,
    decision_process TEXT,
    technical_notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_activity_at TEXT NOT NULL,
    FOREIGN KEY(lead_no) REFERENCES leads(no) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_opportunities_lead ON opportunities(lead_no);
CREATE INDEX IF NOT EXISTS idx_opportunities_stage ON opportunities(stage);
CREATE INDEX IF NOT EXISTS idx_opportunities_next_action ON opportunities(next_action_date);
CREATE INDEX IF NOT EXISTS idx_opportunities_close ON opportunities(expected_close_date);
"""

FIELDS = {
    "title", "stage", "amount", "currency", "probability", "expected_close_date",
    "next_action", "next_action_date", "use_case", "indoor_outdoor", "width_m",
    "height_m", "quantity", "pixel_pitch", "destination", "incoterm",
    "competitor", "loss_reason", *QUALIFICATION_COLUMNS.keys(),
}

TEXT_FIELDS = {
    "use_case", "indoor_outdoor", "pixel_pitch", "destination", "incoterm",
    "competitor", "loss_reason", "next_action", "currency", *(
        k for k, sql_type in QUALIFICATION_COLUMNS.items() if sql_type == "TEXT"
    ),
}


class OpportunityValidation(ValueError):
    pass


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    # Existing local databases predate Spec 35. SQLite's CREATE TABLE IF NOT EXISTS does
    # not add columns, so migrate additively and never rebuild/copy the user's pipeline.
    present = {row["name"] for row in conn.execute("PRAGMA table_info(opportunities)")}
    for name, sql_type in QUALIFICATION_COLUMNS.items():
        if name not in present:
            conn.execute(f"ALTER TABLE opportunities ADD COLUMN {name} {sql_type}")
    conn.commit()


def _date(value, field: str) -> str | None:
    if value in (None, ""):
        return None
    try:
        return dt.date.fromisoformat(str(value)).isoformat()
    except ValueError as exc:
        raise OpportunityValidation(f"{field} 必须是 YYYY-MM-DD") from exc


def _validate(data: dict, *, partial: bool = False) -> dict:
    out = {k: v for k, v in data.items() if k in FIELDS}
    if "title" in out:
        out["title"] = str(out["title"]).strip()
        if not out["title"]:
            raise OpportunityValidation("项目名称不能为空")
    elif not partial:
        raise OpportunityValidation("项目名称不能为空")

    if "stage" in out and out["stage"] not in STAGE_PROBABILITY:
        raise OpportunityValidation("未知商机阶段")
    if "amount" in out and out["amount"] not in (None, ""):
        out["amount"] = float(out["amount"])
        if out["amount"] < 0:
            raise OpportunityValidation("金额不能为负数")
    if "probability" in out and out["probability"] not in (None, ""):
        out["probability"] = int(out["probability"])
        if not 0 <= out["probability"] <= 100:
            raise OpportunityValidation("成交概率必须在 0-100 之间")
    if "quantity" in out and out["quantity"] not in (None, ""):
        out["quantity"] = int(out["quantity"])
        if out["quantity"] < 1:
            raise OpportunityValidation("数量至少为 1")
    for field in ("width_m", "height_m", "viewing_distance_m"):
        if field in out and out[field] not in (None, ""):
            out[field] = float(out[field])
            if out[field] <= 0:
                raise OpportunityValidation(f"{field} 必须大于 0")
    for field in ("brightness_nits", "refresh_rate_hz"):
        if field in out and out[field] not in (None, ""):
            out[field] = int(out[field])
            if out[field] <= 0:
                raise OpportunityValidation(f"{field} 必须大于 0")
    for field in TEXT_FIELDS:
        if field in out and out[field] is not None:
            out[field] = str(out[field]).strip() or None
    for field in ("expected_close_date", "next_action_date"):
        if field in out:
            out[field] = _date(out[field], field)
    return out


def _stage_requirements(data: dict) -> None:
    stage = data["stage"]
    missing: list[str] = []
    if stage == "requirements" and not (data.get("use_case") or data.get("pixel_pitch")):
        missing.append("用途或像素间距")
    if stage == "quoted":
        if not (data.get("amount") or 0) > 0:
            missing.append("报价金额")
        if not data.get("next_action"):
            missing.append("下一步动作")
    if stage == "negotiation":
        if not (data.get("amount") or 0) > 0:
            missing.append("金额")
        if not data.get("expected_close_date"):
            missing.append("预计成交日期")
        if not data.get("next_action"):
            missing.append("下一步动作")
    if stage == "won" and not (data.get("amount") or 0) > 0:
        missing.append("成交金额")
    if stage == "lost" and not data.get("loss_reason"):
        missing.append("丢单原因")
    if missing:
        raise OpportunityValidation(f"进入该阶段前请填写：{'、'.join(missing)}")


def _sync_lead_stage(conn: sqlite3.Connection, lead_no: int, stage: str) -> None:
    if stage in ("requirements", "quoted", "negotiation"):
        conn.execute(
            "UPDATE leads SET stage='negotiating' WHERE no=?"
            " AND COALESCE(stage, 'new') NOT IN ('won','lost')",
            (lead_no,),
        )
    elif stage == "won":
        conn.execute("UPDATE leads SET stage='won' WHERE no=?", (lead_no,))


def _row(row: sqlite3.Row, today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    data = dict(row)
    amount = float(data.get("amount") or 0)
    probability = int(data.get("probability") or 0)
    data["weighted_amount"] = round(amount * probability / 100, 2)
    stage = data["stage"]
    next_date = _date(data.get("next_action_date"), "next_action_date")
    data["overdue"] = bool(stage in OPEN_STAGES and next_date and next_date < today.isoformat())
    last = dt.datetime.fromisoformat(data["last_activity_at"]).date()
    stale_days = STALE_DAYS.get(stage)
    data["stale"] = bool(stale_days and (today - last).days >= stale_days)
    return data


def create(conn: sqlite3.Connection, lead_no: int, data: dict) -> dict:
    ensure_schema(conn)
    if conn.execute("SELECT 1 FROM leads WHERE no=?", (lead_no,)).fetchone() is None:
        raise OpportunityValidation("客户不存在")
    clean = _validate(data)
    stage = clean.get("stage", "qualified")
    clean["stage"] = stage
    clean.setdefault("probability", STAGE_PROBABILITY[stage])
    clean.setdefault("currency", "USD")
    clean.setdefault("quantity", 1)
    _stage_requirements(clean)
    now = _now()
    cols = ["lead_no", *clean.keys(), "created_at", "updated_at", "last_activity_at"]
    values = [lead_no, *clean.values(), now, now, now]
    marks = ",".join("?" * len(cols))
    cur = conn.execute(
        f"INSERT INTO opportunities({','.join(cols)}) VALUES ({marks})", values)
    _sync_lead_stage(conn, lead_no, stage)
    conn.commit()
    result = get(conn, cur.lastrowid)
    from app import activities
    activities.sync_opportunity(conn, result)
    return result


def get(conn: sqlite3.Connection, opportunity_id: int, today: dt.date | None = None) -> dict | None:
    ensure_schema(conn)
    row = conn.execute(
        "SELECT o.*, l.company_en, l.country FROM opportunities o"
        " JOIN leads l ON l.no=o.lead_no WHERE o.id=?",
        (opportunity_id,),
    ).fetchone()
    return _row(row, today) if row else None


def update(conn: sqlite3.Connection, opportunity_id: int, data: dict) -> dict | None:
    ensure_schema(conn)
    current = get(conn, opportunity_id)
    if current is None:
        return None
    clean = _validate(data, partial=True)
    merged = {k: current.get(k) for k in FIELDS}
    merged.update(clean)
    stage = merged["stage"]
    if "stage" in clean and "probability" not in clean:
        clean["probability"] = STAGE_PROBABILITY[stage]
        merged["probability"] = clean["probability"]
    _stage_requirements(merged)
    if not clean:
        return current
    clean["updated_at"] = _now()
    clean["last_activity_at"] = clean["updated_at"]
    sets = ", ".join(f"{k}=?" for k in clean)
    conn.execute(
        f"UPDATE opportunities SET {sets} WHERE id=?",
        [*clean.values(), opportunity_id],
    )
    _sync_lead_stage(conn, current["lead_no"], stage)
    conn.commit()
    result = get(conn, opportunity_id)
    from app import activities
    activities.sync_opportunity(conn, result)
    return result


def list_all(conn: sqlite3.Connection, *, stage: str | None = None,
             lead_no: int | None = None, attention: bool = False,
             today: dt.date | None = None) -> list[dict]:
    ensure_schema(conn)
    sql = (
        "SELECT o.*, l.company_en, l.country FROM opportunities o"
        " JOIN leads l ON l.no=o.lead_no"
    )
    where, params = [], []
    if stage:
        where.append("o.stage=?")
        params.append(stage)
    if lead_no is not None:
        where.append("o.lead_no=?")
        params.append(lead_no)
    if where:
        sql += " WHERE " + " AND ".join(where)
    rows = [_row(r, today) for r in conn.execute(sql, params)]
    if attention:
        rows = [r for r in rows if r["overdue"] or r["stale"]]
    return sorted(
        rows,
        key=lambda r: (
            not r["overdue"], not r["stale"],
            r.get("next_action_date") or "9999-12-31",
            -(r.get("amount") or 0),
        ),
    )


def touch_for_lead(conn: sqlite3.Connection, lead_no: int) -> None:
    ensure_schema(conn)
    now = _now()
    conn.execute(
        "UPDATE opportunities SET last_activity_at=?, updated_at=?"
        " WHERE lead_no=? AND stage NOT IN ('won','lost')",
        (now, now, lead_no),
    )
    conn.commit()


def stats(conn: sqlite3.Connection, today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    rows = list_all(conn, today=today)
    open_rows = [r for r in rows if r["stage"] in OPEN_STAGES]
    month = today.strftime("%Y-%m")
    closing = [r for r in open_rows if (r.get("expected_close_date") or "").startswith(month)]
    won = [r for r in rows if r["stage"] == "won"
           and (r.get("updated_at") or "").startswith(month)]
    by_stage = {stage: 0 for stage in STAGE_PROBABILITY}
    for r in rows:
        by_stage[r["stage"]] += 1
    return {
        "open_count": len(open_rows),
        "open_amount": round(sum(r.get("amount") or 0 for r in open_rows), 2),
        "weighted_amount": round(sum(r["weighted_amount"] for r in open_rows), 2),
        "closing_this_month": round(sum(r.get("amount") or 0 for r in closing), 2),
        "won_this_month": round(sum(r.get("amount") or 0 for r in won), 2),
        "attention_count": sum(1 for r in open_rows if r["overdue"] or r["stale"]),
        "overdue_count": sum(1 for r in open_rows if r["overdue"]),
        "stale_count": sum(1 for r in open_rows if r["stale"]),
        "by_stage": by_stage,
    }
