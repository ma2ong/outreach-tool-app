"""What an approved proposal actually does.

Every handler delegates to the module that already owns the action, so agent-initiated
work inherits the same guards as work Allen does by hand. Handlers return a short human
sentence that lands in `execution_result` — the Agent page shows it verbatim, so it has
to read like an answer to "what happened", not like a status code.

Kinds without a handler here fail loudly rather than silently doing nothing.
"""
from __future__ import annotations

import datetime as dt

from app import activities, autosend, delivery_intents, mailboxes, opportunities, repository
from app.channels import email_adapter


class ExecutionRefused(RuntimeError):
    """A guard said no. The proposal fails with this reason shown to Allen."""


def _lead(conn, lead_no: int) -> dict:
    row = conn.execute(
        "SELECT no, company_en, do_not_contact FROM leads WHERE no=?", (lead_no,)).fetchone()
    if row is None:
        raise ExecutionRefused(f"客户 {lead_no} 不存在")
    return dict(row)


def _pick_mailbox(conn, preferred_email: str | None):
    """Answer from the address the customer wrote to. Falls back to rotation only when
    that mailbox is gone, because a reply from an unrelated address is worse than none."""
    if preferred_email:
        row = conn.execute(
            "SELECT id, email, smtp_host, port, username, password FROM mailboxes"
            " WHERE email=? AND active=1", (preferred_email,)).fetchone()
        if row:
            return dict(row)
    box = mailboxes.pick_mailbox(conn)
    if box is None:
        raise ExecutionRefused("没有可用发件邮箱（全部停用或已达当日上限）")
    return box


def _mark_handled(conn, p: dict) -> None:
    if p.get("inbox_message_id"):
        conn.execute("UPDATE inbox_messages SET handled_at=?, is_read=1 WHERE id=?",
                     (dt.datetime.now(dt.UTC).isoformat(), p["inbox_message_id"]))


def _reply_claim(conn, p: dict, *, channel: str, target: str, subject: str | None,
                 body: str, metadata: dict | None = None) -> int:
    proposal_id = int(p.get("id") or 0)
    if not proposal_id:
        raise ExecutionRefused("回复缺少可审计的提议编号，未发送")
    intent_id = delivery_intents.claim_action(
        conn,
        operation_key=f"reply:{proposal_id}", source_kind="reply", source_id=proposal_id,
        lead_no=p["lead_no"], channel=channel, target=target, subject=subject, body=body,
        metadata={"inbox_message_id": p.get("inbox_message_id"), **(metadata or {})},
    )
    if intent_id is None:
        raise ExecutionRefused("这条回复已有发送记录，请先在运行状态中核对结果，勿重复发送")
    return intent_id


def _mark_reply_unknown(conn, intent_id: int, exc: Exception) -> None:
    conn.rollback()
    try:
        delivery_intents.finish(conn, intent_id, error=exc)
    except Exception:  # noqa: BLE001 — committed pending claim still prevents a retry
        conn.rollback()


def send_dm_reply(conn, p: dict, channel: str) -> str:
    """Answer in the chat the customer wrote in.

    Deliberately not `channel_outreach.send_channel_campaign`: that path is for cold
    outreach and its eligibility filter excludes leads who have already replied — which
    is every single person we would be answering here. The guards that do apply to a
    reply (do-not-contact, a real handle) are checked directly.
    """
    from app.agent import social
    from app.api.channels import ENGINE
    body = (p.get("payload") or {}).get("body", "").strip()
    if not body:
        raise ExecutionRefused("回复正文为空")
    target = social.target_for(conn, p["lead_no"], channel)
    intent_id = _reply_claim(
        conn, p, channel=channel, target=target, subject=None, body=body)
    # No case image on a reply. The always-attach rule exists for cold DMs that open a
    # conversation; re-sending the poster to someone mid-conversation reads as a bot.
    try:
        ENGINE.send_message(channel, target, body, None)
        _mark_handled(conn, p)
        from app.agent import conversation
        conversation.record_sent_reply(
            conn, p["lead_no"], channel, p.get("inbox_message_id"),
            (p.get("payload") or {}).get("open_questions") or "",
            is_followup=(p.get("payload") or {}).get("followup_kind") == "warm")
        repository.add_note(conn, p["lead_no"],
                            f"{channel} 回复（Agent 起草，已确认发送）：{body[:300]}")
        conn.commit()
        delivery_intents.finish(conn, intent_id)
    except Exception as exc:
        _mark_reply_unknown(conn, intent_id, exc)
        raise
    return f"已在 {channel} 回复 {target}"


def send_reply(conn, p: dict) -> str:
    payload = p.get("payload") or {}
    lead = _lead(conn, p["lead_no"])
    if lead["do_not_contact"]:
        raise ExecutionRefused("该客户已标记不再联系")
    channel = payload.get("channel") or "email"
    from app.agent import conversation
    state = conversation.get(conn, p["lead_no"], channel)
    if state and state["owner"] == "allen":
        raise ExecutionRefused("该会话已由 Allen 接管；明确交回 Agent 后才能发送草稿")
    if channel != "email":
        return send_dm_reply(conn, p, channel)
    to = (payload.get("to") or "").strip()
    body = (payload.get("body") or "").strip()
    if not to or "@" not in to:
        raise ExecutionRefused("收件地址缺失")
    if not body:
        raise ExecutionRefused("回复正文为空")
    subject = (payload.get("subject") or "").strip() or "Re:"
    box = _pick_mailbox(conn, payload.get("mailbox_email"))
    intent_id = _reply_claim(
        conn, p, channel=channel, target=to, subject=subject, body=body,
        metadata={"mailbox_id": box.get("id")},
    )
    try:
        email_adapter.send_via(box, to, subject, body, payload.get("attachment"))
        if box.get("id"):
            mailboxes.record_send(conn, box["id"])
            delivery_intents.update_metadata(conn, intent_id, mailbox_counted=True)
        _mark_handled(conn, p)
        conversation.record_sent_reply(
            conn, p["lead_no"], channel, p.get("inbox_message_id"),
            payload.get("open_questions") or "",
            is_followup=payload.get("followup_kind") == "warm")
        repository.add_note(conn, p["lead_no"], f"回复 {to}（Agent 起草，已确认发送）：{body[:300]}")
        conn.commit()
        delivery_intents.finish(conn, intent_id)
    except Exception as exc:
        _mark_reply_unknown(conn, intent_id, exc)
        raise
    return f"已从 {box['email']} 回复 {to}"


def create_task(conn, p: dict) -> str:
    payload = p.get("payload") or {}
    # One open agent task per customer. The planner dedupes within a day, so the same
    # unfinished job came back as a fresh task every morning: 89 open items, the same
    # sentence three times over. An agent that wakes itself up has nothing new to say
    # about a customer until the last thing it asked for is done — and Allen's
    # attention is the thing being spent. A task he created himself does not count:
    # it is his note, not the agent's standing request.
    activities.ensure_schema(conn)
    standing = conn.execute(
        "SELECT id, title FROM activities WHERE lead_no=? AND status='open'"
        " AND source='agent' ORDER BY id LIMIT 1", (p["lead_no"],)).fetchone()
    if standing:
        return f"该客户已有未完成任务 #{standing['id']}：{standing['title']}，不重复建"
    task = activities.create(conn, p["lead_no"], {
        "title": payload.get("title") or p["title"],
        "type": payload.get("type") or "task",
        "due_at": payload.get("due_at"),
        "priority": payload.get("priority") or "normal",
        "note": payload.get("note"),
    }, opportunity_id=p.get("opportunity_id"))
    # Record where it came from now, at the moment it is created. Until this, an agent
    # task was indistinguishable from one Allen typed, and ownership had to be inferred
    # afterwards by parsing the executor's own result string back out of the proposal.
    if p.get("id"):
        conn.execute(
            "UPDATE activities SET source='agent', source_ref=? WHERE id=?",
            (f"proposal:{p['id']}", task["id"]))
        conn.commit()
    return f"已建销售任务 #{task['id']}：{task['title']}"


def build_opportunity(conn, p: dict) -> str:
    payload = dict(p.get("payload") or {})
    payload.pop("lead_no", None)
    opp = opportunities.create(conn, p["lead_no"], payload)
    return f"已建商机 #{opp['id']}：{opp.get('title') or ''}".strip()


def mark_do_not_contact(conn, p: dict) -> str:
    lead = _lead(conn, p["lead_no"])
    repository.update_lead(conn, p["lead_no"], {"do_not_contact": 1})
    reason = (p.get("payload") or {}).get("reason") or "客户明确拒绝"
    repository.add_note(conn, p["lead_no"], f"标记不再联系（Agent 提议，已确认）：{reason}")
    conn.commit()
    return f"{lead['company_en']} 已标记不再联系，全渠道停发"


def _persist_autonomous_recheck(conn, p: dict, payload: dict, decision: dict) -> None:
    """Keep the execution-time decision even if it refuses the send."""
    import json
    from app.agent import send_decision

    payload = dict(payload)
    payload["execution_recheck"] = {
        "accepted": [send_decision.compact(d) for d in decision["decisions"] if d["ready"]],
        "rejected": [send_decision.compact(d) for d in decision["rejected"]],
    }
    conn.execute("UPDATE agent_proposals SET payload=?, updated_at=? WHERE id=?",
                 (json.dumps(payload, ensure_ascii=False),
                  dt.datetime.now(dt.UTC).isoformat(), p["id"]))
    conn.commit()


def send_outreach(conn, p: dict) -> str:
    """First-touch a batch using one of Allen's templates.

    Goes through `outreach.send_campaign`, which is the same call the Outreach panel
    makes — so the batch cap, the daily quota, the one-touch-per-lead-per-day rule and
    the invalid-address skip all apply, and anything over budget is deferred rather than
    dropped. The Agent's auto mode additionally rechecks whether each account is still
    worth contacting now; manual approval remains the human timing override.
    """
    pause = autosend.safety_pause(conn)
    if pause:
        raise ExecutionRefused(f"邮件开发处于安全暂停：{pause['reason']}")

    from app import outreach
    from app.api import send as send_api
    payload = p.get("payload") or {}
    tpl = conn.execute("SELECT subject, body, channel FROM templates WHERE id=?",
                       (payload.get("template_id"),)).fetchone()
    if tpl is None:
        raise ExecutionRefused("模板已被删除")
    if tpl["channel"] != "email":
        raise ExecutionRefused("目前只支持邮件模板的批量触达；社媒批量仍走手动面板")
    lead_nos = [int(n) for n in payload.get("lead_nos") or []]
    if not lead_nos:
        raise ExecutionRefused("没有选中客户")

    late_removed = 0
    if p.get("execution_mode") == "auto":
        from app.agent import send_decision
        decision = send_decision.evaluate_batch(
            conn, lead_nos, subject=tpl["subject"] or "", body=tpl["body"],
        )
        _persist_autonomous_recheck(conn, p, payload, decision)
        late_removed = len(lead_nos) - len(decision["accepted"])
        lead_nos = decision["accepted"]
        if not lead_nos:
            reason = (decision["rejected"][0].get("blockers") or
                      ["当前已不满足自主发送质量门槛"])[0]
            raise ExecutionRefused(f"执行前复检停止发送：{reason}")

    result = outreach.send_campaign(
        conn, lead_nos, tpl["subject"] or "", tpl["body"],
        send_api.DEFAULT_ATTACHMENT, send_api.pick_sender(conn),
        campaign=f"Agent {dt.date.today().isoformat()}")
    note = f"已发 {result['sent']} 封，失败 {result['failed']}"
    if late_removed:
        note += f"，执行前质量复检移除 {late_removed} 家"
    if result.get("held"):
        note += f"，最终文本安全拦下 {result['held']} 家"
    if result.get("deferred"):
        note += f"，额度外延后 {result['deferred']}（明天继续）"
    if result.get("skipped"):
        note += f"，跳过 {result['skipped']}（不符合发送条件）"
    return note


def enroll_sequence(conn, p: dict) -> str:
    from app import sequences
    payload = p.get("payload") or {}
    lead_nos = [int(n) for n in payload.get("lead_nos") or []]
    if not lead_nos:
        raise ExecutionRefused("没有选中客户")
    count = sequences.enroll_leads(conn, int(payload["sequence_id"]), lead_nos)
    return f"已把 {count} 个客户加入跟进序列"


def stop_sequence(conn, p: dict) -> str:
    from app import sequences
    channel = (p.get("payload") or {}).get("channel")
    stopped = sequences.stop_for_lead(conn, p["lead_no"], channel)
    return f"已停掉 {stopped} 条跟进" if stopped else "该客户本来就没有进行中的跟进"


def _sequence_for(conn, lead: dict) -> int | None:
    """Route from durable rules; defaults preserve the old language/segment behavior."""
    from app.seed_sequences import ensure_routing_columns
    from app import sequence_routing

    ensure_routing_columns(conn)
    return sequence_routing.route(conn, lead)


def _enroll_imported(conn, lead_nos: list[int]) -> tuple[int, list[str]]:
    from app import sequences

    if not lead_nos:
        return 0, []
    placeholders = ",".join("?" * len(lead_nos))
    rows = conn.execute(
        f"SELECT no, country, tags, target_fit, business, hook, brief FROM leads"
        f" WHERE no IN ({placeholders})"
        " AND COALESCE(email_status,'') != 'invalid'", lead_nos).fetchall()
    # Grouped by the sequence each lead belongs in, so one enrol call covers each.
    groups: dict[int | None, list[int]] = {}
    for row in rows:
        groups.setdefault(_sequence_for(conn, dict(row)), []).append(row["no"])
    enrolled = 0
    missing: list[str] = []
    for sequence_id, nos in groups.items():
        if sequence_id is None:
            missing.append(f"没有可用的邮件序列（{len(nos)} 家）")
            continue
        enrolled += sequences.enroll_leads(conn, sequence_id, nos)
    return enrolled, missing


def _import_skip_reason(skipped: dict) -> str:
    if skipped.get("duplicate_of"):
        return f"重复客户：#{skipped['duplicate_of']}"
    if skipped.get("blocked_domain"):
        return f"域名在永久排除名单：{skipped['blocked_domain']}"
    return "导入时被安全规则跳过"


def discover_run(conn, p: dict) -> str:
    """Search and preserve every candidate; auto-import only in autonomous mode.

    A manually approved search retains the checkbox review flow. An autonomous search
    may close the loop, but only through the shared strict qualification/import path,
    email verification and an existing language-matched sequence.
    """
    import json

    from app import discovery
    payload = dict(p.get("payload") or {})
    queries = payload.get("queries") or []
    country = payload.get("country")
    found: list[dict] = []
    seen: set[str] = set()
    def persist_progress(progress: dict) -> None:
        payload["progress"] = progress
        conn.execute("UPDATE agent_proposals SET payload=? WHERE id=?",
                     (json.dumps(payload, ensure_ascii=False), p["id"]))
        conn.commit()

    for query_index, query in enumerate(queries, 1):
        text = f"{query} {country}".strip() if country else query
        persist_progress({"status": "searching", "query": query,
                          "query_index": query_index, "query_total": len(queries),
                          "done": 0, "total": 0, "candidates": len(found)})

        def on_progress(done: int, total: int) -> None:
            persist_progress({"status": "enriching", "query": query,
                              "query_index": query_index, "query_total": len(queries),
                              "done": done, "total": total, "candidates": len(found)})

        for cand in discovery.run_discovery(
                conn, text, limit=10, on_progress=on_progress) or []:
            # Deduplicate on `domain`, the same key /api/discover uses. Candidates carry
            # `domain` and `title`; `company_en` and `website` are only filled in later,
            # at import — keying on those dropped every single result.
            key = (cand.get("domain") or "").lower()
            if key and key not in seen:
                seen.add(key)
                found.append(cand)
    payload["progress"] = {"status": "complete", "query_index": len(queries),
                           "query_total": len(queries), "candidates": len(found)}
    payload["found"] = found
    conn.execute("UPDATE agent_proposals SET payload=? WHERE id=?",
                 (json.dumps(payload, ensure_ascii=False), p["id"]))
    conn.commit()
    usable = [c for c in found if not c.get("excluded")]
    if p.get("execution_mode") != "auto":
        return (f"已搜到 {len(found)} 个候选（其中 {len(usable)} 个可用），"
                "就在这条提议里，展开勾选导入（不会自动入库）")

    from app import verify
    from app.agent import mission

    assignment = mission.get(conn)
    accepted, rejected = discovery.qualify_for_auto_import(
        found, assignment["minimum_fit_score"], email_classifier=verify.classify_email,
        target_country=country)
    imported = discovery.import_candidates(conn, accepted, country)
    for skipped in imported["skipped"]:
        rejected.append({
            "domain": skipped.get("website") or skipped.get("company_en") or "",
            "reason": _import_skip_reason(skipped),
        })
    lead_nos = imported["imported_lead_nos"]
    verification = verify.verify_leads(conn, lead_nos) if lead_nos else {"checked": 0}
    enrolled, missing = (0, [])
    if assignment["auto_enroll"]:
        enrolled, missing = _enroll_imported(conn, lead_nos)
    payload["auto_import"] = {
        "accepted": len(accepted),
        "imported": imported["imported"],
        "imported_lead_nos": lead_nos,
        "rejected": rejected,
        "verification": verification,
        "enrolled": enrolled,
        "missing_sequences": missing,
    }
    conn.execute("UPDATE agent_proposals SET payload=? WHERE id=?",
                 (json.dumps(payload, ensure_ascii=False), p["id"]))
    conn.commit()
    note = (f"已搜到 {len(found)} 个候选，自动导入 {imported['imported']} 家，"
            f"验证 {verification.get('checked', 0)} 个邮箱，加入序列 {enrolled} 家")
    if rejected:
        note += f"，{len(rejected)} 个未通过质量门"
    if missing:
        note += "；缺少" + "、".join(missing)
    return note


def reschedule_work(conn, p: dict) -> str:
    """Move work Allen did not schedule (docs/88 R1).

    The agent sets its own due dates — 579 of the open tasks carry one nobody chose —
    and until now no screen could change them. Nothing here leaves the tool: it edits a
    due date, a priority or cancels, so the risk is a day of work reordered, not a letter.
    """
    payload = dict(p.get("payload") or {})
    ids = [int(i) for i in payload.get("activity_ids") or []]
    if not ids:
        return "没有要改的任务"
    patch: dict = {}
    for field in ("due_at", "priority", "status"):
        if payload.get(field):
            patch[field] = payload[field]
    if not patch:
        return "没有要改的字段"
    changed = 0
    for activity_id in ids:
        if activities.update(conn, activity_id, dict(patch)):
            changed += 1
    conn.commit()
    what = "、".join(f"{k}={v}" for k, v in patch.items())
    return f"{changed} 条任务已改：{what}"


HANDLERS = {
    "reply_draft": send_reply,
    "reschedule_work": reschedule_work,
    "create_task": create_task,
    "build_opportunity": build_opportunity,
    "mark_do_not_contact": mark_do_not_contact,
    "send_outreach": send_outreach,
    "enroll_sequence": enroll_sequence,
    "stop_sequence": stop_sequence,
    "discover_run": discover_run,
}
