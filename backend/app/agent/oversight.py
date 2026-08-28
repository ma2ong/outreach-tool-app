"""Outcome and safety supervision for the autonomous sales operator."""
from __future__ import annotations

import datetime as dt
import json

from app import autosend, campaigns, settings
from app.agent import mission, proposals

MIN_SAFETY_SAMPLE = 25
RUN_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    result_json TEXT,
    incident_json TEXT,
    error TEXT
);
CREATE INDEX IF NOT EXISTS idx_agent_runs_started ON agent_runs(started_at DESC);
"""


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def ensure_schema(conn) -> None:
    conn.executescript(RUN_SCHEMA)
    conn.commit()


def start_run(conn) -> int:
    ensure_schema(conn)
    cur = conn.execute("INSERT INTO agent_runs(started_at) VALUES (?)", (_now(),))
    conn.commit()
    return cur.lastrowid


def finish_run(conn, run_id: int, status: str, result: dict | None = None,
               incident: dict | None = None, error: str = "") -> None:
    conn.execute(
        "UPDATE agent_runs SET finished_at=?, status=?, result_json=?, incident_json=?,"
        " error=? WHERE id=?",
        (_now(), status,
         json.dumps(result or {}, ensure_ascii=False),
         json.dumps(incident or {}, ensure_ascii=False),
         error[:500], run_id),
    )
    conn.commit()


def latest_runs(conn, limit: int = 5) -> list[dict]:
    ensure_schema(conn)
    rows = conn.execute(
        "SELECT id,started_at,finished_at,status,result_json,incident_json,error"
        " FROM agent_runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        for source, target in (("result_json", "result"), ("incident_json", "incident")):
            try:
                item[target] = json.loads(item.pop(source) or "{}")
            except json.JSONDecodeError:
                item[target] = {}
        out.append(item)
    return out


def _incident_lead(conn) -> int | None:
    row = conn.execute(
        "SELECT l.no FROM send_log s JOIN leads l ON l.no=s.lead_no"
        " WHERE s.channel='email' ORDER BY s.sent_at DESC LIMIT 1"
    ).fetchone()
    return row["no"] if row else None


def evaluate(conn) -> dict:
    """Report delivery health. It no longer decides how much gets sent (docs/67 R2).

    A bounce says *this address* is wrong. It does not say the customer should not be
    contacted, and it certainly does not say today is a day to send less. Allen's
    instruction is explicit: a high bounce rate means find the other person at that
    company, or reach them another way — the answer to a bad address is more work, not
    less outreach.

    So the numbers are still measured and still shown; what changed is that this
    function stopped switching sending off by itself. The domain risk is real and it is
    reported every day, but stopping is his call, not a threshold's.
    """
    delivery = campaigns.deliverability(conn)
    result = {"paused": False, "code": None, "deliverability": delivery}
    existing = autosend.safety_pause(conn)
    if existing:
        return {"paused": True, "code": existing.get("code"),
                "reason": existing.get("reason"), "deliverability": delivery,
                "pause": existing, "already_paused": True}
    if not autosend.enabled(conn) or delivery["sends"] < MIN_SAFETY_SAMPLE:
        return result
    # docs/75 R3. The rate used to come back as a warning here. Allen's instruction is
    # "不要管退信率多少" — and a warning that can never be acted on is not information,
    # it is a number asking to be obeyed. Bounces still produce work, one address at a
    # time, in `bounce_followup_tasks`; that is the whole of their effect now.
    return result


def bounce_followup_tasks(conn, limit: int = 20) -> int:
    """Turn recent hard bounces into "find another contact there" work (docs/67 R2).

    This is what replaces the circuit breaker. The old behaviour read a bounce as a
    reason to send less; the useful reading is that one address is dead and the company
    still needs reaching — through a different person, or a different channel.
    """
    rows = conn.execute(
        "SELECT no, company_en FROM leads"
        " WHERE bounced_at IS NOT NULL AND COALESCE(do_not_contact, 0) = 0"
        "   AND date(bounced_at) >= date('now', '-14 days')"
        " ORDER BY bounced_at DESC LIMIT ?", (limit,)).fetchall()
    made = 0
    for row in rows:
        proposals.create(
            conn, "create_task", lead_no=row["no"],
            title=f"{row['company_en'] or row['no']}：邮箱退信，找这家的另一个联系人",
            reasoning="这个地址收不到信，但这家公司仍然是目标",
            evidence=[{"claim": "硬退信", "source": "邮件退信通知"}],
            payload={"title": "找采购/项目负责人的直邮地址，或改走 WhatsApp / Instagram",
                     "type": "task", "due_at": dt.date.today().isoformat(),
                     "priority": "normal",
                     "note": "退信说明地址不对，不说明这家不该联系。"},
            risk="low", dedupe_key=f"bounce-{row['no']}")
        made += 1
    return made


def weak_sequence_ids(conn) -> set[int]:
    """Active sequence IDs that already sent enough with zero replies."""
    from app.agent import learn

    weak_names = {
        row["campaign"][len("序列:"):]
        for row in learn.weak_campaigns(conn)
        if row["channel"] == "email" and row["campaign"].startswith("序列:")
    }
    if not weak_names:
        return set()
    placeholders = ",".join("?" * len(weak_names))
    return {row["id"] for row in conn.execute(
        f"SELECT id FROM sequences WHERE name IN ({placeholders})", list(weak_names))}


def _today_discoveries(conn) -> list[dict]:
    proposals.ensure_schema(conn)
    rows = conn.execute(
        "SELECT status,payload FROM agent_proposals WHERE kind='discover_run'"
        " AND date(created_at,'localtime')=date('now','localtime') ORDER BY id DESC"
    ).fetchall()
    out = []
    for row in rows:
        try:
            payload = json.loads(row["payload"] or "{}")
        except json.JSONDecodeError:
            payload = {}
        found = payload.get("found") or []
        out.append({"status": row["status"],
                    "auto_import": payload.get("auto_import") or {},
                    # A run that never reached the auto-import branch has no such key.
                    # Absent is not the same as 'imported nothing'.
                    "auto_imported": "auto_import" in payload,
                    "usable": len([c for c in found if not c.get("excluded")])})
    return out


def daily_outcome(conn) -> dict:
    progress = mission.progress(conn)
    target = progress["daily_target"]
    achieved = progress["qualified_leads_imported_today"]
    blockers: list[dict] = []
    pause = autosend.safety_pause(conn)
    if pause:
        blockers.append({"code": "safety_pause", "message": pause["reason"]})
    attempt_date = settings.get(conn, "agent_plan_attempt_date")
    try:
        attempts = int(settings.get(conn, "agent_plan_attempts", "0") or 0)
    except (TypeError, ValueError):
        attempts = 0
    if (attempt_date == dt.date.today().isoformat() and attempts >= 3
            and settings.get(conn, "agent_plan_last_date") != attempt_date):
        blockers.append({"code": "planning_exhausted",
                         "message": "今日计划连续失败 3 次，已停止重试"})
    discoveries = _today_discoveries(conn)
    if achieved < target and not discoveries:
        blockers.append({"code": "no_discovery", "message": "今天还没有完成自动找客"})
    elif achieved < target and discoveries:
        imported = sum(int(d["auto_import"].get("imported") or 0) for d in discoveries)
        waiting = sum(d["usable"] for d in discoveries if not d["auto_imported"])
        if imported == 0 and waiting:
            # These candidates are good and one click from the lead base. Calling that
            # a failed quality gate hid 14 usable US accounts behind a fake blocker.
            blockers.append({"code": "candidates_awaiting_import",
                             "message": f"已搜到 {waiting} 个候选，去「已执行」里勾选导入"})
        elif imported == 0:
            blockers.append({"code": "no_qualified_imports",
                             "message": "今天的找客结果没有候选通过自动质量门"})
        missing = [item for d in discoveries
                   for item in d["auto_import"].get("missing_sequences") or []]
        if missing:
            blockers.append({"code": "missing_sequence",
                             "message": "缺少" + "、".join(dict.fromkeys(missing))})
    completion = 100 if target == 0 else min(100, round(achieved * 100 / target))
    return {"achieved": achieved, "target": target, "remaining": max(0, target - achieved),
            "completion_pct": completion, "met": achieved >= target, "blockers": blockers}
