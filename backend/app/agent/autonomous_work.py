"""Execute routine Agent-owned CRM work without turning it into human homework.

This worker only handles traceable public-data research. It may read company websites,
classify ICP, repair a dead contact channel from company-owned evidence, verify a junk
company name, and run Decision Maker Radar. It never sends a customer message and never
sets pricing/payment/delivery/warranty/quote terms.
"""
from __future__ import annotations

import datetime as dt
import urllib.parse

from app import activities, enrich, icp, recheck
from app.agent import opportunity_coach, proposals, task_ownership

MAX_PER_CYCLE = 6
DECISION_MAKER_MAX_PER_CYCLE = 2
TRANSIENT_RETRY_DAYS = 3
UNKNOWN_ICP_RETRY_DAYS = 30
DECISION_RETRY_DAYS = 30
CHANNEL_RETRY_DAYS = 14


def _today() -> dt.date:
    return dt.date.today()


def _domain(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if not raw.lower().startswith(("http://", "https://")):
        raw = "https://" + raw
    return urllib.parse.urlparse(raw).netloc.lower().removeprefix("www.")


def _append_note(existing: str | None, text: str) -> str:
    stamp = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M UTC")
    return f"{existing or ''}\n[Agent {stamp}] {text}".strip()[:1000]


def _reschedule(conn, task: dict, days: int, note: str) -> None:
    activities.update(conn, task["id"], {
        "due_at": (_today() + dt.timedelta(days=max(1, days))).isoformat(),
        "note": _append_note(task.get("note"), note),
    })


def _done(conn, task: dict, note: str) -> None:
    activities.update(conn, task["id"], {
        "status": "done",
        "note": _append_note(task.get("note"), note),
    })


def _lead(conn, lead_no: int) -> dict | None:
    row = conn.execute(
        "SELECT no,company_en,website,email,email_status,bounced_at,phone,instagram,facebook,"
        " target_fit FROM leads WHERE no=?",
        (lead_no,),
    ).fetchone()
    return dict(row) if row else None


def _site_info(lead: dict) -> dict:
    domain = _domain(lead.get("website"))
    if not domain:
        raise RuntimeError("客户没有可读取官网")
    info = enrich.enrich_domain(domain)
    if int(info.get("pages") or 0) <= 0:
        raise RuntimeError("官网暂时无法读取")
    return info


def _refresh_common(conn, lead: dict, info: dict) -> dict:
    """Reuse the normal conflict-safe website reread before applying special repairs."""
    return recheck.run(
        conn, lead["no"], first_read=True,
        enrich_fn=lambda _website: info,
    )


def _refresh_icp(conn, task: dict, lead: dict) -> str:
    info = _site_info(lead)
    result = _refresh_common(conn, lead, info)
    classified = {
        "icp_type": info.get("icp_type") or "unknown",
        "fit_score": int(info.get("fit_score") or 0),
        "hits": [],
    }
    if classified["fit_score"] > 0 and classified["icp_type"] != "unknown":
        icp.apply_to_lead(conn, lead["no"], classified)
        _done(
            conn, task,
            f"官网已由 Agent 重读并完成 ICP 分级：{icp.label(classified['icp_type'])} "
            f"({classified['fit_score']})。",
        )
        return "done"
    _reschedule(
        conn, task, UNKNOWN_ICP_RETRY_DAYS,
        "官网已重读，但目前没有足够证据判定 LED 买家类型；保留为 Agent 后台复查，不转给人工。"
        + (f" 下次站点复查 {result.get('next_due')}。" if result.get("next_due") else ""),
    )
    return "rescheduled"


def _find_decision_maker(conn, task: dict, lead: dict) -> str:
    from app import decision_maker_radar

    coverage = opportunity_coach.contact_coverage(conn, lead["no"], {})
    if coverage["commercial_authority"]:
        _done(conn, task, "已有来源可追溯的 Owner / Purchasing / Procurement 等商务负责人证据。")
        return "done"
    result = decision_maker_radar.scan(conn, lead["no"])
    coverage = opportunity_coach.contact_coverage(conn, lead["no"], {})
    if coverage["commercial_authority"]:
        _done(
            conn, task,
            f"Decision Maker Radar 已找到并保存可行动负责人证据；本轮新增/晋级 "
            f"{result.get('created', 0)}/{result.get('promoted', 0)}。",
        )
        return "done"
    candidates = result.get("candidates") or []
    _reschedule(
        conn, task, DECISION_RETRY_DAYS,
        f"公开官网研究完成，当前只有 {len(candidates)} 个证据不足候选；候选保留在 Radar，"
        "不会要求你逐条人工查人，也不会把推测职位写成 CRM 决策人。",
    )
    return "rescheduled"


def _channel_available(conn, lead_no: int) -> bool:
    lead = conn.execute(
        "SELECT email,email_status,phone,instagram,facebook FROM leads WHERE no=?",
        (lead_no,),
    ).fetchone()
    if lead and (
        (lead["email"] and lead["email_status"] != "invalid")
        or lead["phone"] or lead["instagram"] or lead["facebook"]
    ):
        return True
    row = conn.execute(
        "SELECT 1 FROM contacts WHERE lead_no=? AND ("
        " (email IS NOT NULL AND email!='' AND COALESCE(email_status,'')!='invalid')"
        " OR (phone IS NOT NULL AND phone!='') OR (linkedin IS NOT NULL AND linkedin!=''))"
        " LIMIT 1",
        (lead_no,),
    ).fetchone()
    return row is not None


def _replace_invalid_channel(conn, task: dict, lead: dict) -> str:
    from app import contacts, verify

    contacts.ensure_schema(conn)
    if _channel_available(conn, lead["no"]):
        _done(conn, task, "客户已经有可行动联系渠道。")
        return "done"
    info = _site_info(lead)
    _refresh_common(conn, lead, info)

    # A different address explicitly published on the company website may replace an
    # already-invalid lead email. Clear the old bounce fact because it belonged to the
    # old address, then run the existing verifier before any send path can use it.
    fresh_email = str(info.get("email") or "").strip().lower()
    current_email = str(lead.get("email") or "").strip().lower()
    if lead.get("email_status") == "invalid" and fresh_email and fresh_email != current_email:
        conn.execute(
            "UPDATE leads SET email=?,email_source=?,email_status=NULL,bounced_at=NULL WHERE no=?",
            (fresh_email, info.get("email_source"), lead["no"]),
        )
        conn.commit()
        verify.verify_leads(conn, [lead["no"]])

    if _channel_available(conn, lead["no"]):
        _done(conn, task, "Agent 已从公司官网补到并校验可行动联系渠道。")
        return "done"
    _reschedule(
        conn, task, CHANNEL_RETRY_DAYS,
        "官网已重新检查，仍没有可靠联系渠道；由 Agent 后台继续复查，不转给人工。",
    )
    return "rescheduled"


def _verify_company(conn, task: dict, lead: dict) -> str:
    from app import fix_junk_names, sales_intelligence

    if not sales_intelligence._junk_company_name(lead.get("company_en")):
        _done(conn, task, "公司名称已经不是页面标题/404 类占位名称。")
        return "done"
    new_name, source = fix_junk_names.resolve(lead)
    if new_name and new_name != lead.get("company_en"):
        old = lead.get("company_en") or ""
        conn.execute("UPDATE leads SET company_en=? WHERE no=?", (new_name, lead["no"]))
        conn.execute(
            "INSERT INTO notes(lead_no,created_at,text) VALUES (?,?,?)",
            (lead["no"], dt.datetime.now(dt.UTC).isoformat(),
             f"Agent 公司名修复：{old} → {new_name}（来源：{source}）"),
        )
        conn.commit()
        _done(conn, task, f"公司名称已自动核实为 {new_name}（{source}）。")
        return "done"
    _reschedule(conn, task, 30, "官网/域名仍无法给出可靠公司名，Agent 后台稍后重试。")
    return "rescheduled"


def _radar_review(conn, task: dict) -> str:
    _done(
        conn, task,
        "弱证据联系人候选已保留在 Decision Maker Radar，等待后续公开证据增强；"
        "这不是需要人工完成的销售待办。",
    )
    return "done"


def _rule_for(proposal: dict) -> tuple[str | None, dict]:
    payload = proposal.get("payload") or {}
    rule = payload.get("completion_rule")
    if isinstance(rule, dict) and rule.get("type") == "account_brain":
        return str(rule.get("next_action_key") or ""), rule
    if str(proposal.get("dedupe_key") or "").startswith("decision-maker-"):
        return "radar_review", {}
    return None, {}


def sweep(conn, *, today: dt.date | None = None, limit: int = MAX_PER_CYCLE) -> dict:
    """Consume due Agent-owned work with bounded live I/O."""
    today = today or _today()
    ownership = task_ownership.backfill(conn)
    rows = conn.execute(
        "SELECT * FROM activities WHERE status='open' AND source='agent'"
        " AND work_owner='agent' AND source_ref LIKE 'proposal:%'"
        " AND (due_at IS NULL OR due_at<=?)"
        " ORDER BY due_at IS NULL,due_at,id LIMIT ?",
        (today.isoformat(), max(1, min(int(limit), 50))),
    ).fetchall()
    processed = done = rescheduled = failed = 0
    decision_scans = 0
    results: list[dict] = []

    for raw in rows:
        task = dict(raw)
        try:
            proposal_id = int(str(task["source_ref"]).split(":", 1)[1])
        except (TypeError, ValueError, IndexError):
            continue
        proposal = proposals.get(conn, proposal_id)
        if not proposal:
            continue
        key, _rule = _rule_for(proposal)
        if not key:
            continue
        if key == "find_decision_maker" and decision_scans >= DECISION_MAKER_MAX_PER_CYCLE:
            continue
        lead = _lead(conn, task["lead_no"])
        if lead is None:
            _done(conn, task, "客户记录已不存在，任务自动关闭。")
            continue
        processed += 1
        try:
            if key == "refresh_icp":
                outcome = _refresh_icp(conn, task, lead)
            elif key == "find_decision_maker":
                decision_scans += 1
                outcome = _find_decision_maker(conn, task, lead)
            elif key == "replace_invalid_channel":
                outcome = _replace_invalid_channel(conn, task, lead)
            elif key == "verify_company":
                outcome = _verify_company(conn, task, lead)
            elif key == "radar_review":
                outcome = _radar_review(conn, task)
            else:
                continue
        except Exception as exc:  # noqa: BLE001 — one dead site must not stop other accounts
            failed += 1
            _reschedule(
                conn, task, TRANSIENT_RETRY_DAYS,
                f"自动处理暂时失败：{type(exc).__name__}: {str(exc)[:180]}。已排队重试。",
            )
            outcome = "retry"
        if outcome == "done":
            done += 1
        elif outcome == "rescheduled":
            rescheduled += 1
        results.append({"activity_id": task["id"], "lead_no": task["lead_no"],
                        "key": key, "outcome": outcome})

    return {
        "ownership": ownership,
        "processed": processed,
        "done": done,
        "rescheduled": rescheduled,
        "failed": failed,
        "results": results,
    }
