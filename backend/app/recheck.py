"""Re-reading a lead's own website some months after we messaged them.

A company we contacted in March and never heard back from is not a dead row. Their site
gets a new contact address, a projects page, a phone number that was not there before —
and none of that reaches us, because the only time we ever read the site was the day we
found them. This is the one mechanism that puts already-contacted leads back in play
without collecting anybody new.

Two decisions carried over from how a research agent paces itself:

**The interval is set by how good the fit is, and it is recorded with a reason.** A
rental company that scored 90 is worth looking at every month; a 40 is worth looking at
twice a year. Checking everything on the same clock spends the same effort on rows
nobody will ever sell to.

**A check that found nothing produces nothing.** No task, no note, no badge — just a
later date. A task list that reports non-events every quarter is a task list Allen stops
reading, which costs more than the check was ever worth.

On what a check may overwrite: an empty field gets filled, because there is nothing to
lose. A field that already has a different value is left alone and the new value goes in
the note instead — the site could have been redesigned, or the fetch could have grabbed
a partner's address off a footer, and quietly replacing a working email with that is the
one outcome worse than not checking at all.
"""
import datetime as dt
import re
import sqlite3

# Fit is stored as "AV集成商 (85)" — the same parenthesized score the leads table sorts on.
_FIT_RE = re.compile(r"\((\d+)\)\s*$")

# Base interval in days by fit score. A no-change check doubles it (capped), so a lead
# that has stayed identical through three checks settles at roughly a yearly look.
_BASE_INTERVAL = ((85, 30), (70, 90))
_DEFAULT_INTERVAL = 180
_MAX_INTERVAL = 365

# Fields a re-read may fill in when the record has nothing. Ordered for the note.
_FIELDS = ("email", "phone", "instagram", "facebook", "linkedin")
_LABELS = {"email": "邮箱", "phone": "电话", "instagram": "Instagram",
           "facebook": "Facebook", "linkedin": "LinkedIn"}


def _today() -> dt.date:
    return dt.date.today()


def fit_score(target_fit: str | None) -> int:
    m = _FIT_RE.search(target_fit or "")
    return int(m.group(1)) if m else 0


def interval_days(target_fit: str | None, recheck_count: int = 0) -> int:
    """How long until this lead is worth reading again, and why: a strong fit comes back
    round quickly, and each check that changed nothing pushes the next one further out."""
    base = _DEFAULT_INTERVAL
    for floor, days in _BASE_INTERVAL:
        if fit_score(target_fit) >= floor:
            base = days
            break
    return min(_MAX_INTERVAL, base * (2 ** max(0, recheck_count)))


def reason(target_fit: str | None, recheck_count: int = 0) -> str:
    days = interval_days(target_fit, recheck_count)
    if recheck_count:
        return f"连续 {recheck_count} 次复检官网没有变化，下次改为 {days} 天后"
    score = fit_score(target_fit)
    if score >= 85:
        return f"高分客户（{score}），官网换联系人或上新项目就值得再触达，{days} 天后复检"
    if score >= 70:
        return f"契合度 {score}，{days} 天后复检官网"
    return f"契合度偏低（{score}），{days} 天后复检一次就够"


def _set_due(conn: sqlite3.Connection, lead_no: int, days: int) -> str:
    due = (_today() + dt.timedelta(days=days)).isoformat()
    conn.execute("UPDATE leads SET recheck_due=? WHERE no=?", (due, lead_no))
    return due


def schedule_after_send(conn: sqlite3.Connection, lead_no: int) -> str | None:
    """Put a first re-read on the calendar when we message somebody. Never moves a date
    that is already set: a second touch does not make the site newer."""
    row = conn.execute(
        "SELECT target_fit, website, recheck_due FROM leads WHERE no=?", (lead_no,)
    ).fetchone()
    if row is None or not (row["website"] or "").strip() or row["recheck_due"]:
        return None
    due = _set_due(conn, lead_no, interval_days(row["target_fit"]))
    conn.commit()
    return due


def due_leads(conn: sqlite3.Connection, limit: int = 20) -> list[dict]:
    """Leads whose re-read has come round. Excludes anyone who replied (they are a
    conversation now, not a record to research), anyone marked do-not-contact, and
    anything already won or lost."""
    rows = conn.execute(
        "SELECT no, company_en, recheck_due FROM leads"
        " WHERE recheck_due IS NOT NULL AND recheck_due <= date('now')"
        "   AND COALESCE(website, '') != ''"
        "   AND COALESCE(do_not_contact, 0) = 0"
        "   AND (stage IS NULL OR stage NOT IN ('won', 'lost'))"
        "   AND no NOT IN (SELECT lead_no FROM outreach WHERE status='replied')"
        " ORDER BY recheck_due, no LIMIT ?",
        (max(1, limit),),
    ).fetchall()
    return [dict(r) for r in rows]


def _diff(lead: dict, info: dict) -> tuple[dict, list[str]]:
    """Split a fresh read into what we may write and what only a human should decide.

    Returns (fills, notes) — fills go straight onto the record because those fields were
    empty; notes describe everything else worth a look, including values that disagree
    with what we already have."""
    fills: dict = {}
    notes: list[str] = []
    for field in _FIELDS:
        fresh = (info.get(field) or "").strip()
        if not fresh:
            continue
        current = (lead.get(field) or "").strip()
        if not current:
            fills[field] = fresh
            notes.append(f"新增{_LABELS[field]}：{fresh}")
        elif fresh.lower() != current.lower():
            notes.append(f"{_LABELS[field]}官网上写的是 {fresh}，库里是 {current}（未自动改）")
    # Brief and hook are gated separately in app.brief and have to be stored separately
    # too. Writing the hook only alongside a brief silently dropped every site that
    # earned one without the other — which is exactly the single-keyword Korean case the
    # gloss table exists to serve.
    for field, label in (("brief", "简介"), ("hook", "开场白")):
        fresh = (info.get(field) or "").strip()
        had = (lead.get(field) or "").strip()
        # docs/100：带出处的开场白不被正则重建覆盖。09-04 真跑时看见 MW LED 的
        # 「Saw P2 panels listed on your site.」被换成了「Saw the events work on your
        # site.」—— 一句具体的换成一句类目的，是降级。docs/93 R5 已经在
        # `refresh_hooks` 上立过同一条规矩，这里是它漏掉的另一条写入路径。
        if field == "hook" and str(lead.get("hook_quote") or "").strip():
            continue
        if fresh and fresh != had:
            # Derived from the page rather than typed by anyone, so these are safe to
            # replace outright — they describe the site as it reads today.
            fills[field] = fresh
            notes.append(f"官网{label}有更新，已重写" if had else f"首次抓到官网内容，已写入{label}")
    return fills, notes


def _is_boilerplate(conn: sqlite3.Connection, lead_no: int, candidate: dict) -> bool:
    """True when this exact wording already came off a different company's site.

    Navigation and footer text describes how a website is built, not what a company is
    doing. The same sentence turning up under two domains is the tell (docs/58 R3).
    """
    headline = (candidate.get("headline") or "").strip()
    if not headline:
        return False
    return conn.execute(
        "SELECT 1 FROM buying_signals WHERE lower(headline)=lower(?) AND lead_no<>? LIMIT 1",
        (headline, lead_no)).fetchone() is not None


def _store_new_signals(conn: sqlite3.Connection, lead_no: int,
                       candidates: list[dict]) -> list[dict]:
    """Persist only genuinely new public evidence; repeated rechecks stay quiet."""
    if not candidates:
        return []
    from app import sales_intelligence

    sales_intelligence.ensure_schema(conn)
    candidates = [c for c in candidates if not _is_boilerplate(conn, lead_no, c)]
    known = {row["id"] for row in conn.execute(
        "SELECT id FROM buying_signals WHERE lead_no=?", (lead_no,)).fetchall()}
    added = []
    for candidate in candidates:
        try:
            signal = sales_intelligence.create_signal(conn, lead_no, candidate)
        except (sales_intelligence.SalesIntelligenceValidation, TypeError, ValueError):
            # One malformed detector candidate must not turn an otherwise successful
            # website reread into a failed recheck.
            continue
        if signal["id"] not in known:
            known.add(signal["id"])
            added.append(signal)
    return added


def run(conn: sqlite3.Connection, lead_no: int, enrich_fn=None,
        first_read: bool = False) -> dict:
    """Re-read one lead's site now. Returns what changed; {"changed": False} is a normal,
    successful outcome and deliberately leaves no trace beyond the next due date.

    `first_read` is for the backfill over leads collected before any of this existed.
    Everything it finds is new by definition, so raising "the website changed, worth
    another touch" on all of them would bury genuine current buying windows. Public
    buying signals are therefore only activated on later rechecks, not the historical
    first-read backfill."""
    from app import activities, hook_writer, repository as repo

    # 下面的 SELECT 要读 hook_quote，老库和测试库里这几列可能还没建。
    hook_writer.ensure_schema(conn)
    row = conn.execute(
        "SELECT no, company_en, country, website, target_fit, recheck_count,"
        "       email, phone, instagram, facebook, linkedin, brief, hook, hook_quote"
        " FROM leads WHERE no=?", (lead_no,)
    ).fetchone()
    if row is None:
        return {"ok": False, "error": "客户不存在"}
    lead = dict(row)
    website = (lead.get("website") or "").strip()
    if not website:
        return {"ok": False, "error": "没有官网，无法复检"}

    if enrich_fn is None:
        from app.enrich import enrich_domain
        enrich_fn = enrich_domain
    try:
        info = enrich_fn(website) or {}
    except Exception as exc:  # noqa: BLE001 — an unreachable site is not a lead problem
        # Try again on the normal cadence rather than retrying a dead host every sweep.
        _set_due(conn, lead_no, interval_days(lead["target_fit"], lead["recheck_count"] or 0))
        conn.commit()
        return {"ok": False, "error": str(exc)}

    # Nothing came back at all. That is a network outcome, not a fact about the company,
    # and recording it as "this site says nothing" would retire the lead from every
    # future pass over a page we never actually read.
    if info.get("pages") == 0:
        _set_due(conn, lead_no, interval_days(lead["target_fit"], lead["recheck_count"] or 0))
        conn.commit()
        return {"ok": False, "error": "官网一个页面都没抓到"}

    fills, notes = _diff(lead, info)
    new_signals = [] if first_read else _store_new_signals(
        conn, lead_no, info.get("buying_signals") or [])

    if fills:
        if "email" in fills and info.get("email_source"):
            fills["email_source"] = info["email_source"]
        sets = ", ".join(f"{k}=?" for k in fills)
        conn.execute(f"UPDATE leads SET {sets}, updated_at=? WHERE no=?",
                     [*fills.values(), dt.datetime.now(dt.UTC).isoformat(), lead_no])

    # docs/93 R6：官网重读的时候正文正好在手，顺路写一句引用得出的开场白。
    # 失败向下退，不向上抛 —— 没有更好的开场白不是一次失败的复检。
    from app import hook_writer

    better = hook_writer.improve(conn, {**lead, **fills}, info.get("text") or "", website)
    if better:
        notes.append(f"开场白改用官网原话：{better['hook']}")

    has_finding = bool(notes or new_signals)
    count = 0 if has_finding else (lead["recheck_count"] or 0) + 1
    conn.execute("UPDATE leads SET recheck_count=? WHERE no=?", (count, lead_no))
    due = _set_due(conn, lead_no, interval_days(lead["target_fit"], count))
    conn.commit()

    if not has_finding:
        return {"ok": True, "changed": False, "next_due": due}

    timeline = list(notes)
    if new_signals:
        timeline.append("发现采购信号：" + "；".join(s["headline"] for s in new_signals[:5]))
    repo.add_note(conn, lead_no, ("首次读取官网：" if first_read else "官网复检：")
                  + "；".join(timeline))

    if not first_read:
        from app import sales_intelligence
        if notes:
            sales_intelligence.record_site_change(
                conn, lead_no, website, notes, hook=info.get("hook"))
        activities.ensure_schema(conn)
        if new_signals:
            confidence = max(int(s.get("confidence") or 0) for s in new_signals)
            title = f"发现采购信号，可以跟进：{lead['company_en']}"
            priority = "high" if confidence >= 80 else "normal"
        else:
            title = f"官网有更新，可以再触达：{lead['company_en']}"
            priority = "normal"
        activities._upsert_source(
            conn, lead_no=lead_no, opportunity_id=None, source="recheck",
            source_ref=f"lead:{lead_no}:recheck", type="task",
            title=title, due_at=_today().isoformat(), priority=priority,
            note="；".join(timeline)[:500],
        )
        activities.sync_lead(conn, lead_no)
    return {"ok": True, "changed": True, "next_due": due,
            "filled": sorted(fills), "notes": notes,
            "signals": [{"id": s["id"], "headline": s["headline"],
                         "confidence": s["confidence"]} for s in new_signals]}


def sweep(conn: sqlite3.Connection, limit: int = 20, enrich_fn=None) -> dict:
    """Work through today's due leads. Capped per run: each lead is a live page fetch,
    and the same restraint that governs sending governs reading."""
    checked = changed = failed = 0
    for lead in due_leads(conn, limit):
        result = run(conn, lead["no"], enrich_fn=enrich_fn)
        checked += 1
        if not result.get("ok"):
            failed += 1
        elif result.get("changed"):
            changed += 1
    return {"checked": checked, "changed": changed, "failed": failed}
