"""The approval spine: everything the agent wants to do becomes a proposal first.

Spec 22 section 2 — the agent proposes, Allen decides. Autonomy is a per-kind dial
(off / propose / auto) that ships at `propose` for every kind, so a new capability can
never start out acting on its own. Turning one grid square to `auto` leaves the rest
untouched, and an `auto` execution still writes its record, so nothing the agent does
is invisible after the fact.

Executors deliberately call the existing modules rather than reimplementing a send or
an update. That is what keeps the batch cap, the daily quota, the do-not-contact
exclusion and the invalid-address skip in force for agent-initiated work — those
guards cannot be bypassed here because there is no second path to bypass them with.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sqlite3

from app import settings

KINDS = (
    "reply_draft", "send_outreach", "create_task", "enroll_sequence",
    "stop_sequence", "discover_run", "build_opportunity", "mark_do_not_contact",
)
AUTONOMY = ("off", "propose", "auto")
RISKS = ("low", "medium", "high")
OPEN_STATUSES = ("pending",)
# Approved but not finished — i.e. running right now. Kept in the pending
# list so three minutes of work is not three minutes of blank screen.
APPROVED_STATUSES = ("approved", "edited_approved")
EXPIRE_DAYS = 7

_K_AUTONOMY = "agent_autonomy_%s"

SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    lead_no INTEGER,
    contact_id INTEGER,
    opportunity_id INTEGER,
    inbox_message_id INTEGER,
    title TEXT NOT NULL,
    reasoning TEXT,
    evidence TEXT,
    payload TEXT,
    original_payload TEXT,
    risk TEXT NOT NULL DEFAULT 'medium',
    status TEXT NOT NULL DEFAULT 'pending',
    decided_at TEXT,
    decided_note TEXT,
    reject_reason TEXT,
    executed_at TEXT,
    execution_result TEXT,
    backend TEXT,
    fingerprint TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lead_memory (
    lead_no INTEGER PRIMARY KEY,
    summary TEXT NOT NULL,
    source_count INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_proposals_status ON agent_proposals(status, created_at);
CREATE INDEX IF NOT EXISTS idx_proposals_lead ON agent_proposals(lead_no);
CREATE INDEX IF NOT EXISTS idx_proposals_msg ON agent_proposals(inbox_message_id);
"""

# Rejection reasons are a fixed list, not free text: phase C's only training signal is
# why Allen said no, and "not good" cannot be counted.
REJECT_REASONS = {
    "wrong_intent": "意图判断错了",
    "bad_content": "内容写得不对",
    "wrong_timing": "时机不对",
    "not_worth_it": "这个客户不值得跟",
    "handled_myself": "我自己处理了",
    "other": "其他",
}


class ProposalError(ValueError):
    pass


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


# ---------------------------------------------------------------- autonomy dial

def autonomy(conn, kind: str) -> str:
    return settings.get(conn, _K_AUTONOMY % kind, "propose")


def set_autonomy(conn, kind: str, level: str) -> None:
    if kind not in KINDS:
        raise ProposalError(f"未知动作类型 {kind}")
    if level not in AUTONOMY:
        raise ProposalError(f"未知自主度 {level}")
    settings.set_value(conn, _K_AUTONOMY % kind, level)


def autonomy_map(conn) -> dict:
    return {kind: autonomy(conn, kind) for kind in KINDS}


# ---------------------------------------------------------------- create / read

def _fingerprint(kind: str, lead_no, inbox_message_id, key: str) -> str:
    raw = f"{kind}|{lead_no}|{inbox_message_id}|{key}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _row(r) -> dict:
    d = dict(r)
    for field in ("evidence", "payload", "original_payload"):
        try:
            d[field] = json.loads(d[field]) if d.get(field) else None
        except (TypeError, json.JSONDecodeError):
            d[field] = None
    return d


def get(conn, proposal_id: int) -> dict | None:
    r = conn.execute("SELECT * FROM agent_proposals WHERE id=?", (proposal_id,)).fetchone()
    return _row(r) if r else None


def create(conn, kind: str, *, title: str, payload: dict, lead_no: int | None = None,
           reasoning: str = "", evidence: list | None = None, risk: str = "medium",
           contact_id: int | None = None, opportunity_id: int | None = None,
           inbox_message_id: int | None = None, backend: str = "",
           dedupe_key: str = "") -> dict | None:
    """Record one proposal. Returns None when this kind is switched off or when the
    same thing was already proposed — a duplicate draft for a reply Allen already saw
    is noise, not a second opinion."""
    ensure_schema(conn)
    if kind not in KINDS:
        raise ProposalError(f"未知动作类型 {kind}")
    if risk not in RISKS:
        raise ProposalError(f"未知风险级 {risk}")
    level = autonomy(conn, kind)
    if level == "off":
        return None
    fp = _fingerprint(kind, lead_no, inbox_message_id, dedupe_key or title)
    if conn.execute("SELECT 1 FROM agent_proposals WHERE fingerprint=?", (fp,)).fetchone():
        return None
    now = _now()
    cur = conn.execute(
        "INSERT INTO agent_proposals(kind, lead_no, contact_id, opportunity_id,"
        " inbox_message_id, title, reasoning, evidence, payload, risk, status,"
        " backend, fingerprint, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,'pending',?,?,?,?)",
        (kind, lead_no, contact_id, opportunity_id, inbox_message_id, title, reasoning,
         json.dumps(evidence or [], ensure_ascii=False),
         json.dumps(payload or {}, ensure_ascii=False), risk, backend, fp, now, now))
    conn.commit()
    proposal = get(conn, cur.lastrowid)
    if level == "auto":
        # Still recorded, still auditable — 'auto' skips the asking, not the writing down.
        return _execute(conn, proposal, note="自主执行")
    return proposal


def list_proposals(conn, status: str | None = "pending", lead_no: int | None = None,
                   kind: str | None = None, limit: int = 200) -> list[dict]:
    ensure_schema(conn)
    sql = ("SELECT p.*, l.company_en, l.country FROM agent_proposals p"
           " LEFT JOIN leads l ON l.no = p.lead_no WHERE 1=1")
    params: list = []
    if status == "pending":
        sql += " AND p.status IN (?,?,?)"
        params.extend(["pending", *APPROVED_STATUSES])
    elif status:
        sql += " AND p.status = ?"
        params.append(status)
    if lead_no is not None:
        sql += " AND p.lead_no = ?"
        params.append(lead_no)
    if kind:
        sql += " AND p.kind = ?"
        params.append(kind)
    # High risk first so the decisions that matter are not buried under routine ones.
    sql += (" ORDER BY CASE p.risk WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,"
            " p.created_at DESC LIMIT ?")
    params.append(limit)
    return [_row(r) for r in conn.execute(sql, params)]


def summary(conn) -> dict:
    ensure_schema(conn)
    rows = conn.execute(
        "SELECT status, COUNT(*) c FROM agent_proposals GROUP BY status").fetchall()
    by_status = {r["status"]: r["c"] for r in rows}
    risk = conn.execute(
        "SELECT risk, COUNT(*) c FROM agent_proposals WHERE status='pending' GROUP BY risk"
    ).fetchall()
    return {
        "pending": by_status.get("pending", 0),
        "by_status": by_status,
        "pending_by_risk": {r["risk"]: r["c"] for r in risk},
        "autonomy": autonomy_map(conn),
    }


def expire_stale(conn, days: int = EXPIRE_DAYS) -> int:
    """A reply that has waited a week is no longer worth sending. Letting it rot in the
    queue is worse than retiring it — Allen would eventually approve a stale answer."""
    ensure_schema(conn)
    cutoff = (dt.datetime.now(dt.UTC) - dt.timedelta(days=days)).isoformat()
    cur = conn.execute(
        "UPDATE agent_proposals SET status='expired', updated_at=?"
        " WHERE status='pending' AND created_at < ?", (_now(), cutoff))
    conn.commit()
    return cur.rowcount


# ---------------------------------------------------------------- decide

def reject(conn, proposal_id: int, reason: str, note: str = "") -> dict:
    if reason not in REJECT_REASONS:
        raise ProposalError(f"驳回理由必须从 {list(REJECT_REASONS)} 里选")
    p = get(conn, proposal_id)
    if not p:
        raise ProposalError("提议不存在")
    if p["status"] != "pending":
        raise ProposalError(f"提议已是 {p['status']}，不能再驳回")
    conn.execute(
        "UPDATE agent_proposals SET status='rejected', reject_reason=?, decided_note=?,"
        " decided_at=?, updated_at=? WHERE id=?",
        (reason, note, _now(), _now(), proposal_id))
    conn.commit()
    return get(conn, proposal_id)


def approve(conn, proposal_id: int, payload: dict | None = None, note: str = "") -> dict:
    """Approve and execute in one go — for the autonomous loop and for tests.

    The HTTP path uses `mark_approved` + `execute_approved` instead, so a three-minute
    discovery run does not happen inside the request.
    """
    mark_approved(conn, proposal_id, payload, note)
    return execute_approved(conn, proposal_id, note=note)


def execute_approved(conn, proposal_id: int, note: str = "") -> dict:
    """Run the action of an already-approved proposal. Safe to call from a background
    task: everything it needs is in the row."""
    p = get(conn, proposal_id)
    if not p:
        raise ProposalError("提议不存在")
    if p["status"] not in APPROVED_STATUSES:
        raise ProposalError(f"提议是 {p['status']}，不是待执行状态")
    return _execute(conn, p, note=note)


def mark_approved(conn, proposal_id: int, payload: dict | None = None,
                  note: str = "") -> dict:
    """Record the decision without doing the work. An edited payload is recorded as
    `edited_approved` — the diff between what the agent wrote and what Allen sent is
    phase C's best data.

    Taking `pending` away here is also what stops a double click from running the
    action twice: the second one no longer finds a pending row."""
    p = get(conn, proposal_id)
    if not p:
        raise ProposalError("提议不存在")
    if p["status"] != "pending":
        raise ProposalError(f"提议已是 {p['status']}，不能重复确认")
    edited = payload is not None and payload != p["payload"]
    if edited:
        # Keep the agent's version. What Allen changed is the only real training signal
        # phase C has, and overwriting the draft in place threw it away every time.
        conn.execute(
            "UPDATE agent_proposals SET payload=?, original_payload=?, updated_at=?"
            " WHERE id=?",
            (json.dumps(payload, ensure_ascii=False),
             json.dumps(p["payload"], ensure_ascii=False), _now(), proposal_id))
        conn.commit()
        p = get(conn, proposal_id)
    conn.execute(
        "UPDATE agent_proposals SET status=?, decided_at=?, decided_note=?, updated_at=?"
        " WHERE id=?",
        ("edited_approved" if edited else "approved", _now(), note, _now(), proposal_id))
    conn.commit()
    return get(conn, proposal_id)


def fail_interrupted(conn) -> int:
    """A background execution dies with the process. Without this, its proposal shows
    「执行中」 forever — neither done nor failed. Marked failed rather than retried:
    re-running an action that may already have sent an email is the worse risk."""
    ensure_schema(conn)
    cur = conn.execute(
        "UPDATE agent_proposals SET status='failed', executed_at=?, execution_result=?,"
        " updated_at=? WHERE status IN (?, ?)",
        (_now(), "服务重启，执行中断——请确认结果后再决定是否重跑", _now(),
         *APPROVED_STATUSES))
    conn.commit()
    return cur.rowcount


# ---------------------------------------------------------------- execute

def _finish(conn, proposal_id: int, ok: bool, result: str) -> dict:
    conn.execute(
        "UPDATE agent_proposals SET status=?, executed_at=?, execution_result=?, updated_at=?"
        " WHERE id=?",
        ("executed" if ok else "failed", _now(), result[:500], _now(), proposal_id))
    conn.commit()
    return get(conn, proposal_id)


def _execute(conn, p: dict, note: str = "") -> dict:
    from app.agent import executors
    handler = executors.HANDLERS.get(p["kind"])
    if handler is None:
        return _finish(conn, p["id"], False, f"{p['kind']} 没有执行器，无法执行")
    try:
        mode = "auto" if p["status"] == "pending" else "approved"
        result = handler(conn, {**p, "execution_mode": mode})
    except Exception as exc:  # noqa: BLE001 — a failed action must stay visible, not crash
        return _finish(conn, p["id"], False, f"{type(exc).__name__}: {exc}")
    return _finish(conn, p["id"], True, result)


# ---------------------------------------------------------------- lead memory

def get_memory(conn, lead_no: int) -> dict | None:
    ensure_schema(conn)
    r = conn.execute("SELECT * FROM lead_memory WHERE lead_no=?", (lead_no,)).fetchone()
    return dict(r) if r else None


def set_memory(conn, lead_no: int, summary_text: str, source_count: int = 0) -> dict:
    ensure_schema(conn)
    conn.execute(
        "INSERT INTO lead_memory(lead_no, summary, source_count, updated_at)"
        " VALUES (?,?,?,?) ON CONFLICT(lead_no) DO UPDATE SET"
        " summary=excluded.summary, source_count=excluded.source_count,"
        " updated_at=excluded.updated_at",
        (lead_no, summary_text.strip(), source_count, _now()))
    conn.commit()
    return get_memory(conn, lead_no)
