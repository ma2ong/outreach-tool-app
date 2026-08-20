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
    """Pause autonomous email when enough evidence says measurement or quality is unsafe."""
    delivery = campaigns.deliverability(conn)
    result = {"paused": False, "code": None, "deliverability": delivery}
    existing = autosend.safety_pause(conn)
    if existing:
        return {"paused": True, "code": existing.get("code"),
                "reason": existing.get("reason"), "deliverability": delivery,
                "pause": existing, "already_paused": True}
    if not autosend.enabled(conn) or delivery["sends"] < MIN_SAFETY_SAMPLE:
        return result
    if delivery["blind"]:
        code = "deliverability_blind"
        reason = (f"近 {delivery['days']} 天发给 {delivery['sends']} 家，但有退信无法被监测"
                  f"（未测发送 {delivery['unmeasured']}，同步异常={delivery['sync_broken']}）")
    elif delivery["danger"]:
        code = "bounce_rate"
        reason = (f"近 {delivery['days']} 天硬退信 {delivery['bounced']}/{delivery['sends']}，"
                  f"退信率 {delivery['bounce_rate']}% 超过 {campaigns.BOUNCE_DANGER_PCT}% 安全线")
    else:
        return result
    pause = autosend.pause(conn, code, reason, delivery)
    lead_no = _incident_lead(conn)
    if lead_no is not None:
        proposals.create(
            conn, "create_task", lead_no=lead_no,
            title="邮件自动跟进已安全暂停——先修复送达率",
            reasoning=reason,
            evidence=[{"claim": "邮件送达率安全闸", "source": reason}],
            payload={"title": "修复邮箱送达率后再恢复自动跟进", "type": "task",
                     "due_at": dt.date.today().isoformat(), "priority": "high",
                     "note": "Agent 已自动停掉邮件自动跟进；检查退信、邮箱验证和可收退信的发件箱。"},
            risk="high", dedupe_key=f"safety-{code}-{dt.date.today().isoformat()}")
    return {"paused": True, "code": code, "reason": reason,
            "deliverability": delivery, "pause": pause}


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
        out.append({"status": row["status"], "auto_import": payload.get("auto_import") or {}})
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
        if imported == 0:
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
