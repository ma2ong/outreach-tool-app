"""Source-backed decision-maker research for accounts with real sales work.

The radar searches only public company-owned pages, stages named people in a candidate
pool, and promotes only strong evidence. It never guesses an email address and never
sets `decision_maker` merely because a title sounds senior; Opportunity Coach can use
the public title as coverage evidence without turning an inference into CRM truth.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import sqlite3
import urllib.parse

from app.agent import proposals


CANDIDATE_STATUSES = ("new", "promoted", "dismissed")
ROLE_KINDS = ("commercial", "project")
AUTO_PROMOTE_MIN = 90
MAX_SEARCH_PAGES = 4
MAX_SWEEP_ACCOUNTS = 2

SCHEMA = """
CREATE TABLE IF NOT EXISTS contact_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_no INTEGER NOT NULL,
    name TEXT NOT NULL,
    title TEXT NOT NULL,
    email TEXT,
    linkedin TEXT,
    role_kind TEXT NOT NULL,
    source_url TEXT NOT NULL,
    evidence TEXT NOT NULL,
    confidence INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    promoted_contact_id INTEGER,
    fingerprint TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(lead_no) REFERENCES leads(no) ON DELETE CASCADE,
    FOREIGN KEY(promoted_contact_id) REFERENCES contacts(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS decision_maker_scans (
    lead_no INTEGER PRIMARY KEY,
    scanned_at TEXT NOT NULL,
    pages_checked INTEGER NOT NULL DEFAULT 0,
    result_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    FOREIGN KEY(lead_no) REFERENCES leads(no) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_contact_candidates_lead
    ON contact_candidates(lead_no, status, confidence DESC);
CREATE INDEX IF NOT EXISTS idx_contact_candidates_status
    ON contact_candidates(status, confidence DESC);
"""


class DecisionMakerValidation(ValueError):
    pass


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def _today() -> dt.date:
    return dt.date.today()


def ensure_schema(conn: sqlite3.Connection) -> None:
    from app.contacts import ensure_schema as ensure_contacts
    ensure_contacts(conn)
    conn.executescript(SCHEMA)
    conn.commit()


def _domain(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if not re.match(r"^https?://", raw, re.I):
        raw = "https://" + raw
    return urllib.parse.urlparse(raw).netloc.lower().removeprefix("www.")


def _company_owned(source_url: str, website: str | None) -> bool:
    source = _domain(source_url)
    company = _domain(website)
    return bool(source and company and (source == company or source.endswith("." + company)))


def _fingerprint(lead_no: int, candidate: dict) -> str:
    raw = "|".join(str(v or "").strip().lower() for v in (
        lead_no, candidate.get("name"), candidate.get("title"), candidate.get("email"),
        candidate.get("linkedin"), candidate.get("source_url"), candidate.get("role_kind"),
    ))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _validate(candidate: dict) -> dict:
    clean = {
        "name": str(candidate.get("name") or "").strip()[:120],
        "title": str(candidate.get("title") or "").strip()[:160],
        "email": str(candidate.get("email") or "").strip().lower()[:240] or None,
        "linkedin": str(candidate.get("linkedin") or "").strip()[:800] or None,
        "role_kind": str(candidate.get("role_kind") or "").strip(),
        "source_url": str(candidate.get("source_url") or "").strip()[:1000],
        "evidence": str(candidate.get("evidence") or "").strip()[:1200],
    }
    if not clean["name"] or not clean["title"]:
        raise DecisionMakerValidation("联系人候选必须有公开姓名和职位")
    if clean["role_kind"] not in ROLE_KINDS:
        raise DecisionMakerValidation("未知联系人候选角色")
    if not re.match(r"^https?://[^\s]+$", clean["source_url"], re.I):
        raise DecisionMakerValidation("联系人候选必须有公开来源 URL")
    if not clean["evidence"]:
        raise DecisionMakerValidation("联系人候选必须保留来源证据")
    try:
        clean["confidence"] = int(candidate.get("confidence") or 0)
    except (TypeError, ValueError) as exc:
        raise DecisionMakerValidation("联系人候选可信度必须是整数") from exc
    if not 1 <= clean["confidence"] <= 100:
        raise DecisionMakerValidation("联系人候选可信度必须是 1-100")
    if clean["email"] and "@" not in clean["email"]:
        raise DecisionMakerValidation("联系人候选邮箱格式不正确")
    if clean["linkedin"] and "linkedin.com/in/" not in clean["linkedin"].lower():
        # A company LinkedIn page is not proof of a named person's identity.
        clean["linkedin"] = None
    return clean


def _row(row) -> dict | None:
    return dict(row) if row else None


def get_candidate(conn: sqlite3.Connection, candidate_id: int) -> dict | None:
    ensure_schema(conn)
    row = conn.execute(
        "SELECT c.*, l.company_en, l.country, l.website FROM contact_candidates c"
        " JOIN leads l ON l.no=c.lead_no WHERE c.id=?", (candidate_id,)
    ).fetchone()
    return _row(row)


def list_candidates(conn: sqlite3.Connection, *, lead_no: int | None = None,
                    status: str | None = "new", limit: int = 200) -> list[dict]:
    ensure_schema(conn)
    where, params = [], []
    if lead_no is not None:
        where.append("c.lead_no=?")
        params.append(lead_no)
    if status:
        if status not in CANDIDATE_STATUSES:
            raise DecisionMakerValidation("未知联系人候选状态")
        where.append("c.status=?")
        params.append(status)
    sql = (
        "SELECT c.*, l.company_en, l.country, l.website FROM contact_candidates c"
        " JOIN leads l ON l.no=c.lead_no"
    )
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY c.confidence DESC, c.id DESC LIMIT ?"
    params.append(max(1, min(int(limit), 1000)))
    return [dict(r) for r in conn.execute(sql, params)]


def _existing_contact(conn, candidate: dict) -> dict | None:
    from app import contacts
    if candidate.get("email"):
        found = contacts.find_email(conn, candidate["email"], lead_no=candidate["lead_no"])
        if found:
            return found
    if candidate.get("linkedin"):
        row = conn.execute(
            "SELECT * FROM contacts WHERE lead_no=? AND lower(COALESCE(linkedin,''))=lower(?) LIMIT 1",
            (candidate["lead_no"], candidate["linkedin"]),
        ).fetchone()
        if row:
            return dict(row)
    row = conn.execute(
        "SELECT * FROM contacts WHERE lead_no=? AND lower(COALESCE(name,''))=lower(?)"
        " AND lower(COALESCE(title,''))=lower(?) LIMIT 1",
        (candidate["lead_no"], candidate["name"], candidate["title"]),
    ).fetchone()
    return dict(row) if row else None


def _mark_promoted(conn, candidate_id: int, contact_id: int) -> dict:
    conn.execute(
        "UPDATE contact_candidates SET status='promoted', promoted_contact_id=?, updated_at=? WHERE id=?",
        (contact_id, _now(), candidate_id),
    )
    conn.commit()
    return get_candidate(conn, candidate_id)


def promote_candidate(conn: sqlite3.Connection, candidate_id: int, *, manual: bool = False) -> dict:
    """Promote a candidate into contacts without asserting an inferred CRM role.

    Automatic promotion requires company-owned evidence, a direct public channel and a
    high confidence score. A project/technical person is auto-added only when the
    company already has a contact, so an engineer cannot silently become the default
    sales recipient. Manual promotion is the user's explicit override.
    """
    from app import contacts

    candidate = get_candidate(conn, candidate_id)
    if candidate is None:
        raise DecisionMakerValidation("联系人候选不存在")
    if candidate["status"] == "promoted" and candidate.get("promoted_contact_id"):
        return candidate
    existing = _existing_contact(conn, candidate)
    if existing:
        return _mark_promoted(conn, candidate_id, existing["id"])

    if not manual:
        if candidate["confidence"] < AUTO_PROMOTE_MIN:
            raise DecisionMakerValidation("候选证据还不够强，保留给人工确认")
        if not _company_owned(candidate["source_url"], candidate.get("website")):
            raise DecisionMakerValidation("自动晋级只接受客户自有官网证据")
        if not (candidate.get("email") or candidate.get("linkedin")):
            raise DecisionMakerValidation("自动晋级需要公开公司邮箱或个人 LinkedIn")
        any_contact = conn.execute(
            "SELECT 1 FROM contacts WHERE lead_no=? LIMIT 1", (candidate["lead_no"],)
        ).fetchone() is not None
        if candidate["role_kind"] == "project" and not any_contact:
            raise DecisionMakerValidation("技术/项目候选不会自动成为第一主要联系人")

    note = (
        f"Decision Maker Radar：公开官网候选，可信度 {candidate['confidence']}/100；"
        f"来源 {candidate['source_url']}；角色仅由职位推断，未自动标记 decision_maker。"
    )[:1000]
    contact = contacts.create(
        conn, candidate["lead_no"], {
            "name": candidate["name"], "title": candidate["title"],
            "email": candidate.get("email"), "linkedin": candidate.get("linkedin"),
            "role": "other", "note": note,
        },
        is_primary=False,
        source="agent.public-site",
    )
    return _mark_promoted(conn, candidate_id, contact["id"])


def dismiss_candidate(conn: sqlite3.Connection, candidate_id: int) -> dict:
    candidate = get_candidate(conn, candidate_id)
    if candidate is None:
        raise DecisionMakerValidation("联系人候选不存在")
    conn.execute(
        "UPDATE contact_candidates SET status='dismissed', updated_at=? WHERE id=?",
        (_now(), candidate_id),
    )
    conn.commit()
    return get_candidate(conn, candidate_id)


def persist_candidates(conn: sqlite3.Connection, lead_no: int, candidates: list[dict],
                       *, auto_promote: bool = True) -> dict:
    ensure_schema(conn)
    lead = conn.execute("SELECT no, website FROM leads WHERE no=?", (lead_no,)).fetchone()
    if lead is None:
        raise DecisionMakerValidation("客户不存在")
    created, promoted, ids = 0, 0, []
    for raw in candidates or []:
        try:
            clean = _validate(raw)
        except DecisionMakerValidation:
            continue
        fp = _fingerprint(lead_no, clean)
        existing = conn.execute(
            "SELECT id FROM contact_candidates WHERE fingerprint=?", (fp,)
        ).fetchone()
        if existing:
            candidate_id = existing["id"]
        else:
            now = _now()
            cur = conn.execute(
                "INSERT INTO contact_candidates(lead_no,name,title,email,linkedin,role_kind,"
                " source_url,evidence,confidence,status,fingerprint,created_at,updated_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,'new',?,?,?)",
                (lead_no, clean["name"], clean["title"], clean["email"], clean["linkedin"],
                 clean["role_kind"], clean["source_url"], clean["evidence"], clean["confidence"],
                 fp, now, now),
            )
            conn.commit()
            candidate_id = cur.lastrowid
            created += 1
        ids.append(candidate_id)
        if auto_promote:
            try:
                before = get_candidate(conn, candidate_id)
                after = promote_candidate(conn, candidate_id, manual=False)
                if before and before["status"] != "promoted" and after["status"] == "promoted":
                    promoted += 1
            except DecisionMakerValidation:
                pass
    return {"created": created, "promoted": promoted, "ids": ids}


def _queries(company: str, domain: str, role_kinds: set[str]) -> list[str]:
    queries = []
    if "commercial" in role_kinds:
        queries.append(
            f'site:{domain} "{company}" procurement purchasing buyer owner founder president management'
        )
    if "project" in role_kinds:
        queries.append(
            f'site:{domain} "{company}" "project manager" "technical director" "AV manager" engineer team'
        )
    return queries


def _missing_role_kinds(conn: sqlite3.Connection, lead_no: int) -> set[str]:
    from app import opportunities
    from app.agent import opportunity_coach

    missing: set[str] = set()
    open_opps = [opp for opp in opportunities.list_all(conn, lead_no=lead_no)
                 if opp["stage"] in opportunities.OPEN_STAGES]
    if not open_opps:
        coverage = opportunity_coach.contact_coverage(conn, lead_no, {})
        if not coverage["commercial_authority"]:
            missing.add("commercial")
        if not coverage["project_authority"]:
            missing.add("project")
        return missing
    for opp in open_opps:
        coverage = opportunity_coach.contact_coverage(conn, lead_no, opp)
        if not coverage["commercial_authority"]:
            missing.add("commercial")
        if not coverage["project_authority"]:
            missing.add("project")
    return missing


def scan(conn: sqlite3.Connection, lead_no: int, *, role_kinds: set[str] | None = None,
         search_fn=None, fetch_fn=None, max_pages: int = MAX_SEARCH_PAGES) -> dict:
    """Search and read a bounded set of company-owned public pages for named people."""
    from app import search
    from app.jina import fetch as jina_fetch
    from app.people_detector import detect_pages

    ensure_schema(conn)
    lead = conn.execute(
        "SELECT no, company_en, website, do_not_contact FROM leads WHERE no=?", (lead_no,)
    ).fetchone()
    if lead is None:
        raise DecisionMakerValidation("客户不存在")
    if lead["do_not_contact"]:
        raise DecisionMakerValidation("客户已标记不再联系，不继续做联系人研究")
    domain = _domain(lead["website"])
    if not domain:
        raise DecisionMakerValidation("客户没有官网，无法做来源可验证的联系人研究")
    wanted = set(role_kinds or _missing_role_kinds(conn, lead_no)) & set(ROLE_KINDS)
    if not wanted:
        return {"lead_no": lead_no, "searched": False, "reason": "关键角色已经覆盖",
                "pages_checked": 0, "created": 0, "promoted": 0, "candidates": []}

    search_fn = search_fn or (lambda q, lim: search.search_urls(
        q, limit=lim, allowed_domain=domain))
    fetch_fn = fetch_fn or jina_fetch
    urls: list[str] = []
    for query in _queries(lead["company_en"], domain, wanted):
        try:
            found = search_fn(query, max_pages) or []
        except Exception:
            found = []
        for url in found:
            if url not in urls and _company_owned(url, lead["website"]):
                urls.append(url)
            if len(urls) >= max(1, min(int(max_pages), MAX_SEARCH_PAGES)):
                break
        if len(urls) >= max_pages:
            break

    pages, errors = [], []
    for url in urls[:max_pages]:
        try:
            text = fetch_fn(url) or ""
        except Exception as exc:  # noqa: BLE001 — one page failure must not sink the account
            errors.append(f"{url}: {exc}")
            continue
        if text:
            pages.append({"url": url, "text": text})
    candidates = [row for row in detect_pages(pages, company_domain=domain)
                  if row["role_kind"] in wanted]
    persisted = persist_candidates(conn, lead_no, candidates, auto_promote=True)
    error_text = "; ".join(errors)[:1000] or None
    conn.execute(
        "INSERT INTO decision_maker_scans(lead_no,scanned_at,pages_checked,result_count,last_error)"
        " VALUES (?,?,?,?,?) ON CONFLICT(lead_no) DO UPDATE SET"
        " scanned_at=excluded.scanned_at,pages_checked=excluded.pages_checked,"
        " result_count=excluded.result_count,last_error=excluded.last_error",
        (lead_no, _now(), len(pages), len(candidates), error_text),
    )
    conn.commit()
    return {
        "lead_no": lead_no, "searched": True, "roles": sorted(wanted),
        "pages_checked": len(pages), "created": persisted["created"],
        "promoted": persisted["promoted"], "errors": errors,
        "candidates": list_candidates(conn, lead_no=lead_no, status="new", limit=20),
    }


def _scan_due(last_scanned: str | None, days: int, today: dt.date) -> bool:
    if not last_scanned:
        return True
    try:
        previous = dt.date.fromisoformat(str(last_scanned)[:10])
    except ValueError:
        return True
    return (today - previous).days >= days


def due_accounts(conn: sqlite3.Connection, *, today: dt.date | None = None,
                 limit: int = MAX_SWEEP_ACCOUNTS) -> list[dict]:
    """High-value open opportunities missing authority, with a bounded research cadence."""
    from app.agent import opportunity_coach

    ensure_schema(conn)
    today = today or _today()
    out, seen = [], set()
    for row in opportunity_coach.portfolio(conn, today=today, limit=50):
        lead_no = row["lead_no"]
        if lead_no in seen or not row["contact_coverage"]["missing"]:
            continue
        seen.add(lead_no)
        lead = conn.execute(
            "SELECT website, do_not_contact FROM leads WHERE no=?", (lead_no,)
        ).fetchone()
        if not lead or lead["do_not_contact"] or not _domain(lead["website"]):
            continue
        scan_row = conn.execute(
            "SELECT scanned_at FROM decision_maker_scans WHERE lead_no=?", (lead_no,)
        ).fetchone()
        cadence = 14 if row["stage"] in ("quoted", "negotiation") or row["severity"] in ("critical", "high") else 30
        if not _scan_due(scan_row["scanned_at"] if scan_row else None, cadence, today):
            continue
        out.append({
            "lead_no": lead_no, "company_en": row["company_en"], "stage": row["stage"],
            "severity": row["severity"], "urgency": row["urgency"],
            "missing_roles": [item["kind"] for item in row["contact_coverage"]["missing"]],
        })
        if len(out) >= max(1, min(int(limit), MAX_SWEEP_ACCOUNTS)):
            break
    return out


def _candidate_digest(rows: list[dict]) -> str:
    raw = json.dumps([
        {"id": row["id"], "name": row["name"], "title": row["title"], "confidence": row["confidence"]}
        for row in rows[:5]
    ], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def sweep(conn: sqlite3.Connection, *, today: dt.date | None = None,
          limit: int = MAX_SWEEP_ACCOUNTS, search_fn=None, fetch_fn=None) -> dict:
    """Research a tiny number of authority gaps and surface review work as proposals."""
    today = today or _today()
    checked, promoted, proposal_ids, results = 0, 0, [], []
    for account in due_accounts(conn, today=today, limit=limit):
        result = scan(
            conn, account["lead_no"], role_kinds=set(account["missing_roles"]),
            search_fn=search_fn, fetch_fn=fetch_fn,
        )
        checked += 1
        promoted += result.get("promoted", 0)
        results.append(result)
        candidates = result.get("candidates") or []
        if candidates:
            summary = "；".join(
                f"{c['name']} / {c['title']}（{c['confidence']}/100）" for c in candidates[:3]
            )
            proposal = proposals.create(
                conn, "create_task", lead_no=account["lead_no"],
                title=f"审核关键联系人候选：{account['company_en']}"[:200],
                reasoning=(f"Decision Maker Radar 找到公开官网候选，但证据未达到安全自动晋级条件。{summary}")[:600],
                evidence=[{"claim": "公开联系人候选", "source": c["source_url"]}
                          for c in candidates[:3]],
                payload={
                    "title": f"审核关键联系人候选：{account['company_en']}"[:200],
                    "type": "task", "due_at": today.isoformat(), "priority": "high",
                    "note": summary[:500],
                },
                risk="low",
                dedupe_key=f"decision-maker-{account['lead_no']}-{_candidate_digest(candidates)}",
            )
            if proposal:
                proposal_ids.append(proposal["id"])
    return {"checked": checked, "promoted": promoted, "proposed": len(proposal_ids),
            "proposal_ids": proposal_ids, "results": results}
