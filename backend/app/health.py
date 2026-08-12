"""Lead-base health check: find data that is quietly costing money, then fix it.

Every issue here wastes something real — sending budget on peers, daily WhatsApp
quota on leads with no phone, or a stage board that lies about where deals stand.
Fixes are conservative: peers/directories are suppressed (do_not_contact), never
deleted, so a wrong call is one click to undo.
"""
from app import screening

ISSUES = ("peer", "directory", "no_contact", "junk_name", "stale_stage")

_JUNK_NAMES = ("contact", "contact us", "contact-us", "home", "about", "index",
               "page not found", "404")


def _rows(conn):
    return conn.execute(
        "SELECT no, company_en, country, website, email, phone, instagram, facebook, stage,"
        "       COALESCE(do_not_contact, 0) dnc FROM leads").fetchall()


def _is_junk_name(name: str | None) -> bool:
    n = (name or "").strip().lower()
    return len(n) < 3 or n in _JUNK_NAMES


def scan(conn) -> dict:
    """Group the lead base's problems, each with the leads it affects."""
    found: dict[str, list[dict]] = {k: [] for k in ISSUES}
    messaged = {r["lead_no"] for r in conn.execute(
        "SELECT DISTINCT lead_no FROM outreach WHERE status IN ('messaged','replied')")}
    for r in _rows(conn):
        lead = {"no": r["no"], "company_en": r["company_en"],
                "website": r["website"], "country": r["country"]}
        if not r["dnc"]:
            s = screening.screen({"domain": r["website"], "phone": r["phone"], "email": r["email"]})
            if s["excluded"]:
                key = "directory" if "目录" in (s["exclude_reason"] or "") else "peer"
                found[key].append(lead | {"reason": s["exclude_reason"]})
                continue
        if not any((r["email"], r["phone"], r["instagram"], r["facebook"])):
            found["no_contact"].append(lead)
        if _is_junk_name(r["company_en"]):
            found["junk_name"].append(lead)
        # Stage says "new" but we already messaged them — the board is lying.
        if r["no"] in messaged and (r["stage"] or "new") == "new":
            found["stale_stage"].append(lead)
    return {k: v for k, v in found.items() if v}


def cleanable(conn) -> list[dict]:
    """Leads that are pure dead weight — safe to delete without reading them one by one.

    Nothing to send to (no email/phone/IG/FB) AND nothing invested: never messaged, no
    note, no inbox message, no sales task, no opportunity. Anything with history stays, because a
    deleted lead cannot be undone and a wrong call there costs a real customer. Peers
    keep their own conservative fix (do_not_contact), so they are not in here even
    though Allen may well want them gone — those he picks by hand."""
    from app.opportunities import ensure_schema as ensure_opportunity_schema
    from app.activities import ensure_schema as ensure_activity_schema
    from app.contacts import ensure_schema as ensure_contact_schema
    from app.sales_documents import ensure_schema as ensure_sales_document_schema
    ensure_opportunity_schema(conn)
    ensure_activity_schema(conn)
    ensure_contact_schema(conn)
    ensure_sales_document_schema(conn)
    return [dict(r) for r in conn.execute("""
        SELECT no, company_en, website, country FROM leads l
         WHERE COALESCE(email,'')='' AND COALESCE(phone,'')=''
           AND COALESCE(instagram,'')='' AND COALESCE(facebook,'')=''
           AND NOT EXISTS (SELECT 1 FROM outreach o WHERE o.lead_no=l.no
                            AND o.status IN ('messaged','replied'))
           AND NOT EXISTS (SELECT 1 FROM notes n WHERE n.lead_no=l.no)
           AND NOT EXISTS (SELECT 1 FROM inbox_messages m WHERE m.lead_no=l.no)
           AND NOT EXISTS (SELECT 1 FROM activities a WHERE a.lead_no=l.no)
           AND NOT EXISTS (SELECT 1 FROM contacts c WHERE c.lead_no=l.no)
           AND NOT EXISTS (SELECT 1 FROM opportunities p WHERE p.lead_no=l.no)
           AND NOT EXISTS (SELECT 1 FROM quotes q WHERE q.lead_no=l.no)
           AND NOT EXISTS (SELECT 1 FROM orders ord WHERE ord.lead_no=l.no)
         ORDER BY no""")]


def fix(conn, issues: list[str]) -> dict:
    """Apply the safe fix for each requested issue. Returns what changed."""
    from app import repository
    found = scan(conn)
    done: dict[str, int] = {}
    for key in issues:
        leads = found.get(key, [])
        if key in ("peer", "directory"):
            for lead in leads:
                conn.execute("UPDATE leads SET do_not_contact=1 WHERE no=?", (lead["no"],))
                repository.add_note(conn, lead["no"],
                                    f"体检自动标记不再联系：{lead.get('reason', '同行/目录站')}")
            done[key] = len(leads)
        elif key == "stale_stage":
            for lead in leads:
                conn.execute("UPDATE leads SET stage='contacted' WHERE no=? AND stage='new'",
                             (lead["no"],))
            done[key] = len(leads)
        # no_contact / junk_name are reported only: deleting or renaming a lead is
        # Allen's call, not the tool's.
    conn.commit()
    return done
