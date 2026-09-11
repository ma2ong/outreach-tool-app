"""Deterministic quality gate for Agent-initiated first-touch email.

Rendered Message Guard answers "is this exact text safe to send?". This module answers
the earlier commercial question: "is this account worth spending a first touch on now?"
Only Agent autonomy uses this policy; a human can still deliberately send an unusual
account through the normal Outreach panel and its existing safety controls.
"""
from __future__ import annotations

import re

from app import case_library, message_guard, sales_intelligence
from app.agent import product_advisor
from app.personalize import render

GOOD_EMAIL_STATUSES = {"valid", "role"}

# A prospect question such as "Are you working on a current project?" is not a claim
# about our own history. Require case-library evidence only when the template asserts
# delivery / installation / references / recent projects as our proof.
_CASE_CLAIM_RE = re.compile(
    r"\b(?:delivered|installed|installation|references?|case\s+stud(?:y|ies))\b"
    r"|\brecent\b.{0,50}\bprojects?\b"
    r"|납품|설치사례|최근.{0,40}프로젝트", re.I | re.S,
)
# 패널 / 피치 were missing, so a Korean letter could claim what we manufacture
# without ever reaching the product gate — its English half could not.
_PRODUCT_CLAIM_RE = re.compile(
    r"\bP\s*\d+(?:\.\d+)?\b|\bpixel\s+pitch\b|\bindoor\b|\boutdoor\b"
    r"|\bpanels?\b|실내|실외|제품|패널|피치", re.I,
)


def _one(conn, sql: str, params: tuple = ()):  # compact scalar helper
    return conn.execute(sql, params).fetchone()


def _best_signal_summary(sales: dict) -> dict | None:
    signal = sales.get("best_signal") or {}
    if not signal:
        return None
    return {
        "headline": signal.get("headline"),
        "confidence": int(signal.get("confidence") or 0),
        "source_url": signal.get("source_url"),
    }


def evaluate_account(conn, lead_no: int, *, sales: dict | None = None,
                     allow_active_sequence: bool = False) -> dict:
    """Account/timing readiness before a template is chosen.

    `allow_active_sequence` exists only for sequence step zero: the enrollment itself
    must not disqualify the very first message, while every other first-touch caller
    keeps the original active-sequence blocker.
    """
    sales_intelligence.ensure_schema(conn)
    lead = _one(conn, "SELECT * FROM leads WHERE no=?", (lead_no,))
    if lead is None:
        return {"lead_no": lead_no, "ready_for_template_check": False,
                "score": 0, "grade": "D", "blockers": ["客户不存在"], "positives": []}

    sales = sales or sales_intelligence.score_lead(conn, lead_no, _ensure=False)
    blockers: list[str] = []
    positives: list[str] = []
    score = int((sales or {}).get("score") or 0)
    grade = (sales or {}).get("grade") or "D"

    # docs/74 R1. The score orders the queue; it does not decide whether to write. A cold
    # lead scores low because it is cold — refusing to send on that basis argues in a
    # circle, and on 2026-08-28 it killed 77 of 113 due letters to companies like SNA
    # Displays and Trans-Lux, whose only failing was an empty decision-maker column.
    positives.append(f"销售优先级 {score}/100（{grade}）")

    # docs/74 R3. Not knowing who buys displays is the reason to write the letter, not a
    # reason to withhold it — the letter asks that question. The gap becomes work instead
    # of silence: `decision_maker_radar` picks these accounts up.
    if not (sales or {}).get("data_incomplete"):
        positives.append("官网/ICP/联系方式证据完整")
    if not (sales or {}).get("missing_decision_maker"):
        positives.append("已有决策联系人")

    email_status = str(lead["email_status"] or "").strip().lower()
    if not lead["email"]:
        blockers.append("没有邮箱")
    elif email_status in GOOD_EMAIL_STATUSES:
        positives.append(f"邮箱状态 {email_status}")
    # An unverified address is not a known-bad one. `invalid` — where all 36 bounced
    # addresses sit — is still excluded upstream by eligibility, and Allen's rule is that
    # bounce risk may not reduce volume (docs/67).

    if lead["do_not_contact"]:
        blockers.append("客户已标记不再联系")
    if str(lead["stage"] or "new") in {"won", "lost"}:
        blockers.append(f"CRM 阶段为 {lead['stage']}，不做自主冷触达")

    if _one(conn,
            "SELECT 1 FROM inbox_messages WHERE lead_no=? AND kind='reply'"
            " AND handled_at IS NULL LIMIT 1", (lead_no,)):
        blockers.append("有未处理客户回复，先处理回复")
    if _one(conn,
            "SELECT 1 FROM opportunities WHERE lead_no=? AND stage NOT IN ('won','lost')"
            " LIMIT 1", (lead_no,)):
        blockers.append("已有开放商机，下一步应由商机流程而不是冷触达负责")
    if not allow_active_sequence and _one(conn,
            "SELECT 1 FROM sequence_enrollments WHERE lead_no=? AND status='active' LIMIT 1",
            (lead_no,)):
        blockers.append("已经在进行中的跟进序列里")
    if _one(conn,
            "SELECT 1 FROM outreach WHERE lead_no=? AND status IN ('messaged','replied') LIMIT 1",
            (lead_no,)):
        blockers.append("已经触达或已回复，不属于首触")
    if _one(conn,
            "SELECT 1 FROM send_log WHERE lead_no=?"
            " AND date(sent_at,'localtime')=date('now','localtime') LIMIT 1", (lead_no,)):
        blockers.append("今天已经有其他触达")

    task = _one(conn,
        "SELECT title FROM activities WHERE lead_no=? AND status='open'"
        " AND due_at IS NOT NULL AND due_at <= date('now', 'localtime') ORDER BY due_at,id LIMIT 1",
        (lead_no,),
    )
    if task:
        blockers.append(f"当前下一步由销售任务负责：{task['title']}")

    signal = _best_signal_summary(sales or {})
    if signal and signal["confidence"] >= 60:
        positives.append(f"有来源采购信号：{signal['headline']}（{signal['confidence']}）")

    return {
        "lead_no": lead_no,
        "company_en": lead["company_en"],
        "ready_for_template_check": not blockers,
        "score": score,
        "grade": grade,
        "blockers": blockers,
        "positives": positives,
        "best_signal": signal,
    }


def _template_evidence(conn, subject: str, body: str) -> tuple[list[str], list[str], dict]:
    text = f"{subject}\n{body}"
    blockers: list[str] = []
    positives: list[str] = []
    needs_case = bool(_CASE_CLAIM_RE.search(text))
    needs_product = bool(_PRODUCT_CLAIM_RE.search(text))

    case_count = 0
    if needs_case:
        case_count = len(case_library.list_all(conn, shareable=True, limit=1))
        if case_count:
            positives.append("模板的项目/交付说法有可公开案例库支撑")
        else:
            blockers.append("模板提到项目/交付案例，但案例库没有已批准为可公开的案例")

    product_count = 0
    if needs_product:
        product_count = len(product_advisor.approved_products(conn))
        if product_count:
            positives.append("模板的产品说法有 Agent-approved 产品库支撑")
        else:
            blockers.append("模板提到产品/点间距能力，但产品库没有 Agent-approved 产品事实")

    return blockers, positives, {
        "case_claim": needs_case,
        "product_claim": needs_product,
        "shareable_case_available": bool(case_count),
        "approved_product_available": bool(product_count),
    }


def evaluate(conn, lead_no: int, *, subject: str, body: str,
             sales: dict | None = None, allow_active_sequence: bool = False) -> dict:
    """Full account + template + exact rendered-message decision."""
    base = evaluate_account(conn, lead_no, sales=sales,
                            allow_active_sequence=allow_active_sequence)
    blockers = list(base["blockers"])
    positives = list(base["positives"])

    evidence_blockers, evidence_positives, template_evidence = _template_evidence(
        conn, subject or "", body or "",
    )
    blockers.extend(evidence_blockers)
    positives.extend(evidence_positives)

    lead_row = _one(conn, "SELECT * FROM leads WHERE no=?", (lead_no,))
    if lead_row is not None:
        lead = dict(lead_row)
        rendered_subject = render(subject, lead)
        rendered_body = render(body, lead)
        verdict = message_guard.check(rendered_body, lead, subject=rendered_subject)
        if verdict.blocked:
            blockers.append(f"最终文本 Guard：{verdict.detail}")
        else:
            positives.append("最终渲染文本通过 Rendered Message Guard")
        rendered = {"subject": rendered_subject, "body_preview": rendered_body[:240]}
        guard = {"blocked": verdict.blocked, "reason": verdict.reason,
                 "detail": verdict.detail}
    else:
        rendered = {"subject": "", "body_preview": ""}
        guard = {"blocked": True, "reason": "missing_lead", "detail": "客户不存在"}

    return {
        **base,
        "ready": not blockers,
        "blockers": blockers,
        "positives": positives,
        "template_evidence": template_evidence,
        "message_guard": guard,
        "rendered": rendered,
    }


def evaluate_batch(conn, lead_nos: list[int], *, subject: str, body: str) -> dict:
    """Preserve order and explain every removal."""
    decisions = [evaluate(conn, int(no), subject=subject, body=body) for no in lead_nos]
    accepted = [d["lead_no"] for d in decisions if d["ready"]]
    rejected = [d for d in decisions if not d["ready"]]
    return {"accepted": accepted, "decisions": decisions, "rejected": rejected}


def compact(decision: dict) -> dict:
    """Small durable audit snapshot suitable for a proposal payload."""
    return {
        "lead_no": decision.get("lead_no"),
        "score": decision.get("score"),
        "grade": decision.get("grade"),
        "ready": bool(decision.get("ready")),
        "positives": (decision.get("positives") or [])[:6],
        "blockers": (decision.get("blockers") or [])[:6],
        "template_evidence": decision.get("template_evidence") or {},
    }
