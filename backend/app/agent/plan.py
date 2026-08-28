"""The daily plan: the agent reads the state of the business and says what it would do.

The model never touches the database. It returns a list of actions, each of which is
checked here against a whitelist before becoming a proposal — unknown kind, unknown
lead, unknown sequence, out-of-range batch and made-up dates are all dropped with a
reason rather than trusted. A planner that can only emit validated proposals is a
planner whose worst day is a queue Allen rejects, not a mess he has to undo.

The division of labour with the copy matters: the model picks WHO to contact and WHY
now. It never writes cold outreach — that comes from Allen's templates, which are the
lines he actually sends.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json

from app import autosend
from app.agent import llm, mission, proposals, send_decision, world

MAX_ACTIONS = 12
MAX_BATCH_LEADS = 20          # matches channel_outreach.MAX_BATCH; never exceeded

PLANNABLE = {
    "create_task": "给某个客户排一件具体的下一步",
    "send_outreach": "用现成模板给一批没触达过的客户发第一封",
    "enroll_sequence": "把客户加进已有跟进序列",
    "stop_sequence": "停掉某客户的后续跟进",
    "discover_run": "跑一轮关键词客户开发",
    "build_opportunity": "把已经聊到具体项目的客户建成商机",
}

SYSTEM = """You plan one working day for Allen, who sells LED displays from Shenzhen to
B2B buyers worldwide. You are given the real state of his pipeline as JSON.

The `mission` object is Allen's standing instruction. `mission_progress.remaining` is
the qualified, contactable lead target still missing today. Work toward it after urgent
replies and revenue-moving tasks; never lower its quality bar.

Produce the smallest set of actions that moves the most money forward today. Fewer,
better-argued actions beat a long list. An empty plan is correct when nothing is worth
doing; say so rather than inventing work.

You may only use these action kinds:
- create_task: one concrete next step for one customer
- send_outreach: first-touch a batch of untouched accounts using an EXISTING template
- enroll_sequence: put customers into an EXISTING follow-up sequence
- stop_sequence: stop follow-ups for a customer
- discover_run: search for new candidate companies with keywords
- build_opportunity: turn a customer who described a real project into an opportunity

Rules:
- Use only lead_no, template_id and sequence_id values that appear in the input.
- Never exceed the remaining daily capacity given under `capacity`.
- If `email_safety_pause` is not null, do not propose send_outreach. Keep prospecting,
  qualifying and doing internal work; the send gate can only be resumed by Allen.
- Do not propose anything already listed in `already_pending`.
- Unhandled replies are the highest-value thing in the pipeline. If one is sitting there,
  dealing with it outranks any amount of new outreach.
- `due_followups` contains already-contacted accounts whose next step is currently owned
  by nobody else. Treat high-score overdue accounts as real pipeline work, ahead of
  filling the day with more low-value cold volume.
- `untouched.emailable_untouched` is how many contactable companies have never been
  written to. `untouched.top` is only the highest-scoring dozen — a short list there
  does NOT mean the pool is empty.
- Every row in `untouched.top` has `autonomous_send`. Prefer send_outreach only for rows
  where `autonomous_send.ready_for_template_check` is true. If nobody is ready, research,
  qualify or discover instead of forcing a low-quality send. In auto mode the backend
  independently enforces this and also checks approved case/product evidence plus the
  exact rendered message.
- `weak_campaigns` lists campaigns that reached enough people to judge and got zero
  replies. Worth saying out loud in the summary; do not silently keep feeding them.
- Think like an experienced LED-display export salesperson. Once a buyer has a real
  project, progressively establish the application/use case, indoor vs outdoor,
  physical screen dimensions, viewing distance or justified pixel pitch, environment
  and brightness requirement, quantity, destination, installation/maintenance access,
  control-system constraints and decision/timing. Never manufacture a missing fact.
- A real LED opportunity should have one explicit next action and date. If the buyer has
  not given enough technical context, the next action is to obtain the missing project
  facts, not to guess a configuration or commercial promise.
- You do NOT write outreach copy. send_outreach picks who; the template supplies what.
- You do NOT price anything. When a customer wants a quote, the only action is a task
  for Allen — never a message, never an amount, never a discount. This is absolute.
- risk: "low" for internal bookkeeping (tasks), "medium" for anything that sends a
  message or changes a customer's state, "high" if you are unsure it should happen.

Return JSON:
{"summary": "<one sentence, Chinese, what today is about>",
 "plan": [{"kind": "...", "lead_no": <int or null>, "title": "<Chinese, what to do>",
           "why": "<Chinese, why this and why now — cite the number you used>",
           "risk": "low|medium|high", "payload": {...}}]}

payload by kind:
  create_task       {"title": str, "type": "task|call|email|whatsapp|meeting|quote",
                     "due_at": "YYYY-MM-DD", "priority": "high|normal|low"}
  send_outreach     {"template_id": int, "lead_nos": [int, ...], "channel": "email"}
  enroll_sequence   {"sequence_id": int, "lead_nos": [int, ...]}
  stop_sequence     {"channel": "email|whatsapp|instagram" or null}
  discover_run      {"queries": [str, ...], "country": str or null}
  build_opportunity {"title": str, "stage": "qualified", "use_case": str or null,
                     "pixel_pitch": str or null, "indoor_outdoor": str or null}"""

_TASK_TYPES = ("task", "call", "email", "whatsapp", "instagram", "meeting", "quote")
_PRIORITIES = ("high", "normal", "low")


class Rejected(ValueError):
    """This action did not survive validation; the reason is shown in the run result."""


def _int(value, field: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        raise Rejected(f"{field} 不是整数：{value!r}") from None


def _date(value, field: str) -> str | None:
    if value in (None, ""):
        return None
    try:
        return dt.date.fromisoformat(str(value)).isoformat()
    except ValueError:
        raise Rejected(f"{field} 不是合法日期：{value!r}") from None


def _known_leads(conn, lead_nos: list, limit: int) -> list[int]:
    if not isinstance(lead_nos, list) or not lead_nos:
        raise Rejected("lead_nos 为空")
    nos = [_int(n, "lead_no") for n in lead_nos][:limit]
    rows = {r["no"] for r in conn.execute(
        f"SELECT no FROM leads WHERE no IN ({','.join('?' * len(nos))})"
        " AND COALESCE(do_not_contact,0)=0", nos)}
    known = [n for n in nos if n in rows]
    if not known:
        raise Rejected("lead_nos 里没有一个是库里可联系的客户")
    return known


def _validate(conn, action: dict) -> dict:
    """Turn one model-proposed action into arguments for proposals.create."""
    kind = str(action.get("kind") or "").strip()
    if kind not in PLANNABLE:
        raise Rejected(f"未知动作类型 {kind!r}")
    payload = action.get("payload")
    if not isinstance(payload, dict):
        raise Rejected("payload 不是对象")
    title = str(action.get("title") or "").strip()
    if not title:
        raise Rejected("没有 title")
    risk = action.get("risk") if action.get("risk") in proposals.RISKS else "medium"
    lead_no = None
    if action.get("lead_no") is not None:
        lead_no = _int(action["lead_no"], "lead_no")
        if conn.execute("SELECT 1 FROM leads WHERE no=?", (lead_no,)).fetchone() is None:
            raise Rejected(f"客户 {lead_no} 不在库里")

    if kind == "create_task":
        clean = {
            "title": str(payload.get("title") or title)[:200],
            "type": payload.get("type") if payload.get("type") in _TASK_TYPES else "task",
            "due_at": _date(payload.get("due_at"), "due_at") or dt.date.today().isoformat(),
            "priority": (payload.get("priority")
                         if payload.get("priority") in _PRIORITIES else "normal"),
        }
        if lead_no is None:
            raise Rejected("create_task 必须指定客户")
    elif kind == "send_outreach":
        pause = autosend.safety_pause(conn)
        if pause:
            raise Rejected(f"邮件开发处于安全暂停：{pause['reason']}")
        template_id = _int(payload.get("template_id"), "template_id")
        tpl = conn.execute("SELECT id, channel, COALESCE(subject,'') subject, body"
                           " FROM templates WHERE id=?", (template_id,)).fetchone()
        if tpl is None:
            raise Rejected(f"模板 {template_id} 不存在")
        if tpl["channel"] != "email":
            raise Rejected("send_outreach 只能使用 Email 模板")
        # Capacity is a hard ceiling, not a suggestion: the send path would defer the
        # overflow anyway, and a proposal promising 40 sends that delivers 12 is a lie.
        capacity = world._channel_capacity(conn)
        if not capacity["email_sendable"]:
            raise Rejected("没有可用发件邮箱，发不出去")
        room = min(capacity["email_remaining_today"], MAX_BATCH_LEADS)
        if room <= 0:
            raise Rejected("今日发送额度已用完")
        known = _known_leads(conn, payload.get("lead_nos") or [], room)
        if proposals.autonomy(conn, "send_outreach") == "auto":
            decision = send_decision.evaluate_batch(
                conn, known, subject=tpl["subject"], body=tpl["body"],
            )
            if not decision["accepted"]:
                reasons = []
                for row in decision["rejected"][:3]:
                    reason = (row.get("blockers") or ["未通过自主发送质量门槛"])[0]
                    reasons.append(f"#{row['lead_no']} {reason}")
                raise Rejected("自主发送质量门槛未通过：" + "；".join(reasons))
            clean = {
                "template_id": template_id,
                "channel": "email",
                "lead_nos": decision["accepted"],
                "autonomous_decision": {
                    "accepted": [send_decision.compact(d) for d in decision["decisions"] if d["ready"]],
                    "rejected": [send_decision.compact(d) for d in decision["rejected"]],
                },
            }
        else:
            clean = {"template_id": template_id, "channel": "email", "lead_nos": known}
    elif kind == "enroll_sequence":
        sequence_id = _int(payload.get("sequence_id"), "sequence_id")
        if conn.execute("SELECT 1 FROM sequences WHERE id=?",
                        (sequence_id,)).fetchone() is None:
            raise Rejected(f"序列 {sequence_id} 不存在")
        clean = {"sequence_id": sequence_id,
                 "lead_nos": _known_leads(conn, payload.get("lead_nos") or [],
                                          MAX_BATCH_LEADS)}
    elif kind == "stop_sequence":
        if lead_no is None:
            raise Rejected("stop_sequence 必须指定客户")
        channel = payload.get("channel")
        clean = {"channel": channel if channel in ("email", "whatsapp", "instagram") else None}
    elif kind == "discover_run":
        queries = [str(q).strip() for q in (payload.get("queries") or []) if str(q).strip()]
        if not queries:
            raise Rejected("discover_run 没有关键词")
        clean = {"queries": queries[:6], "country": payload.get("country") or None}
    else:  # build_opportunity
        if lead_no is None:
            raise Rejected("build_opportunity 必须指定客户")
        clean = {"title": str(payload.get("title") or title)[:200], "stage": "qualified"}
        for field in ("use_case", "pixel_pitch", "indoor_outdoor"):
            if payload.get(field):
                clean[field] = str(payload[field])[:80]

    return {"kind": kind, "lead_no": lead_no, "title": title[:200],
            "reasoning": str(action.get("why") or "")[:600], "risk": risk,
            "payload": clean}


def build_mission_fallback(conn, state: dict | None = None,
                           backend: str = "deterministic") -> dict:
    """Keep the core acquisition mission moving without inventing model output."""
    proposals.ensure_schema(conn)
    state = state or world.build(conn)
    action = mission.fallback_discovery(conn, state)
    if not action:
        return {"proposed": 0, "ids": [], "rejected": []}
    try:
        clean = _validate(conn, action)
    except Rejected as exc:
        return {"proposed": 0, "ids": [], "rejected": [f"mission fallback: {exc}"]}
    proposal = proposals.create(
        conn, clean["kind"], lead_no=clean["lead_no"], title=clean["title"],
        reasoning=clean["reasoning"], payload=clean["payload"], risk=clean["risk"],
        evidence=[{"claim": "销售任务书兜底",
                   "source": f"{state['today']} 目标与进度"}],
        backend=backend,
        dedupe_key=f"mission-{state['today']}-{clean['payload'].get('country')}")
    ids = [proposal["id"]] if proposal else []
    return {"proposed": len(ids), "ids": ids, "rejected": []}


def _dedupe_key(today: str, clean: dict) -> str:
    """Stable idempotency without collapsing different same-day batches.

    Proposal fingerprints already include kind and lead_no. Batch actions normally have
    no lead_no, however, so a key containing only the date made two different outreach
    or enrollment batches of the same kind collide. Use the validated payload as part
    of the key: exact repeats still collapse, genuinely different work does not.
    """
    if clean["kind"] == "discover_run":
        return f"plan-{today}-discover-{clean['payload'].get('country') or 'any'}"
    raw = json.dumps({"lead_no": clean["lead_no"], "payload": clean["payload"]},
                     ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"plan-{today}-{digest}"


def build_plan(conn) -> dict:
    """Ask for today's plan and turn what survives validation into proposals."""
    proposals.ensure_schema(conn)
    state = world.build(conn)
    data = llm.complete_json(conn, "draft", SYSTEM,
                             json.dumps(state, ensure_ascii=False, default=str))
    actions = data.get("plan")
    if not isinstance(actions, list):
        raise llm.LLMError("计划不是一个列表")
    made, rejected, duplicates = [], [], []
    backend = data.get("_llm_backend") or llm.backend_for(conn, "draft")
    if len(actions) > MAX_ACTIONS:
        # Say so rather than truncating quietly: a plan of forty items is a signal that
        # the planner misread the day, and Allen should see that it happened.
        rejected.append(f"计划超长（{len(actions)} 条），只取前 {MAX_ACTIONS} 条")
        actions = actions[:MAX_ACTIONS]
    for action in actions:
        try:
            clean = _validate(conn, action)
        except Rejected as exc:
            rejected.append(f"{action.get('kind', '?')}: {exc}")
            continue
        p = proposals.create(
            conn, clean["kind"], lead_no=clean["lead_no"], title=clean["title"],
            reasoning=clean["reasoning"], payload=clean["payload"], risk=clean["risk"],
            evidence=[{"claim": "今日计划", "source": f"{state['today']} 管道状态"}],
            backend=backend, dedupe_key=_dedupe_key(state["today"], clean))
        if p:
            made.append(p["id"])
        else:
            # A repeat is not a failure, but it is not nothing either: 'proposed 0'
            # with no explanation is why a planned day looked like a dead button.
            duplicates.append(clean["title"])
    # Fallback is for a genuinely empty model plan, not a malformed one. If the model
    # attempted unsafe/unknown work, keep the rejection visible instead of disguising
    # that planning defect as a successful discovery action.
    if not made and not actions:
        fallback = build_mission_fallback(conn, state, backend)
        made.extend(fallback["ids"])
        rejected.extend(fallback["rejected"])
    return {"summary": str(data.get("summary") or "").strip(),
            "proposed": len(made), "rejected": rejected,
            "duplicates": duplicates, "considered": len(actions)}