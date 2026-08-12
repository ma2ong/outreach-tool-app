"""Explainable sales priority and source-backed LED buying signals."""
from __future__ import annotations

import datetime as dt
import hashlib
import re
import sqlite3

from app import recheck


SIGNAL_TYPES = (
    "project", "hiring", "exhibition", "distributor", "tender", "social",
    "site_change", "location", "partnership", "manual",
)
SIGNAL_STATUSES = ("new", "reviewed", "actioned", "dismissed")
USE_CASES = (
    "Rental", "Fixed Installation", "DOOH", "Retail", "Sports", "Church",
    "Control Room", "Broadcast", "Virtual Production",
)
EDITABLE_SIGNAL_FIELDS = {
    "signal_type", "headline", "evidence", "source_url", "occurred_at",
    "confidence", "use_case", "product_fit", "suggested_angle", "status",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS buying_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_no INTEGER NOT NULL,
    opportunity_id INTEGER,
    signal_type TEXT NOT NULL,
    headline TEXT NOT NULL,
    evidence TEXT NOT NULL,
    source_url TEXT NOT NULL,
    occurred_at TEXT,
    captured_at TEXT NOT NULL,
    confidence INTEGER NOT NULL,
    use_case TEXT,
    product_fit TEXT,
    suggested_angle TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    fingerprint TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(lead_no) REFERENCES leads(no) ON DELETE CASCADE,
    FOREIGN KEY(opportunity_id) REFERENCES opportunities(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_buying_signals_lead ON buying_signals(lead_no, status);
CREATE INDEX IF NOT EXISTS idx_buying_signals_status ON buying_signals(status, captured_at);
CREATE INDEX IF NOT EXISTS idx_buying_signals_occurred ON buying_signals(occurred_at);
"""


class SalesIntelligenceValidation(ValueError):
    pass


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def _today() -> dt.date:
    return dt.date.today()


def ensure_schema(conn: sqlite3.Connection) -> None:
    from app.contacts import ensure_schema as ensure_contacts
    from app.opportunities import ensure_schema as ensure_opportunities
    from app.activities import ensure_schema as ensure_activities
    from app.sales_documents import ensure_schema as ensure_documents
    ensure_contacts(conn)
    ensure_opportunities(conn)
    ensure_activities(conn)
    ensure_documents(conn)
    conn.executescript(SCHEMA)
    conn.commit()


def _date(value, field: str) -> str | None:
    if value in (None, ""):
        return None
    try:
        return dt.date.fromisoformat(str(value)).isoformat()
    except ValueError as exc:
        raise SalesIntelligenceValidation(f"{field} 必须是 YYYY-MM-DD") from exc


def _text(value, field: str, *, required: bool = False, limit: int = 2000) -> str | None:
    clean = str(value or "").strip()
    if required and not clean:
        raise SalesIntelligenceValidation(f"{field}不能为空")
    return clean[:limit] or None


def _validate_signal(data: dict, *, partial: bool = False) -> dict:
    clean = {k: v for k, v in data.items() if k in EDITABLE_SIGNAL_FIELDS}
    required = not partial
    for field, label, limit in (
        ("headline", "信号标题", 240), ("evidence", "证据", 2000),
        ("source_url", "来源 URL", 1000),
    ):
        if field in clean or required:
            clean[field] = _text(clean.get(field), label, required=required, limit=limit)
    if clean.get("source_url") and not re.match(r"^https?://[^\s]+$", clean["source_url"], re.I):
        raise SalesIntelligenceValidation("来源 URL 必须是可访问的 http/https 地址")
    if "signal_type" in clean:
        if clean["signal_type"] not in SIGNAL_TYPES:
            raise SalesIntelligenceValidation("未知采购信号类型")
    elif required:
        clean["signal_type"] = "manual"
    if "status" in clean and clean["status"] not in SIGNAL_STATUSES:
        raise SalesIntelligenceValidation("未知信号状态")
    if "confidence" in clean:
        try:
            clean["confidence"] = int(clean["confidence"])
        except (TypeError, ValueError) as exc:
            raise SalesIntelligenceValidation("可信度必须是 1-100 的整数") from exc
        if not 1 <= clean["confidence"] <= 100:
            raise SalesIntelligenceValidation("可信度必须是 1-100 的整数")
    elif required:
        clean["confidence"] = 60
    if "occurred_at" in clean:
        clean["occurred_at"] = _date(clean["occurred_at"], "发生日期")
    if "use_case" in clean and clean["use_case"] not in (None, "", *USE_CASES):
        raise SalesIntelligenceValidation("未知 LED 应用场景")
    for field in ("use_case", "product_fit", "suggested_angle"):
        if field in clean:
            clean[field] = _text(clean[field], field, limit=500)
    return clean


def _fingerprint(lead_no: int, data: dict) -> str:
    raw = "|".join(str(v or "").strip().lower() for v in (
        lead_no, data.get("signal_type"), data.get("source_url"),
        data.get("headline"), data.get("occurred_at"),
    ))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_signal(conn: sqlite3.Connection, signal_id: int) -> dict | None:
    ensure_schema(conn)
    row = conn.execute(
        "SELECT s.*, l.company_en, l.country, o.title opportunity_title"
        " FROM buying_signals s JOIN leads l ON l.no=s.lead_no"
        " LEFT JOIN opportunities o ON o.id=s.opportunity_id WHERE s.id=?",
        (signal_id,),
    ).fetchone()
    return dict(row) if row else None


def create_signal(conn: sqlite3.Connection, lead_no: int, data: dict) -> dict:
    ensure_schema(conn)
    if conn.execute("SELECT 1 FROM leads WHERE no=?", (lead_no,)).fetchone() is None:
        raise SalesIntelligenceValidation("客户不存在")
    clean = _validate_signal(data)
    clean.setdefault("status", "new")
    now = _now()
    fingerprint = _fingerprint(lead_no, clean)
    existing = conn.execute(
        "SELECT id FROM buying_signals WHERE fingerprint=?", (fingerprint,)
    ).fetchone()
    if existing:
        return get_signal(conn, existing["id"])
    cols = ["lead_no", *clean.keys(), "captured_at", "fingerprint", "created_at", "updated_at"]
    values = [lead_no, *clean.values(), now, fingerprint, now, now]
    cur = conn.execute(
        f"INSERT INTO buying_signals({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
        values,
    )
    conn.commit()
    return get_signal(conn, cur.lastrowid)


def update_signal(conn: sqlite3.Connection, signal_id: int, data: dict) -> dict | None:
    current = get_signal(conn, signal_id)
    if current is None:
        return None
    clean = _validate_signal(data, partial=True)
    if not clean:
        return current
    merged = {**current, **clean}
    if {"signal_type", "source_url", "headline", "occurred_at"} & clean.keys():
        clean["fingerprint"] = _fingerprint(current["lead_no"], merged)
    clean["updated_at"] = _now()
    try:
        conn.execute(
            f"UPDATE buying_signals SET {', '.join(f'{k}=?' for k in clean)} WHERE id=?",
            [*clean.values(), signal_id],
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise SalesIntelligenceValidation("同一来源的这条信号已经存在") from exc
    return get_signal(conn, signal_id)


def list_signals(conn: sqlite3.Connection, *, lead_no: int | None = None,
                 status: str | None = None, limit: int = 200) -> list[dict]:
    ensure_schema(conn)
    where, params = [], []
    if lead_no is not None:
        where.append("s.lead_no=?")
        params.append(lead_no)
    if status:
        if status not in SIGNAL_STATUSES:
            raise SalesIntelligenceValidation("未知信号状态")
        where.append("s.status=?")
        params.append(status)
    sql = (
        "SELECT s.*, l.company_en, l.country, o.title opportunity_title"
        " FROM buying_signals s JOIN leads l ON l.no=s.lead_no"
        " LEFT JOIN opportunities o ON o.id=s.opportunity_id"
    )
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY COALESCE(s.occurred_at, substr(s.captured_at,1,10)) DESC, s.confidence DESC, s.id DESC LIMIT ?"
    params.append(max(1, min(int(limit), 1000)))
    return [dict(r) for r in conn.execute(sql, params)]


def record_site_change(conn: sqlite3.Connection, lead_no: int, website: str,
                       notes: list[str], *, hook: str | None = None) -> dict:
    source_url = website.strip()
    if not re.match(r"^https?://", source_url, re.I):
        source_url = "https://" + source_url
    return create_signal(conn, lead_no, {
        "signal_type": "site_change",
        "headline": "官网出现新的销售线索",
        "evidence": "；".join(notes)[:2000],
        "source_url": source_url,
        "occurred_at": _today().isoformat(),
        "confidence": 70,
        "product_fit": "LED display solutions",
        "suggested_angle": hook or "官网近期有更新，可先核实新项目或联系人变化。",
    })


def merge_lead_signals(conn: sqlite3.Connection, keep: int, duplicate: int) -> None:
    """Repoint a duplicate company's evidence without creating duplicate signals."""
    ensure_schema(conn)
    for row in conn.execute(
        "SELECT * FROM buying_signals WHERE lead_no=? ORDER BY id", (duplicate,)
    ).fetchall():
        signal = dict(row)
        fingerprint = _fingerprint(keep, signal)
        existing = conn.execute(
            "SELECT id, opportunity_id, status FROM buying_signals WHERE fingerprint=?",
            (fingerprint,),
        ).fetchone()
        if existing:
            opportunity_id = existing["opportunity_id"] or signal["opportunity_id"]
            status = "actioned" if "actioned" in (existing["status"], signal["status"]) \
                else existing["status"]
            conn.execute(
                "UPDATE buying_signals SET opportunity_id=?, status=?, updated_at=? WHERE id=?",
                (opportunity_id, status, _now(), existing["id"]),
            )
            conn.execute("DELETE FROM buying_signals WHERE id=?", (signal["id"],))
        else:
            conn.execute(
                "UPDATE buying_signals SET lead_no=?, fingerprint=?, updated_at=? WHERE id=?",
                (keep, fingerprint, _now(), signal["id"]),
            )


def _component(key: str, label: str, score: int, maximum: int,
               reasons: list[str]) -> dict:
    return {"key": key, "label": label, "score": score, "max": maximum,
            "reasons": reasons}


def _fresh_date(value: str | None) -> dt.date | None:
    if not value:
        return None
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _best_signal_points(signals: list[sqlite3.Row], today: dt.date) -> tuple[int, sqlite3.Row | None]:
    best_points, best = 0, None
    for signal in signals:
        when = _fresh_date(signal["occurred_at"] or signal["captured_at"])
        age = (today - when).days if when else 999
        confidence = int(signal["confidence"] or 0)
        points = 20 if confidence >= 80 else 15 if confidence >= 60 else 8 if confidence >= 40 else 3
        if age > 180:
            points = round(points * 0.5)
        elif age > 90:
            points = round(points * 0.75)
        if points > best_points:
            best_points, best = points, signal
    return best_points, best


def _junk_company_name(value: str | None) -> bool:
    name = re.sub(r"[^a-z0-9]+", " ", (value or "").strip().lower()).strip()
    exact = {"contact", "contact us", "home", "about", "index", "404",
             "page not found", "pagina nao encontrada", "pagina no encontrada"}
    return name in exact or "page not available" in name or name.endswith("not found")


def _next_action(conn: sqlite3.Connection, lead: sqlite3.Row,
                 best_signal: sqlite3.Row | None) -> str:
    if lead["do_not_contact"]:
        return "保持不再联系，不进入任何发送队列"
    if lead["stage"] == "won":
        return "已成交：到报价订单页推进收款、生产和发货"
    if lead["stage"] == "lost":
        return "已丢单：仅在出现新的高可信项目证据时重新评估"
    reply = conn.execute(
        "SELECT 1 FROM inbox_messages WHERE lead_no=? AND kind='reply' AND handled_at IS NULL LIMIT 1",
        (lead["no"],),
    ).fetchone()
    if reply:
        return "立即处理客户回复，并确认项目用途、尺寸、像素间距、预算和交期"
    reply_status = conn.execute(
        "SELECT 1 FROM outreach WHERE lead_no=? AND (status='replied' OR reply_received=1) LIMIT 1",
        (lead["no"],),
    ).fetchone()
    if reply_status:
        return "立即处理客户回复，并确认项目用途、尺寸、像素间距、预算、交期与下一次沟通时间"
    overdue = conn.execute(
        "SELECT title FROM activities WHERE lead_no=? AND status='open' AND due_at < date('now')"
        " ORDER BY due_at, id LIMIT 1", (lead["no"],),
    ).fetchone()
    if overdue:
        return f"先完成逾期任务：{overdue['title']}"
    accepted = conn.execute(
        "SELECT quote_no FROM quotes q WHERE q.lead_no=? AND q.status='accepted'"
        " AND NOT EXISTS (SELECT 1 FROM orders o WHERE o.quote_id=q.id) ORDER BY q.id DESC LIMIT 1",
        (lead["no"],),
    ).fetchone()
    if accepted:
        return f"报价 {accepted['quote_no']} 已接受，立即转为订单"
    sent = conn.execute(
        "SELECT quote_no FROM quotes WHERE lead_no=? AND status='sent' ORDER BY id DESC LIMIT 1",
        (lead["no"],),
    ).fetchone()
    if sent:
        return f"跟进报价 {sent['quote_no']}：确认技术疑问、付款条款和决策时间"
    if best_signal and int(best_signal["confidence"] or 0) >= 60:
        return best_signal["suggested_angle"] or f"核实采购信号：{best_signal['headline']}"
    opportunity = conn.execute(
        "SELECT next_action, title FROM opportunities WHERE lead_no=?"
        " AND stage NOT IN ('won','lost') ORDER BY updated_at DESC LIMIT 1", (lead["no"],),
    ).fetchone()
    if opportunity:
        return opportunity["next_action"] or f"补齐商机“{opportunity['title']}”的明确下一步和日期"
    if _junk_company_name(lead["company_en"]):
        return "先从官网或域名核实正确公司名；当前名称像页面标题，不能用于外发"
    if recheck.fit_score(lead["target_fit"]) == 0:
        return "先重新读取官网并完成 ICP 分级，确认它是否真是 LED 买家"
    decision = conn.execute(
        "SELECT 1 FROM contacts WHERE lead_no=? AND role='decision_maker' LIMIT 1", (lead["no"],)
    ).fetchone()
    if not decision:
        return "先找到 Owner / Purchasing / Project 决策联系人，再发送针对性消息"
    if lead["email_status"] == "invalid" and not (lead["phone"] or lead["instagram"]):
        return "邮箱无效：补找决策人邮箱、WhatsApp 或 Instagram"
    touched = conn.execute(
        "SELECT 1 FROM outreach WHERE lead_no=? AND status IN ('messaged','replied') LIMIT 1",
        (lead["no"],),
    ).fetchone()
    if not touched:
        return "用官网证据写首条消息，先单渠道触达并安排下一步"
    return "确认最近一次触达结果，安排有日期的下一步任务"


def score_lead(conn: sqlite3.Connection, lead_no: int,
               today: dt.date | None = None, *, _ensure: bool = True) -> dict | None:
    if _ensure:
        ensure_schema(conn)
    today = today or _today()
    lead = conn.execute("SELECT * FROM leads WHERE no=?", (lead_no,)).fetchone()
    if lead is None:
        return None

    raw_fit = recheck.fit_score(lead["target_fit"])
    fit_score = min(30, round(raw_fit * 0.30))
    fit_reasons = [f"官网 ICP 契合分 {raw_fit}/100，折算 {fit_score}/30"] if raw_fit else ["尚未完成官网 ICP 分级"]

    contacts = conn.execute("SELECT * FROM contacts WHERE lead_no=?", (lead_no,)).fetchall()
    named = any((c["name"] or "").strip() for c in contacts)
    decision = any(c["role"] == "decision_maker" for c in contacts)
    has_verified = any(c["email"] and c["email_status"] in ("valid", "role") for c in contacts)
    has_email = bool(lead["email"] and lead["email_status"] != "invalid") or any(
        c["email"] and c["email_status"] != "invalid" for c in contacts)
    has_phone = bool(lead["phone"]) or any(c["phone"] for c in contacts)
    contact_score = (8 if decision else 4 if any(c["title"] for c in contacts) else 0) + (4 if named else 0)
    channel_points = 6 if has_verified else 4 if has_email or has_phone else 3 if lead["instagram"] else 0
    contact_score = min(20, contact_score + channel_points)
    contact_reasons = []
    contact_reasons.append("已有决策联系人" if decision else "缺少 Owner / Purchasing / Project 决策角色")
    contact_reasons.append("联系人有姓名" if named else "联系人姓名未覆盖")
    contact_reasons.append("有已验证联系渠道" if has_verified else "有可用联系渠道" if channel_points else "没有可用联系渠道")

    signals = conn.execute(
        "SELECT * FROM buying_signals WHERE lead_no=? AND status!='dismissed'"
        " ORDER BY COALESCE(occurred_at, substr(captured_at,1,10)) DESC", (lead_no,),
    ).fetchall()
    signal_points, best_signal = _best_signal_points(signals, today)
    opportunity = conn.execute(
        "SELECT stage, title FROM opportunities WHERE lead_no=? AND stage NOT IN ('won','lost')"
        " ORDER BY updated_at DESC LIMIT 1", (lead_no,),
    ).fetchone()
    stage_points = {"qualified": 10, "requirements": 15, "quoted": 20, "negotiation": 25}
    opportunity_points = stage_points.get(opportunity["stage"], 0) if opportunity else 0
    intent_score = min(25, max(signal_points, opportunity_points) + (5 if signal_points and opportunity_points else 0))
    intent_reasons = []
    if best_signal:
        intent_reasons.append(f"采购信号：{best_signal['headline']}（可信度 {best_signal['confidence']}）")
    if opportunity:
        intent_reasons.append(f"已有商机：{opportunity['title']}（{opportunity['stage']}）")
    if not intent_reasons:
        intent_reasons.append("尚无来源明确的采购信号或开放商机")

    outreach = conn.execute(
        "SELECT COALESCE(SUM(touch_count),0) touches,"
        " MAX(CASE WHEN status='replied' OR reply_received=1 THEN 1 ELSE 0 END) replied"
        " FROM outreach WHERE lead_no=?", (lead_no,),
    ).fetchone()
    touches = int(outreach["touches"] or 0)
    replied = bool(outreach["replied"])
    engagement_score = 15 if replied else min(10, 4 + touches * 2) if touches else 0
    engagement_reasons = ["客户已经回复" if replied else f"已完成 {touches} 次触达" if touches else "尚未触达"]

    freshness_score = 0
    freshness_reasons = []
    if lead["website"]:
        freshness_score += 2; freshness_reasons.append("有官网")
    if lead["country"]:
        freshness_score += 1; freshness_reasons.append("国家已确认")
    if lead["brief"] or lead["hook"]:
        freshness_score += 2; freshness_reasons.append("有官网简介或证据开场白")
    if has_email or has_phone or lead["instagram"]:
        freshness_score += 3; freshness_reasons.append("有可行动联系方式")
    due = _fresh_date(lead["recheck_due"])
    if due and due >= today:
        freshness_score += 2; freshness_reasons.append(f"官网复检已排到 {due.isoformat()}")
    if not freshness_reasons:
        freshness_reasons.append("客户资料尚未补全")

    components = [
        _component("fit", "ICP 契合度", fit_score, 30, fit_reasons),
        _component("contact", "联系人质量", contact_score, 20, contact_reasons),
        _component("intent", "采购意向", intent_score, 25, intent_reasons),
        _component("engagement", "互动进展", engagement_score, 15, engagement_reasons),
        _component("freshness", "数据时效", freshness_score, 10, freshness_reasons),
    ]
    warnings = []
    penalty = 0
    junk_name = _junk_company_name(lead["company_en"])
    if junk_name:
        penalty += 25
        warnings.append("公司名像 Contact / 404 等页面标题，扣 25 分并要求先核实")
    if lead["email_status"] == "invalid" and not has_phone and not lead["instagram"]:
        penalty += 8
        warnings.append("唯一邮箱无效且没有替代渠道，扣 8 分")
    score = max(0, min(100, sum(c["score"] for c in components) - penalty))
    if lead["do_not_contact"] or lead["stage"] in ("won", "lost"):
        score = 0
    grade = "A" if score >= 75 else "B" if score >= 55 else "C" if score >= 35 else "D"
    return {
        "lead_no": lead_no, "company_en": lead["company_en"], "country": lead["country"],
        "target_fit": lead["target_fit"], "score": score, "grade": grade,
        "components": components, "warnings": warnings,
        "next_action": _next_action(conn, lead, best_signal),
        "best_signal": dict(best_signal) if best_signal else None,
        "missing_decision_maker": not decision,
        "data_incomplete": freshness_score < 7 or raw_fit == 0 or junk_name,
    }


def ranked(conn: sqlite3.Connection, *, limit: int = 100,
           min_score: int = 0) -> list[dict]:
    ensure_schema(conn)
    nos = [r["no"] for r in conn.execute(
        "SELECT no FROM leads WHERE COALESCE(do_not_contact,0)=0"
        " AND COALESCE(stage,'new') NOT IN ('won','lost')"
    )]
    rows = [score_lead(conn, no, _ensure=False) for no in nos]
    rows = [row for row in rows if row and row["score"] >= min_score]
    rows.sort(key=lambda row: (-row["score"], row["lead_no"]))
    return rows[:max(1, min(int(limit), 2000))]


def summary(conn: sqlite3.Connection) -> dict:
    rows = ranked(conn, limit=2000)
    signal_count = conn.execute(
        "SELECT COUNT(*) c FROM buying_signals WHERE status='new'"
    ).fetchone()["c"]
    return {
        "ranked_accounts": len(rows),
        "grade_a": sum(r["grade"] == "A" for r in rows),
        "new_signals": int(signal_count),
        "missing_decision_maker": sum(r["missing_decision_maker"] for r in rows),
        "data_incomplete": sum(r["data_incomplete"] for r in rows),
    }


def create_task_from_signal(conn: sqlite3.Connection, signal_id: int) -> dict | None:
    signal = get_signal(conn, signal_id)
    if signal is None:
        return None
    from app import activities
    if signal["signal_type"] == "site_change":
        existing = conn.execute(
            "SELECT id FROM activities WHERE lead_no=? AND source='recheck' AND status='open'"
            " ORDER BY id DESC LIMIT 1", (signal["lead_no"],),
        ).fetchone()
        if existing:
            update_signal(conn, signal_id, {"status": "actioned"})
            return activities.get(conn, existing["id"])
    activity_id, _ = activities._upsert_source(
        conn, lead_no=signal["lead_no"], opportunity_id=None, source="signal",
        source_ref=f"signal:{signal_id}", type="task",
        title=f"跟进采购信号：{signal['headline']}", due_at=_today().isoformat(),
        priority="high" if signal["confidence"] >= 80 else "normal",
        note=f"证据：{signal['evidence']}\n来源：{signal['source_url']}"[:500],
    )
    activities.sync_lead(conn, signal["lead_no"])
    update_signal(conn, signal_id, {"status": "actioned"})
    return activities.get(conn, activity_id)


def create_opportunity_from_signal(conn: sqlite3.Connection, signal_id: int) -> dict | None:
    signal = get_signal(conn, signal_id)
    if signal is None:
        return None
    from app import opportunities
    if signal["opportunity_id"]:
        return opportunities.get(conn, signal["opportunity_id"])
    opportunity = opportunities.create(conn, signal["lead_no"], {
        "title": signal["headline"],
        "stage": "qualified",
        "use_case": signal["use_case"],
        "next_action": "确认项目用途、尺寸、像素间距、预算和交期",
        "next_action_date": (_today() + dt.timedelta(days=2)).isoformat(),
    })
    conn.execute(
        "UPDATE buying_signals SET opportunity_id=?, status='actioned', updated_at=? WHERE id=?",
        (opportunity["id"], _now(), signal_id),
    )
    conn.commit()
    return opportunities.get(conn, opportunity["id"])
