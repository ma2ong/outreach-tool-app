"""Duplicate lead detection and merge.

Root cause of dupes: website was stored inconsistently ('https://www.x.com' vs
'x.com'), so equality-based duplicate checks missed them and the same company got
imported repeatedly. Fix is two-fold: normalize websites everywhere (storage +
lookup), and provide a safe merge that folds duplicates into the oldest lead —
filling its missing fields, repointing outreach/notes/logs, never losing a reply.
"""
import re

_SCHEME = re.compile(r"^https?://", re.I)


def normalize_website(url: str | None) -> str | None:
    if not url:
        return url
    w = _SCHEME.sub("", url.strip().lower())
    if w.startswith("www."):
        w = w[4:]
    return w.rstrip("/") or None


def normalize_all_websites(conn) -> int:
    """One-off, idempotent: bring every stored website to normalized form."""
    changed = 0
    for r in conn.execute("SELECT no, website FROM leads WHERE website IS NOT NULL AND website != ''"):
        norm = normalize_website(r["website"])
        if norm != r["website"]:
            conn.execute("UPDATE leads SET website=? WHERE no=?", (norm, r["no"]))
            changed += 1
    conn.commit()
    return changed


def find_duplicate_groups(conn) -> list[dict]:
    """Groups of lead nos that are the same company (same normalized website, or
    same company name when either side lacks a website). Keeper = lowest no."""
    rows = [dict(r) for r in conn.execute(
        "SELECT no, company_en, website FROM leads ORDER BY no")]
    by_key: dict[str, list[dict]] = {}
    for r in rows:
        site = normalize_website(r["website"])
        key = f"w:{site}" if site else f"c:{(r['company_en'] or '').strip().lower()}"
        by_key.setdefault(key, []).append(r)
    # second pass: leads without website whose company matches a with-website group
    name_of = {}
    for key, grp in by_key.items():
        if key.startswith("w:"):
            for g in grp:
                name_of.setdefault((g["company_en"] or "").strip().lower(), key)
    for key in [k for k in by_key if k.startswith("c:")]:
        target = name_of.get(key[2:])
        if target:
            by_key[target].extend(by_key.pop(key))
    groups = []
    for grp in by_key.values():
        if len(grp) > 1:
            nos = sorted(g["no"] for g in grp)
            groups.append({"keep": nos[0], "dups": nos[1:],
                           "company": grp[0]["company_en"], "website": grp[0]["website"]})
    return sorted(groups, key=lambda g: g["keep"])


_FILL_COLS = ["company_local", "country", "region", "city", "contact_name", "title",
              "email", "phone", "website", "instagram", "facebook", "linkedin",
              "business", "target_fit", "tags", "follow_up_date", "next_action", "email_status"]

_STATUS_RANK = {"replied": 3, "messaged": 2}


def merge_leads(conn, keep: int, dups: list[int]) -> None:
    from app.opportunities import ensure_schema as ensure_opportunity_schema
    from app.activities import ensure_schema as ensure_activity_schema
    from app.contacts import ensure_schema as ensure_contact_schema
    from app.sales_documents import ensure_schema as ensure_sales_document_schema
    ensure_opportunity_schema(conn)
    ensure_activity_schema(conn)
    ensure_contact_schema(conn)
    ensure_sales_document_schema(conn)
    keeper = conn.execute("SELECT * FROM leads WHERE no=?", (keep,)).fetchone()
    if keeper is None:
        return
    for d in dups:
        dup = conn.execute("SELECT * FROM leads WHERE no=?", (d,)).fetchone()
        if dup is None:
            continue
        # fill keeper's missing fields from the dup
        sets, params = [], []
        for col in _FILL_COLS:
            if (keeper[col] is None or keeper[col] == "") and dup[col] not in (None, ""):
                sets.append(f"{col}=?")
                params.append(dup[col])
        if sets:
            conn.execute(f"UPDATE leads SET {', '.join(sets)} WHERE no=?", [*params, keep])
            keeper = conn.execute("SELECT * FROM leads WHERE no=?", (keep,)).fetchone()
        # outreach: keep the strongest status per channel, never lose a reply
        for o in conn.execute("SELECT * FROM outreach WHERE lead_no=?", (d,)):
            cur = conn.execute("SELECT * FROM outreach WHERE lead_no=? AND channel=?",
                               (keep, o["channel"])).fetchone()
            if cur is None:
                conn.execute("UPDATE outreach SET lead_no=? WHERE id=?", (keep, o["id"]))
            else:
                if _STATUS_RANK.get(o["status"], 0) > _STATUS_RANK.get(cur["status"], 0):
                    conn.execute("UPDATE outreach SET status=? WHERE id=?", (o["status"], cur["id"]))
                conn.execute(
                    "UPDATE outreach SET touch_count=touch_count+?,"
                    " reply_received=MAX(reply_received,?) WHERE id=?",
                    (o["touch_count"] or 0, o["reply_received"] or 0, cur["id"]))
                conn.execute("DELETE FROM outreach WHERE id=?", (o["id"],))
        conn.execute("UPDATE notes SET lead_no=? WHERE lead_no=?", (keep, d))
        conn.execute("UPDATE send_log SET lead_no=? WHERE lead_no=?", (keep, d))
        conn.execute("UPDATE inbox_messages SET lead_no=? WHERE lead_no=?", (keep, d))
        conn.execute("UPDATE activities SET lead_no=? WHERE lead_no=?", (keep, d))
        from app import contacts
        contacts.merge_lead_contacts(conn, keep, d)
        # A duplicate company may already have real projects. Repoint them before
        # deleting the duplicate lead so ON DELETE CASCADE never loses pipeline value.
        conn.execute("UPDATE opportunities SET lead_no=? WHERE lead_no=?", (keep, d))
        conn.execute("UPDATE quotes SET lead_no=? WHERE lead_no=?", (keep, d))
        conn.execute("UPDATE orders SET lead_no=? WHERE lead_no=?", (keep, d))
        for e in conn.execute("SELECT id, sequence_id FROM sequence_enrollments WHERE lead_no=?", (d,)):
            dup_of_keep = conn.execute(
                "SELECT 1 FROM sequence_enrollments WHERE lead_no=? AND sequence_id=?",
                (keep, e["sequence_id"])).fetchone()
            if dup_of_keep:
                conn.execute("DELETE FROM sequence_enrollments WHERE id=?", (e["id"],))
            else:
                conn.execute("UPDATE sequence_enrollments SET lead_no=? WHERE id=?", (keep, e["id"]))
        conn.execute("DELETE FROM leads WHERE no=?", (d,))
    from app import activities
    activities.sync_lead(conn, keep)
    conn.commit()


def merge_all(conn) -> dict:
    normalize_all_websites(conn)  # merged rows must end up in canonical form
    groups = find_duplicate_groups(conn)
    for g in groups:
        merge_leads(conn, g["keep"], g["dups"])
    return {"groups": len(groups), "removed": sum(len(g["dups"]) for g in groups)}
