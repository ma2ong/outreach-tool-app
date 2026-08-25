"""Sales activities: the single source of truth for every next action."""
import datetime as dt
import sqlite3


TYPES = ("task", "call", "email", "whatsapp", "instagram", "meeting", "quote")
PRIORITIES = ("high", "normal", "low")
STATUSES = ("open", "done", "cancelled")

SCHEMA = """
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_no INTEGER NOT NULL,
    opportunity_id INTEGER,
    type TEXT NOT NULL DEFAULT 'task',
    title TEXT NOT NULL,
    due_at TEXT,
    priority TEXT NOT NULL DEFAULT 'normal',
    status TEXT NOT NULL DEFAULT 'open',
    source TEXT NOT NULL DEFAULT 'manual',
    source_ref TEXT,
    note TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(lead_no) REFERENCES leads(no) ON DELETE CASCADE,
    FOREIGN KEY(opportunity_id) REFERENCES opportunities(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_activities_status_due ON activities(status, due_at);
CREATE INDEX IF NOT EXISTS idx_activities_lead ON activities(lead_no, status);
CREATE INDEX IF NOT EXISTS idx_activities_opportunity ON activities(opportunity_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_activities_source_ref
    ON activities(source, source_ref)
    WHERE source_ref IS NOT NULL AND source_ref != '';
"""

FIELDS = {"type", "title", "due_at", "priority", "status", "note"}


class ActivityValidation(ValueError):
    pass


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def _today() -> str:
    return dt.date.today().isoformat()


def ensure_schema(conn: sqlite3.Connection) -> None:
    # Activities may be invoked by reply polling in tests and maintenance scripts
    # that only initialized the base schema, so own the dependency instead of
    # relying on FastAPI startup order.
    from app.db import tables_exist
    from app.opportunities import ensure_schema as ensure_opportunity_schema
    # Already set up: stay read-only. `activities` only ever gets created after
    # `opportunities` (its foreign key), so its presence covers both.
    if tables_exist(conn, "activities"):
        return
    ensure_opportunity_schema(conn)
    conn.executescript(SCHEMA)
    conn.commit()


def _date(value, field: str = "due_at") -> str | None:
    if value in (None, ""):
        return None
    try:
        return dt.date.fromisoformat(str(value)).isoformat()
    except ValueError as exc:
        raise ActivityValidation(f"{field} 必须是 YYYY-MM-DD") from exc


def _validate(data: dict, *, partial: bool = False) -> dict:
    clean = {k: v for k, v in data.items() if k in FIELDS}
    if "title" in clean:
        clean["title"] = str(clean["title"] or "").strip()
        if not clean["title"]:
            raise ActivityValidation("任务标题不能为空")
    elif not partial:
        raise ActivityValidation("任务标题不能为空")
    if "type" in clean and clean["type"] not in TYPES:
        raise ActivityValidation("未知任务类型")
    if "priority" in clean and clean["priority"] not in PRIORITIES:
        raise ActivityValidation("未知优先级")
    if "status" in clean and clean["status"] not in STATUSES:
        raise ActivityValidation("未知任务状态")
    if "due_at" in clean:
        clean["due_at"] = _date(clean["due_at"])
    if "note" in clean and clean["note"] is not None:
        clean["note"] = str(clean["note"]).strip() or None
    return clean


def _check_relations(conn: sqlite3.Connection, lead_no: int,
                     opportunity_id: int | None = None) -> None:
    if conn.execute("SELECT 1 FROM leads WHERE no=?", (lead_no,)).fetchone() is None:
        raise ActivityValidation("客户不存在")
    if opportunity_id is None:
        return
    row = conn.execute(
        "SELECT lead_no FROM opportunities WHERE id=?", (opportunity_id,)).fetchone()
    if row is None:
        raise ActivityValidation("商机不存在")
    if row["lead_no"] != lead_no:
        raise ActivityValidation("任务客户与商机客户不一致")


def _sync_lead(conn: sqlite3.Connection, lead_no: int) -> None:
    row = conn.execute(
        "SELECT title, due_at FROM activities WHERE lead_no=? AND status='open'"
        " ORDER BY due_at IS NULL, due_at,"
        "          CASE priority WHEN 'high' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END, id LIMIT 1",
        (lead_no,),
    ).fetchone()
    conn.execute(
        "UPDATE leads SET next_action=?, follow_up_date=? WHERE no=?",
        (row["title"] if row else None, row["due_at"] if row else None, lead_no),
    )


def sync_lead(conn: sqlite3.Connection, lead_no: int) -> None:
    ensure_schema(conn)
    _sync_lead(conn, lead_no)
    conn.commit()


def get(conn: sqlite3.Connection, activity_id: int) -> dict | None:
    ensure_schema(conn)
    row = conn.execute(
        "SELECT a.*, l.company_en, l.country, o.title AS opportunity_title"
        " FROM activities a JOIN leads l ON l.no=a.lead_no"
        " LEFT JOIN opportunities o ON o.id=a.opportunity_id WHERE a.id=?",
        (activity_id,),
    ).fetchone()
    return dict(row) if row else None


def create(conn: sqlite3.Connection, lead_no: int, data: dict,
           opportunity_id: int | None = None) -> dict:
    ensure_schema(conn)
    _check_relations(conn, lead_no, opportunity_id)
    clean = _validate(data)
    clean.setdefault("type", "task")
    clean.setdefault("priority", "normal")
    clean.setdefault("status", "open")
    now = _now()
    cols = ["lead_no", "opportunity_id", *clean.keys(), "source", "created_at", "updated_at"]
    values = [lead_no, opportunity_id, *clean.values(), "manual", now, now]
    cur = conn.execute(
        f"INSERT INTO activities({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
        values,
    )
    _sync_lead(conn, lead_no)
    conn.commit()
    return get(conn, cur.lastrowid)


def update(conn: sqlite3.Connection, activity_id: int, data: dict) -> dict | None:
    ensure_schema(conn)
    current = get(conn, activity_id)
    if current is None:
        return None
    clean = _validate(data, partial=True)
    if not clean:
        return current
    if clean.get("status") == "done":
        clean["completed_at"] = _now()
    elif clean.get("status") in ("open", "cancelled"):
        clean["completed_at"] = None
    clean["updated_at"] = _now()
    conn.execute(
        f"UPDATE activities SET {', '.join(f'{k}=?' for k in clean)} WHERE id=?",
        [*clean.values(), activity_id],
    )
    _sync_lead(conn, current["lead_no"])
    conn.commit()
    return get(conn, activity_id)


def complete(conn: sqlite3.Connection, activity_id: int) -> dict | None:
    return update(conn, activity_id, {"status": "done"})


def list_all(conn: sqlite3.Connection, *, status: str | None = "open",
             scope: str | None = None, lead_no: int | None = None,
             opportunity_id: int | None = None, limit: int = 500) -> list[dict]:
    ensure_schema(conn)
    where, params = [], []
    if status:
        if status not in STATUSES:
            raise ActivityValidation("未知任务状态")
        where.append("a.status=?")
        params.append(status)
    today = _today()
    if scope == "overdue":
        where.append("a.status='open' AND a.due_at < ?")
        params.append(today)
    elif scope == "today":
        where.append("a.status='open' AND a.due_at = ?")
        params.append(today)
    elif scope == "upcoming":
        where.append("a.status='open' AND a.due_at > ?")
        params.append(today)
    elif scope == "no_due":
        where.append("a.status='open' AND (a.due_at IS NULL OR a.due_at='')")
    elif scope not in (None, ""):
        raise ActivityValidation("未知任务范围")
    if lead_no is not None:
        where.append("a.lead_no=?")
        params.append(lead_no)
    if opportunity_id is not None:
        where.append("a.opportunity_id=?")
        params.append(opportunity_id)
    sql = (
        "SELECT a.*, l.company_en, l.country, o.title AS opportunity_title"
        " FROM activities a JOIN leads l ON l.no=a.lead_no"
        " LEFT JOIN opportunities o ON o.id=a.opportunity_id"
    )
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += (
        " ORDER BY CASE a.status WHEN 'open' THEN 0 ELSE 1 END,"
        " a.due_at IS NULL, a.due_at,"
        " CASE a.priority WHEN 'high' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END, a.id DESC LIMIT ?"
    )
    params.append(max(1, min(limit, 1000)))
    return [dict(r) for r in conn.execute(sql, params)]


def stats(conn: sqlite3.Connection) -> dict:
    ensure_schema(conn)
    today = _today()
    row = conn.execute(
        "SELECT"
        " SUM(CASE WHEN status='open' AND due_at < ? THEN 1 ELSE 0 END) overdue,"
        " SUM(CASE WHEN status='open' AND due_at = ? THEN 1 ELSE 0 END) today,"
        " SUM(CASE WHEN status='open' AND due_at > ? THEN 1 ELSE 0 END) upcoming,"
        " SUM(CASE WHEN status='open' AND (due_at IS NULL OR due_at='') THEN 1 ELSE 0 END) no_due,"
        " SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) open_count"
        " FROM activities",
        (today, today, today),
    ).fetchone()
    return {k: int(row[k] or 0) for k in row.keys()}


def _upsert_source(conn: sqlite3.Connection, *, lead_no: int,
                   opportunity_id: int | None, source: str, source_ref: str,
                   type: str, title: str, due_at: str | None,
                   priority: str = "normal", note: str | None = None) -> tuple[int, bool]:
    existing = conn.execute(
        "SELECT id FROM activities WHERE source=? AND source_ref=?", (source, source_ref)
    ).fetchone()
    now = _now()
    if existing:
        conn.execute(
            "UPDATE activities SET lead_no=?, opportunity_id=?, type=?, title=?, due_at=?,"
            " priority=?, status='open', note=?, completed_at=NULL, updated_at=? WHERE id=?",
            (lead_no, opportunity_id, type, title, due_at, priority, note, now, existing["id"]),
        )
        return existing["id"], False
    cur = conn.execute(
        "INSERT INTO activities(lead_no, opportunity_id, type, title, due_at, priority,"
        " status, source, source_ref, note, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?)",
        (lead_no, opportunity_id, type, title, due_at, priority,
         source, source_ref, note, now, now),
    )
    return cur.lastrowid, True


def create_reply_task(conn: sqlite3.Connection, inbox_id: int) -> bool:
    ensure_schema(conn)
    row = conn.execute(
        "SELECT m.*, l.company_en FROM inbox_messages m"
        " JOIN leads l ON l.no=m.lead_no WHERE m.id=? AND m.kind='reply'",
        (inbox_id,),
    ).fetchone()
    if row is None:
        return False
    channel = row["channel"] if row["channel"] in TYPES else "task"
    _, created = _upsert_source(
        conn, lead_no=row["lead_no"], opportunity_id=None,
        source="reply", source_ref=f"inbox:{inbox_id}", type=channel,
        title=f"回复客户：{row['company_en']}", due_at=_today(), priority="high",
        note=(row["subject"] or row["body"] or "")[:500] or None,
    )
    _sync_lead(conn, row["lead_no"])
    conn.commit()
    return created


def complete_reply_task(conn: sqlite3.Connection, inbox_id: int) -> None:
    ensure_schema(conn)
    row = conn.execute(
        "SELECT id, lead_no FROM activities WHERE source='reply' AND source_ref=?",
        (f"inbox:{inbox_id}",),
    ).fetchone()
    if row is None:
        return
    now = _now()
    conn.execute(
        "UPDATE activities SET status='done', completed_at=?, updated_at=? WHERE id=?",
        (now, now, row["id"]),
    )
    _sync_lead(conn, row["lead_no"])
    conn.commit()


def sync_opportunity(conn: sqlite3.Connection, opportunity: dict) -> None:
    ensure_schema(conn)
    ref = f"opportunity:{opportunity['id']}"
    active = (
        opportunity.get("stage") not in ("won", "lost")
        and bool(opportunity.get("next_action"))
        and bool(opportunity.get("next_action_date"))
    )
    if active:
        _upsert_source(
            conn, lead_no=opportunity["lead_no"], opportunity_id=opportunity["id"],
            source="opportunity", source_ref=ref, type="task",
            title=opportunity["next_action"], due_at=_date(opportunity["next_action_date"]),
            priority="normal", note=opportunity.get("title"),
        )
    else:
        conn.execute(
            "UPDATE activities SET status='cancelled', completed_at=NULL, updated_at=?"
            " WHERE source='opportunity' AND source_ref=? AND status='open'",
            (_now(), ref),
        )
    _sync_lead(conn, opportunity["lead_no"])
    conn.commit()


def upsert_legacy_for_lead(conn: sqlite3.Connection, lead_no: int) -> None:
    ensure_schema(conn)
    lead = conn.execute(
        "SELECT next_action, follow_up_date FROM leads WHERE no=?", (lead_no,)
    ).fetchone()
    if lead is None:
        return
    ref = f"lead:{lead_no}:legacy"
    if lead["next_action"] or lead["follow_up_date"]:
        _upsert_source(
            conn, lead_no=lead_no, opportunity_id=None, source="legacy", source_ref=ref,
            type="task", title=lead["next_action"] or "跟进客户",
            due_at=_date(lead["follow_up_date"]), priority="normal",
        )
    else:
        conn.execute(
            "UPDATE activities SET status='cancelled', updated_at=?"
            " WHERE source='legacy' AND source_ref=? AND status='open'",
            (_now(), ref),
        )
    _sync_lead(conn, lead_no)
    conn.commit()


def migrate_existing(conn: sqlite3.Connection) -> dict:
    """Idempotently adopt old next actions, pending replies and opportunity actions."""
    ensure_schema(conn)
    created = 0
    touched: set[int] = set()
    leads = conn.execute(
        "SELECT no, next_action, follow_up_date FROM leads"
        " WHERE COALESCE(next_action, '') != '' OR COALESCE(follow_up_date, '') != ''"
    ).fetchall()
    for lead in leads:
        ref = f"lead:{lead['no']}:legacy"
        if conn.execute(
            "SELECT 1 FROM activities WHERE source='legacy' AND source_ref=?", (ref,)
        ).fetchone() is None and conn.execute(
            "SELECT 1 FROM activities WHERE lead_no=?", (lead["no"],)
        ).fetchone() is None:
            _upsert_source(
                conn, lead_no=lead["no"], opportunity_id=None, source="legacy",
                source_ref=ref, type="task", title=lead["next_action"] or "跟进客户",
                due_at=_date(lead["follow_up_date"]), priority="normal",
            )
            created += 1
            touched.add(lead["no"])
    replies = conn.execute(
        "SELECT id, lead_no FROM inbox_messages"
        " WHERE kind='reply' AND handled_at IS NULL"
    ).fetchall()
    for reply in replies:
        if create_reply_task(conn, reply["id"]):
            created += 1
        touched.add(reply["lead_no"])
    try:
        opportunities = conn.execute("SELECT * FROM opportunities").fetchall()
    except sqlite3.OperationalError:
        opportunities = []
    for opportunity in opportunities:
        before = conn.execute(
            "SELECT 1 FROM activities WHERE source='opportunity' AND source_ref=?",
            (f"opportunity:{opportunity['id']}",),
        ).fetchone()
        sync_opportunity(conn, dict(opportunity))
        if before is None and opportunity["next_action"] and opportunity["next_action_date"]:
            created += 1
        touched.add(opportunity["lead_no"])
    for lead_no in touched:
        _sync_lead(conn, lead_no)
    conn.commit()
    return {"created": created, "leads_touched": len(touched)}
