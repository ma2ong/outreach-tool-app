import json
import sqlite3

from app.customer_types import customer_types
from app.models import Lead, Note, OutreachStatus, Stats, Template

_LEAD_RELATIONS = ("outreach", "notes")
# Filled after the row is read, from other tables (docs/60). Pulling them off the row
# hands pydantic a None where it wants a list.
_LEAD_COMPUTED = ("primary_contact", "primary_title", "customer_types")


def _lead_from_row(row: sqlite3.Row, outreach: list[OutreachStatus],
                   notes: list[Note] | None = None) -> Lead:
    d = dict(row)
    d["whatsapp_verified"] = bool(d.get("whatsapp_verified"))
    d["stage"] = d.get("stage") or "new"
    raw = d.get("source_urls")
    d["source_urls"] = json.loads(raw) if raw else []
    fields = {k: d.get(k) for k in Lead.model_fields
              if k not in _LEAD_RELATIONS and k not in _LEAD_COMPUTED}
    return Lead(**fields, outreach=outreach, notes=notes or [])


def _primary_contacts(conn, lead_nos: list[int]) -> dict[int, tuple[str | None, str | None]]:
    """The one person to show per company (docs/60 R4).

    `is_primary` already exists and already means this; picking a different rule here
    would give the list a different answer than the drawer.
    """
    if not lead_nos:
        return {}
    q = ("SELECT lead_no, name, title, is_primary FROM contacts WHERE lead_no IN (%s)"
         " AND COALESCE(name,'') <> '' ORDER BY is_primary DESC, id ASC"
         % ",".join("?" * len(lead_nos)))
    found: dict[int, tuple[str | None, str | None]] = {}
    for row in conn.execute(q, lead_nos):
        found.setdefault(row["lead_no"], (row["name"], row["title"]))
    return found


def _outreach_for(conn: sqlite3.Connection, lead_nos: list[int]) -> dict[int, list[OutreachStatus]]:
    if not lead_nos:
        return {}
    q = "SELECT * FROM outreach WHERE lead_no IN (%s)" % ",".join("?" * len(lead_nos))
    out: dict[int, list[OutreachStatus]] = {}
    for r in conn.execute(q, lead_nos):
        out.setdefault(r["lead_no"], []).append(OutreachStatus(
            channel=r["channel"], status=r["status"], touch_count=r["touch_count"] or 0,
            message_sent_date=r["message_sent_date"], reply_received=bool(r["reply_received"]),
            exclude_reason=r["exclude_reason"],
        ))
    return out


_HAS_COLS = {"phone": "phone", "instagram": "instagram", "email": "email"}
_TOUCHED = "status IN ('messaged','replied')"

# "Due for follow-up": messaged >= N days ago with no reply and not won/lost,
# OR a manually set follow-up date that has arrived.
def _due_clause(days: int) -> tuple[str, list]:
    clause = (
        "(((l.stage IS NULL OR l.stage NOT IN ('won','lost'))"
        " AND l.no IN (SELECT lead_no FROM outreach WHERE status='messaged'"
        "   AND message_sent_date IS NOT NULL AND message_sent_date <= date('now', ?))"
        " AND l.no NOT IN (SELECT lead_no FROM outreach WHERE status='replied'))"
        " OR (l.follow_up_date IS NOT NULL AND l.follow_up_date != ''"
        "   AND l.follow_up_date <= date('now')))"
    )
    return clause, [f"-{days} days"]


_SORT_COLS = {"no", "company_en", "country", "city", "stage", "target_fit"}
# target_fit is stored as "AV集成商 (85)"; "fit" sorts by that parenthesized score
# so the best-fit buyer types (rental 90 > integrator 85 > reseller 80) float up.
# Unscored leads (quick-add/discovered/NULL) parse to 0 and sink to the bottom.
_FIT_SORT = "CAST(substr(l.target_fit, instr(l.target_fit, '(') + 1) AS INTEGER)"


def _lead_filters(country, channel, status, search, has, follow_up, follow_up_days):
    where, params = [], []
    if country:
        where.append("l.country = ?")
        params.append(country)
    if search:
        where.append(
            "(l.company_en LIKE ? OR l.website LIKE ? OR l.city LIKE ?"
            " OR EXISTS (SELECT 1 FROM contacts c WHERE c.lead_no=l.no"
            "   AND (c.name LIKE ? OR c.email LIKE ? OR c.phone LIKE ? OR c.title LIKE ?)))")
        params += [f"%{search}%"] * 7
    if follow_up == "due":
        clause, cp = _due_clause(follow_up_days)
        where.append(clause)
        params += cp
    if has:
        col = _HAS_COLS.get(has)
        if col:
            if has in ("email", "phone"):
                where.append(
                    f"((l.{col} IS NOT NULL AND l.{col} != '') OR EXISTS"
                    f" (SELECT 1 FROM contacts c WHERE c.lead_no=l.no"
                    f" AND c.{col} IS NOT NULL AND c.{col} != ''))")
            else:
                where.append(f"l.{col} IS NOT NULL AND l.{col} != ''")
    if status == "untouched":
        if channel:
            where.append("l.no NOT IN (SELECT lead_no FROM outreach"
                         f" WHERE channel = ? AND {_TOUCHED})")
            params.append(channel)
        else:
            where.append(f"l.no NOT IN (SELECT lead_no FROM outreach WHERE {_TOUCHED})")
        channel = status = None
    if channel or status:
        sub, sp = [], []
        if channel:
            sub.append("channel = ?")
            sp.append(channel)
        if status:
            sub.append("status = ?")
            sp.append(status)
        where.append("l.no IN (SELECT lead_no FROM outreach WHERE %s)" % " AND ".join(sub))
        params += sp
    return where, params


def count_leads(conn, country=None, channel=None, status=None, search=None, has=None,
                follow_up=None, follow_up_days=7) -> int:
    from app.contacts import ensure_schema
    ensure_schema(conn)
    where, params = _lead_filters(country, channel, status, search, has, follow_up, follow_up_days)
    sql = "SELECT COUNT(*) c FROM leads l"
    if where:
        sql += " WHERE " + " AND ".join(where)
    return conn.execute(sql, params).fetchone()["c"]


def list_leads(conn, country=None, channel=None, status=None, search=None, has=None,
               follow_up=None, follow_up_days=7,
               sort=None, order="asc", limit=None, offset=0) -> list[Lead]:
    from app.contacts import ensure_schema
    ensure_schema(conn)
    where, params = _lead_filters(country, channel, status, search, has, follow_up, follow_up_days)
    sql = "SELECT l.* FROM leads l"
    if where:
        sql += " WHERE " + " AND ".join(where)
    direction = "DESC" if str(order).lower() == "desc" else "ASC"
    if sort == "fit":
        sql += f" ORDER BY {_FIT_SORT} {direction}, l.no ASC"
    else:
        col = sort if sort in _SORT_COLS else "no"
        sql += f" ORDER BY l.{col} {direction}, l.no {direction}"
    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params += [limit, offset]
    rows = list(conn.execute(sql, params))
    nos = [r["no"] for r in rows]
    om = _outreach_for(conn, nos)
    pc = _primary_contacts(conn, nos)
    out = []
    for r in rows:
        lead = _lead_from_row(r, om.get(r["no"], []))
        name, title = pc.get(r["no"], (None, None))
        lead.primary_contact = name or lead.contact_name
        lead.primary_title = title or lead.title
        lead.customer_types = customer_types(r["tags"] if "tags" in r.keys() else None)
        out.append(lead)
    return out


def advance_stage(conn, no: int, target: str) -> None:
    """Keep the sales stage in step with reality so nobody has to maintain it by hand.

    Only moves forward through new -> contacted -> replied, and never overrules a
    stage Allen set himself (negotiating / won / lost stay put).
    """
    order = {"new": 0, "contacted": 1, "replied": 2}
    row = conn.execute("SELECT stage FROM leads WHERE no=?", (no,)).fetchone()
    if row is None:
        return
    current = row["stage"] or "new"
    if current not in order or order.get(target, 0) <= order[current]:
        return
    conn.execute("UPDATE leads SET stage=? WHERE no=?", (target, no))
    conn.commit()


def mark_replied(conn, no: int, channel: str) -> None:
    conn.execute(
        "INSERT INTO outreach(lead_no, channel, status) VALUES (?, ?, 'replied')"
        " ON CONFLICT(lead_no, channel) DO UPDATE SET status='replied'",
        (no, channel),
    )
    conn.commit()
    advance_stage(conn, no, "replied")
    # A reply ends follow-up: stop any active sequence enrollments on this channel
    # so the due queue never chases someone who already answered.
    from app import sequences
    sequences.stop_for_lead(conn, no, channel)
    from app import opportunities
    opportunities.touch_for_lead(conn, no)


def get_lead(conn, no: int) -> Lead | None:
    row = conn.execute("SELECT * FROM leads WHERE no = ?", (no,)).fetchone()
    if row is None:
        return None
    om = _outreach_for(conn, [no])
    return _lead_from_row(row, om.get(no, []), list_notes(conn, no))


_EDITABLE = {"company_en", "company_local", "country", "region", "city", "contact_name",
             "title", "email", "phone", "website", "instagram", "facebook", "linkedin",
             "business", "target_fit", "stage", "tags", "follow_up_date", "next_action",
             "do_not_contact", "brief", "hook"}

def update_lead(conn, no: int, fields: dict) -> bool:
    cols = {k: v for k, v in fields.items() if k in _EDITABLE}
    if not cols:
        return conn.execute("SELECT 1 FROM leads WHERE no = ?", (no,)).fetchone() is not None
    # Typed by Allen beats scraped off a footer, and the record should say which it is.
    # Stamped here rather than at each caller so no edit path can forget.
    if "email" in cols:
        cols["email_source"] = "manual"
    if "country" in cols:
        from app import countries
        cols["country"] = countries.normalize(cols["country"])
    sets = ", ".join(f"{k} = ?" for k in cols) + ", updated_at = ?"
    params = [*cols.values(), _dt.datetime.now(_dt.UTC).isoformat(), no]
    cur = conn.execute(f"UPDATE leads SET {sets} WHERE no = ?", params)
    conn.commit()
    if {"follow_up_date", "next_action"} & cols.keys() and cur.rowcount > 0:
        from app import activities
        activities.upsert_legacy_for_lead(conn, no)
    if {"contact_name", "title", "email", "phone", "linkedin", "email_status"} & cols.keys() and cur.rowcount > 0:
        from app import contacts
        contacts.upsert_primary_from_lead(conn, no)
    return cur.rowcount > 0


# Everything that hangs off a lead. SQLite has no cascade here, and an orphan row would
# keep a deleted company alive in the inbox, the send log and the pipeline counts.
_LEAD_CHILDREN = ("outreach", "notes", "sequence_enrollments", "send_log",
                  "inbox_messages", "activities", "buying_signals", "orders", "quotes",
                  "opportunities", "contacts")


def delete_lead(conn, no: int) -> bool:
    """Erase a lead entirely. For rows that turn out not to be customers at all — a
    competitor, or a Chinese factory's overseas branch. 'Do not contact' is the wrong
    tool for those: it stops the sending but still counts them in the funnel."""
    from app.opportunities import ensure_schema as ensure_opportunity_schema
    from app.activities import ensure_schema as ensure_activity_schema
    from app.contacts import ensure_schema as ensure_contact_schema
    from app.sales_documents import ensure_schema as ensure_sales_document_schema
    from app.sales_intelligence import ensure_schema as ensure_sales_intelligence_schema
    ensure_opportunity_schema(conn)
    ensure_activity_schema(conn)
    ensure_contact_schema(conn)
    ensure_sales_document_schema(conn)
    ensure_sales_intelligence_schema(conn)
    if conn.execute("SELECT 1 FROM leads WHERE no = ?", (no,)).fetchone() is None:
        return False
    for table in _LEAD_CHILDREN:
        conn.execute(f"DELETE FROM {table} WHERE lead_no = ?", (no,))
    conn.execute("DELETE FROM leads WHERE no = ?", (no,))
    conn.commit()
    return True


def add_note(conn, no: int, text: str) -> int:
    now = _dt.datetime.now(_dt.UTC).isoformat()
    cur = conn.execute("INSERT INTO notes(lead_no, created_at, text) VALUES (?, ?, ?)",
                       (no, now, text))
    conn.commit()
    from app import opportunities
    opportunities.touch_for_lead(conn, no)
    return cur.lastrowid


def list_notes(conn, no: int) -> list[Note]:
    rows = conn.execute(
        "SELECT id, created_at, text FROM notes WHERE lead_no = ? ORDER BY id DESC", (no,))
    return [Note(id=r["id"], created_at=r["created_at"], text=r["text"]) for r in rows]


def list_templates(conn, channel: str | None = None) -> list[Template]:
    sql = "SELECT id, name, channel, subject, body, lang FROM templates"
    params: list = []
    if channel:
        sql += " WHERE channel = ?"
        params.append(channel)
    sql += " ORDER BY id"
    return [Template(**dict(r)) for r in conn.execute(sql, params)]


def add_template(conn, name: str, channel: str, subject: str | None, body: str,
                 lang: str | None = None) -> int:
    cur = conn.execute(
        "INSERT INTO templates(name, channel, subject, body, lang) VALUES (?, ?, ?, ?, ?)",
        (name, channel, subject, body, lang))
    conn.commit()
    return cur.lastrowid


def delete_template(conn, tid: int) -> bool:
    cur = conn.execute("DELETE FROM templates WHERE id = ?", (tid,))
    conn.commit()
    return cur.rowcount > 0


def find_duplicate(conn, website=None, instagram=None, company_en=None) -> int | None:
    from app.dedupe import normalize_website
    checks = []
    if website:
        checks.append(("website", normalize_website(website)))
    if instagram:
        checks.append(("instagram", instagram))
    if company_en:
        checks.append(("company_en", company_en))
    for col, val in checks:
        row = conn.execute(f"SELECT no FROM leads WHERE lower({col}) = lower(?)", (val,)).fetchone()
        if row:
            return row["no"]
    return None


def stats(conn) -> Stats:
    from app.contacts import ensure_schema as ensure_contact_schema
    from app.opportunities import ensure_schema as ensure_opportunity_schema
    from app.sales_documents import ensure_schema as ensure_sales_document_schema
    ensure_contact_schema(conn)
    ensure_opportunity_schema(conn)
    ensure_sales_document_schema(conn)
    total = conn.execute("SELECT COUNT(*) c FROM leads").fetchone()["c"]
    by_country = {r["country"]: r["c"] for r in conn.execute(
        "SELECT country, COUNT(*) c FROM leads WHERE country IS NOT NULL GROUP BY country"
    )}
    by_cs: dict[str, dict[str, int]] = {}
    for r in conn.execute(
        "SELECT channel, status, COUNT(*) c FROM outreach GROUP BY channel, status"
    ):
        by_cs.setdefault(r["channel"], {})[r["status"]] = r["c"]

    def _count(sql, params=()):
        return conn.execute(sql, params).fetchone()["c"]

    reach: dict[str, dict[str, int]] = {}
    for ch, col in (("email", "email"), ("whatsapp", "phone"), ("instagram", "instagram")):
        have = _count(f"SELECT COUNT(*) c FROM leads WHERE {col} IS NOT NULL AND {col} != ''")
        messaged = _count("SELECT COUNT(DISTINCT lead_no) c FROM outreach"
                          " WHERE channel=? AND status IN ('messaged','replied')", (ch,))
        replied = _count("SELECT COUNT(DISTINCT lead_no) c FROM outreach"
                         " WHERE channel=? AND status='replied'", (ch,))
        untouched = _count(
            f"SELECT COUNT(*) c FROM leads l WHERE l.{col} IS NOT NULL AND l.{col} != ''"
            " AND l.no NOT IN (SELECT lead_no FROM outreach"
            " WHERE channel=? AND status IN ('messaged','replied','excluded'))", (ch,))
        reach[ch] = {"have": have, "messaged": messaged, "replied": replied, "untouched": untouched}

    funnel = {
        "total": total,
        "with_contact": _count(
            "SELECT COUNT(*) c FROM leads l WHERE"
            " (COALESCE(l.email,'')!='' OR COALESCE(l.phone,'')!=''"
            " OR COALESCE(l.instagram,'')!='' OR COALESCE(l.facebook,'')!='')"
            " OR EXISTS (SELECT 1 FROM contacts c WHERE c.lead_no=l.no"
            " AND (COALESCE(c.email,'')!='' OR COALESCE(c.phone,'')!=''"
            " OR COALESCE(c.linkedin,'')!=''))"),
        "verified": _count(
            "SELECT COUNT(*) c FROM leads l WHERE l.email_status IN ('valid','role')"
            " OR EXISTS (SELECT 1 FROM contacts c WHERE c.lead_no=l.no"
            " AND c.email_status IN ('valid','role'))"),
        "touched": _count("SELECT COUNT(DISTINCT lead_no) c FROM outreach"
                          " WHERE status IN ('messaged','replied')"),
        "replied": _count("SELECT COUNT(DISTINCT lead_no) c FROM outreach WHERE status='replied'"),
        "opportunity": _count("SELECT COUNT(DISTINCT lead_no) c FROM opportunities"),
        "quoted": _count(
            "SELECT COUNT(DISTINCT lead_no) c FROM quotes WHERE status!='draft'"),
        "ordered": _count(
            "SELECT COUNT(DISTINCT lead_no) c FROM orders WHERE status!='cancelled'"),
    }
    _due_c, _due_p = _due_clause(7)
    funnel["follow_up_due"] = _count(f"SELECT COUNT(*) c FROM leads l WHERE {_due_c}", _due_p)
    return Stats(total=total, by_country=by_country, by_channel_status=by_cs,
                 reach=reach, funnel=funnel)


import datetime as _dt

_INSERT_COLS = ["company_en", "company_local", "country", "region", "city",
                "email", "phone", "website", "instagram", "facebook", "linkedin",
                "business", "target_fit", "brief", "hook", "email_source"]


def next_no(conn) -> int:
    row = conn.execute("SELECT MAX(no) m FROM leads").fetchone()
    return (row["m"] or 0) + 1


def insert_lead(conn, data: dict) -> int:
    """Raises blocklist.BlockedLead when the domain is on the never-collect-again list —
    checked here rather than at each caller so a new import path cannot forget it."""
    from app import blocklist, countries
    from app.dedupe import normalize_website
    hit = blocklist.is_blocked(conn, data.get("website"), data.get("email"))
    if hit:
        raise blocklist.BlockedLead(hit)
    no = next_no(conn)
    cols = ["no"] + _INSERT_COLS + ["created_at", "updated_at"]
    now = _dt.datetime.now(_dt.UTC).isoformat()
    data = {**data, "website": normalize_website(data.get("website")),
            "country": countries.normalize(data.get("country"))}
    vals = [no] + [data.get(c) for c in _INSERT_COLS] + [now, now]
    placeholders = ",".join("?" * len(cols))
    conn.execute(f"INSERT INTO leads({','.join(cols)}) VALUES ({placeholders})", vals)
    conn.commit()
    from app import contacts
    contacts.migrate_lead(conn, no)
    return no
