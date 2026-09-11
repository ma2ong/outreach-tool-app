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


# Hosts many unrelated companies share; a match on one says nothing (docs/129 R1).
_SHARED_HOSTS = {"blog.naver.com", "m.blog.naver.com", "sites.google.com", "linktr.ee",
                 "instagram.com", "facebook.com", "linkedin.com", "youtube.com", "wix.com",
                 "wordpress.com", "cafe24.com", "modoo.at", "imweb.me", "pf.kakao.com"}
# Facebook path pieces the quick-add parser used to mistake for a handle.
_NOT_A_HANDLE = {"people", "pg", "profile.php", "pages", "groups"}
_LEGAL_FORM = re.compile(r"\(주\)|㈜|주식회사|\(유\)|유한회사|co\.?,?\s*ltd\.?|pte\.?\s*ltd\.?|inc\.?"
                         r"|llc|corp(?:oration)?\.?|company|limited|ltd\.?|\bthe\b", re.I)


def _site_host(url: str | None) -> str:
    return (normalize_website(url) or "").split("/")[0]


def company_key(name: str | None) -> str:
    """(주)에스엔테크, 에스엔테크 and 'S&N Tech Co., Ltd' → one spelling each side of a compare."""
    cleaned = _LEGAL_FORM.sub("", (name or "").lower())
    return re.sub(r"[^a-z0-9가-힣]", "", cleaned)


def _union(parent: dict, a: int, b: int) -> None:
    ra, rb = _root(parent, a), _root(parent, b)
    if ra != rb:
        parent[max(ra, rb)] = min(ra, rb)


def _root(parent: dict, x: int) -> int:
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def _evidence(conn) -> tuple[list[dict], dict[tuple, list[int]]]:
    """Every lead, and every key two leads could share: contact email, website host,
    company name, social handle, phone."""
    from app.contacts import ensure_schema
    ensure_schema(conn)
    leads = [dict(r) for r in conn.execute(
        "SELECT no, company_en, company_local, country, website, email, phone, instagram,"
        " facebook FROM leads ORDER BY no")]
    emails: dict[int, set[str]] = {}
    for r in conn.execute("SELECT lead_no, lower(email) AS e FROM contacts"
                          " WHERE email IS NOT NULL AND email != ''"):
        emails.setdefault(r["lead_no"], set()).add(r["e"])
    for lead in leads:
        if lead["email"]:
            emails.setdefault(lead["no"], set()).add(lead["email"].lower())
    keyed: dict[tuple, list[int]] = {}
    # A lead with no country yet matches any country; two leads that name different
    # countries are two companies until someone says otherwise.
    countries = sorted({(lead["country"] or "").strip() for lead in leads} - {""})
    for lead in leads:
        no, country = lead["no"], (lead["country"] or "").strip()
        scopes = [country] if country else countries
        for address in emails.get(no, ()):
            keyed.setdefault(("email", address), []).append(no)
        host = _site_host(lead["website"])
        if host and host not in _SHARED_HOSTS:
            for scope in scopes:
                keyed.setdefault(("site", host, scope), []).append(no)
            keyed.setdefault(("site-any", host), []).append(no)
        for field in ("company_en", "company_local"):
            key = company_key(lead[field])
            if len(key) >= (3 if re.search(r"[가-힣]", key) else 4):
                # A name alone is not enough to guess a country: Trans-Lux (USA) and
                # Translux (UK, country still blank) are two makers.
                if country:
                    keyed.setdefault(("name", key, country), []).append(no)
                keyed.setdefault(("name-any", key), []).append(no)
        for field in ("instagram", "facebook"):
            handle = (lead[field] or "").strip().lower()
            if handle and handle not in _NOT_A_HANDLE:
                for scope in scopes:
                    keyed.setdefault((field, handle, scope), []).append(no)
        digits = re.sub(r"\D", "", lead["phone"] or "")
        if len(digits) >= 9:
            keyed.setdefault(("phone", digits[-9:]), []).append(no)
            # A record that has only a number cannot be a second brand on the same line.
            if not host:
                for scope in scopes:
                    keyed.setdefault(("phone-stub", digits[-9:], scope), []).append(no)
    # phone-stub only counts when the stub meets a lead in its country that also carries
    # that number.
    country_of = {lead["no"]: (lead["country"] or "").strip() for lead in leads}
    for key in [k for k in keyed if k[0] == "phone-stub"]:
        full = [n for n in keyed.get(("phone", key[1]), []) if country_of[n] in (key[2], "")]
        keyed[key] = sorted(set(keyed[key]) | set(full)) if len(full) > 1 else []
    return leads, keyed


def _groups(leads: list[dict], keyed: dict, kinds: tuple[str, ...]) -> list[dict]:
    parent = {lead["no"]: lead["no"] for lead in leads}
    why: dict[int, set[str]] = {}
    for (kind, *rest), nos in keyed.items():
        if kind not in kinds or len(set(nos)) < 2:
            continue
        nos = sorted(set(nos))
        for other in nos[1:]:
            _union(parent, nos[0], other)
        for no in nos:
            why.setdefault(no, set()).add(f"{kind}={rest[0]}")
    members: dict[int, list[dict]] = {}
    for lead in leads:
        members.setdefault(_root(parent, lead["no"]), []).append(lead)
    groups = []
    for grp in members.values():
        if len(grp) > 1:
            nos = sorted(g["no"] for g in grp)
            groups.append({"keep": nos[0], "dups": nos[1:],
                           "company": grp[0]["company_en"], "website": grp[0]["website"],
                           "why": sorted(set().union(*(why.get(n, set()) for n in nos)))})
    return sorted(groups, key=lambda g: g["keep"])


def find_duplicate_groups(conn) -> list[dict]:
    """Groups of lead nos that are the same company — a shared contact email, the same
    website host in the same country, the same company name in the same country, or the
    same Instagram/Facebook account (docs/129 R1). Keeper = lowest no."""
    leads, keyed = _evidence(conn)
    return _groups(leads, keyed, ("email", "site", "name", "instagram", "facebook", "phone-stub"))


def find_possible_duplicates(conn) -> list[dict]:
    """Pairs that share only a phone number, or a name or host across countries — one
    owner with two brands, or a franchise. Someone decides these; the merge does not."""
    leads, keyed = _evidence(conn)
    sure = {no for g in find_duplicate_groups(conn) for no in (g["keep"], *g["dups"])}
    weak = _groups(leads, keyed, ("phone", "site-any", "name-any"))
    return [g for g in weak if not {g["keep"], *g["dups"]} <= sure]


# What survives a merge. brief/hook/email_source were missing: two records of the same
# Korean company had all the researched copy on the row being deleted and none on the
# row being kept, so merging them threw away the only sentence we could open with.
_FILL_COLS = ["company_local", "country", "region", "city", "contact_name", "title",
              "email", "phone", "website", "instagram", "facebook", "linkedin",
              "business", "target_fit", "tags", "follow_up_date", "next_action",
              "email_status", "brief", "hook", "email_source", "recheck_due",
              "whatsapp_status"]

# Stage is not a blank to fill — both rows have one, and the merged company is as far
# along as the further of the two. Losing "contacted" would make an already-worked
# customer look untouched and get it opened with a cold letter.
_STAGE_RANK = ["new", "contacted", "replied", "qualified", "quoted", "won", "lost"]

_STATUS_RANK = {"replied": 3, "messaged": 2}


def merge_leads(conn, keep: int, dups: list[int]) -> None:
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
        if dup["stage"] in _STAGE_RANK and keeper["stage"] in _STAGE_RANK and (
                _STAGE_RANK.index(dup["stage"]) > _STAGE_RANK.index(keeper["stage"])):
            sets.append("stage=?")
            params.append(dup["stage"])
        # 0 is not a blank: a company one row says not to write to stays that way (docs/129 R3).
        for flag in ("do_not_contact", "no_cold_outreach"):
            if dup[flag] and not keeper[flag]:
                sets.append(f"{flag}=1")
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
        # The relationship timeline and what the Agent remembers are the two places a
        # merge used to silently drop history on the floor.
        for table in ("relationship_events", "lead_memory_items"):
            try:
                conn.execute(f"UPDATE {table} SET lead_no=? WHERE lead_no=?", (keep, d))
            except Exception:  # noqa: BLE001 — an older database may not have it yet
                pass
        from app import sales_intelligence
        sales_intelligence.merge_lead_signals(conn, keep, d)
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
