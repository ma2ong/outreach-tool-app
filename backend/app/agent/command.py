"""One sentence in, one proposed action out (docs/88).

The tool has fourteen entries organised by object — leads, sequences, inbox, tasks. A
thought is not organised that way: "把没发过信的排 100 封今天发" is one sentence that
touches three of those screens, and 579 of the open tasks carry a due date the agent set
for itself that no screen can change at all.

Three things keep this from becoming a second, unguarded execution path:

* the model may only choose from a written-down list (R1) — it never names a function,
  writes code or edits configuration;
* every write becomes a `pending` proposal even when that kind's dial is on `auto`
  (R2) — the dial was set for code paths, not for a sentence someone typed;
* below the confidence line, or missing an argument, it asks instead of guessing (R3).
"""
from __future__ import annotations

import datetime as dt
import json
import sqlite3

from app import activities, outreach as email_outreach, settings
from app.agent import control_center, llm, proposals

# R1. The whole vocabulary. Anything outside it is refused, not approximated.
READ_ACTIONS = ("today", "stuck", "lead", "why")
WRITE_ACTIONS = ("create_task", "enroll_sequence", "stop_sequence", "discover_run",
                 "mark_do_not_contact", "send_outreach", "reply_draft", "reschedule_work")
ACTIONS = READ_ACTIONS + WRITE_ACTIONS

# Below this the answer is a question, never an action (R3).
MIN_CONFIDENCE = 0.6
# What a single sentence may touch before it has to be said again, smaller.
MAX_LEADS_PER_COMMAND = 200

SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    said TEXT NOT NULL,
    action TEXT NOT NULL,
    args TEXT NOT NULL DEFAULT '{}',
    confidence REAL NOT NULL DEFAULT 0,
    outcome TEXT NOT NULL,
    answer TEXT NOT NULL DEFAULT '',
    proposal_id INTEGER,
    backend TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_agent_commands_said ON agent_commands(said);
"""

_SYSTEM = """你把一句中文销售指令翻译成一个动作。只输出 JSON，不要解释。

只读动作（回答问题，不改任何东西）：
  today   今天的情况、发了多少、卡了多少
  stuck   哪里卡住了、哪个渠道没产出
  lead    某一家客户现在怎么样（args.query 填公司名或国家）
  why     某条提议或任务为什么在那里（args.query 填线索）

写入动作（会生成一条待确认的提议）：
  send_outreach       给一批客户发开发信（args.market 国家、args.limit 数量）
  enroll_sequence     把客户加进跟进序列（args.market、args.limit）
  stop_sequence       停掉某批客户的跟进（args.market、args.limit）
  discover_run        去网上找新客户（args.market、args.limit）
  create_task         建一条待办（args.title、args.market）
  mark_do_not_contact 标记某客户不再联系（args.query）
  reply_draft         给某条回复起草回信（args.query）
  reschedule_work     改任务的到期日或优先级
                      （args.due_at=YYYY-MM-DD 或 today、args.priority、args.scope 任务关键词）

规则：
1. 只能从上面的动作里选一个。做不到的事（写代码、改配置、报价、定折扣、改交期）
   一律输出 action="none"，并在 question 里说明你不做这件事。
2. 听不懂、指代不明、缺少必要参数（比如没说哪个市场、没说改到哪天），
   输出 action="ask"，question 写你要问的那一句，不要自己填默认值。
3. confidence 是 0 到 1 的小数，表示你有多确定理解对了。

输出格式：
{"action": "...", "args": {...}, "confidence": 0.0, "question": ""}"""


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def _record(conn, said: str, parsed: dict, outcome: str, answer: str,
            proposal_id: int | None, backend: str = "") -> int:
    ensure_schema(conn)
    cur = conn.execute(
        "INSERT INTO agent_commands(said, action, args, confidence, outcome, answer,"
        " proposal_id, backend, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (said, str(parsed.get("action") or "none"),
         json.dumps(parsed.get("args") or {}, ensure_ascii=False),
         float(parsed.get("confidence") or 0), outcome, answer, proposal_id,
         backend, _now()))
    conn.commit()
    return cur.lastrowid


def times_said(conn, said: str) -> int:
    """How often this exact sentence has been typed (R5).

    The count is the whole point of the ledger: a sentence on its third outing is a rule
    waiting to be written down, not a thing to keep typing.
    """
    ensure_schema(conn)
    row = conn.execute("SELECT COUNT(*) FROM agent_commands WHERE said = ?",
                       (said.strip(),)).fetchone()
    return int(row[0]) if row else 0


def history(conn, limit: int = 20) -> list[dict]:
    ensure_schema(conn)
    rows = conn.execute(
        "SELECT c.*, (SELECT COUNT(*) FROM agent_commands d WHERE d.said = c.said) times"
        " FROM agent_commands c ORDER BY c.id DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for r in rows:
        item = dict(r)
        try:
            item["args"] = json.loads(item.get("args") or "{}")
        except (TypeError, ValueError):
            item["args"] = {}
        out.append(item)
    return out


def interpret(conn, said: str) -> dict:
    """Map one sentence onto the whitelist. Never raises for a bad answer — an
    unparseable reply is the same as not understanding, which is a question (R3)."""
    try:
        raw = llm.complete_json(conn, "classify", _SYSTEM, said.strip(), timeout=60)
    except Exception as exc:  # noqa: BLE001 — LLMUnavailable / LLMError / bad JSON alike
        return {"action": "ask", "args": {}, "confidence": 0.0,
                "question": f"我现在读不懂这句话（{type(exc).__name__}），你可以换一句更直接的说法。"}
    action = str(raw.get("action") or "none").strip()
    if action not in ACTIONS and action not in ("ask", "none"):
        action = "none"
    try:
        confidence = float(raw.get("confidence") or 0)
    except (TypeError, ValueError):
        confidence = 0.0
    args = raw.get("args")
    return {"action": action, "args": args if isinstance(args, dict) else {},
            "confidence": max(0.0, min(1.0, confidence)),
            "question": str(raw.get("question") or "").strip()}


# ------------------------------------------------------------------ read answers

def _read_today(conn) -> dict:
    counters = control_center.snapshot(conn).get("counters", {})
    stats = activities.stats(conn)
    lines = [
        {"k": "今天已发",
         "v": f"{email_outreach.sent_today(conn)} 封，还剩 "
              f"{email_outreach.remaining_today(conn)} 封额度"},
        {"k": "最近一次运行",
         "v": settings.get(conn, "autosend_last_result", "") or "今天还没跑过自动发送"},
        {"k": "开放任务",
         "v": f"{stats.get('open_count', 0)} 条，其中 {stats.get('overdue', 0)} 条逾期"},
        {"k": "待确认提议", "v": f"{counters.get('awaiting_approval', 0)} 条"},
        {"k": "未分类回复", "v": f"{counters.get('unclassified_replies', 0)} 条"},
    ]
    return {"title": "今天到现在", "lines": lines}


def _read_stuck(conn) -> dict:
    """docs/86 R2 already decides what counts as stuck. Read it, do not re-derive it."""
    blockers = control_center.snapshot(conn).get("blockers", [])
    lines = [{"k": b.get("severity", ""), "v": f"{b.get('title', '')} —— {b.get('detail', '')}"}
             for b in blockers]
    if not lines:
        stats = activities.stats(conn)
        lines.append({"k": "没有阻塞", "v": f"{stats.get('overdue', 0)} 条任务已经过了到期日"})
    return {"title": "现在卡在哪", "lines": lines}


def _read_lead(conn, query: str) -> dict:
    if not query:
        return {"title": "要查哪一家？", "lines": [], "ask": "告诉我公司名或国家。"}
    rows = conn.execute(
        "SELECT no, company_en, country, stage, follow_up_date FROM leads"
        " WHERE company_en LIKE ? OR company_local LIKE ? OR country LIKE ?"
        " ORDER BY no LIMIT 6",
        (f"%{query}%", f"%{query}%", f"%{query}%")).fetchall()
    if not rows:
        return {"title": f"没找到「{query}」", "lines": []}
    lines = [{"k": f"#{r['no']} {r['company_en'] or ''}".strip(),
              "v": f"{r['country'] or '—'} · 阶段 {r['stage'] or '未定'}"} for r in rows]
    return {"title": f"「{query}」匹配到 {len(rows)} 家", "lines": lines}


def _read_why(conn, query: str) -> dict:
    rows = conn.execute(
        "SELECT kind, title, reasoning, status FROM agent_proposals"
        " WHERE title LIKE ? ORDER BY id DESC LIMIT 5", (f"%{query}%",)).fetchall()
    if not rows:
        return {"title": "没有对得上的提议", "lines": []}
    return {"title": f"「{query}」相关的提议", "lines": [
        {"k": r["kind"], "v": f"{r['title']} —— {r['reasoning'] or '没有写理由'}"} for r in rows]}


def answer_read(conn, action: str, args: dict) -> dict:
    query = str(args.get("query") or args.get("market") or "").strip()
    if action == "today":
        return _read_today(conn)
    if action == "stuck":
        return _read_stuck(conn)
    if action == "lead":
        return _read_lead(conn, query)
    return _read_why(conn, query)


# ------------------------------------------------------------------ write actions

def _leads_for(conn, args: dict, *, needs_email: bool = True) -> list[int]:
    """Stopping a sequence is not sending one: a company with no address can still be
    the thing being stopped, so only the sending actions require one."""
    market = str(args.get("market") or "").strip()
    sql = "SELECT no FROM leads WHERE COALESCE(do_not_contact,0)=0"
    if needs_email:
        sql += " AND COALESCE(email,'')<>''"
    params: list = []
    if market:
        sql += " AND (country LIKE ? OR region LIKE ?)"
        params += [f"%{market}%", f"%{market}%"]
    sql += " ORDER BY no LIMIT ?"
    params.append(_limit(args))
    return [r["no"] for r in conn.execute(sql, params)]


def _limit(args: dict) -> int:
    try:
        value = int(args.get("limit") or 0)
    except (TypeError, ValueError):
        value = 0
    if value <= 0:
        value = 20
    return min(value, MAX_LEADS_PER_COMMAND)


def _due_date(value: str) -> str | None:
    text = str(value or "").strip().lower()
    if text in ("today", "今天", "now"):
        return dt.date.today().isoformat()
    if text in ("tomorrow", "明天"):
        return (dt.date.today() + dt.timedelta(days=1)).isoformat()
    try:
        return dt.date.fromisoformat(text).isoformat()
    except ValueError:
        return None


def _tasks_for(conn, args: dict) -> list[dict]:
    scope = str(args.get("scope") or "").strip()
    sql = "SELECT id, title FROM activities WHERE status='open'"
    params: list = []
    if scope:
        sql += " AND title LIKE ?"
        params.append(f"%{scope}%")
    sql += " ORDER BY due_at LIMIT ?"
    params.append(MAX_LEADS_PER_COMMAND * 5)
    return [dict(r) for r in conn.execute(sql, params)]


def plan_write(conn, action: str, args: dict) -> dict:
    """Turn a parsed action into the exact thing that would happen — including how many
    companies it touches, which R4 requires be on screen before anyone can press it."""
    if action == "reschedule_work":
        due = _due_date(args.get("due_at") or "")
        priority = str(args.get("priority") or "").strip()
        if not due and priority not in activities.PRIORITIES:
            return {"ask": "改到哪一天？（或者告诉我改成什么优先级）"}
        tasks = _tasks_for(conn, args)
        if not tasks:
            return {"ask": "没有匹配的开放任务。你指的是哪一批？"}
        payload = {"activity_ids": [t["id"] for t in tasks]}
        if due:
            payload["due_at"] = due
        if priority in activities.PRIORITIES:
            payload["priority"] = priority
        what = f"到期日改成 {due}" if due else f"优先级改成 {priority}"
        return {
            "payload": payload, "risk": "low",
            "title": f"把 {len(tasks)} 条任务的{what}",
            "impact": [("动作类型", "reschedule_work"), ("影响任务", f"{len(tasks)} 条"),
                       ("改成", due or priority), ("对外发送", "无")],
        }

    if action in ("send_outreach", "enroll_sequence", "stop_sequence"):
        if not str(args.get("market") or "").strip():
            return {"ask": "哪个市场？（比如韩国、美国，或者说「全部」）"}
        lead_nos = _leads_for(conn, args, needs_email=action != "stop_sequence")
        if not lead_nos:
            return {"ask": "这个条件下没有匹配的客户。换个说法？"}
        market = args.get("market")
        verb = {"send_outreach": "发开发信", "enroll_sequence": "加进跟进序列",
                "stop_sequence": "停掉跟进"}[action]
        impact = [("动作类型", action), ("影响客户", f"{len(lead_nos)} 家"),
                  ("市场", market)]
        if action != "stop_sequence":
            impact.append(("今日已发", f"{email_outreach.sent_today(conn)} 封"))
            impact.append(("今日剩余额度", f"{email_outreach.remaining_today(conn)} 封"))
        return {
            "payload": {"lead_nos": lead_nos, "market": market},
            "risk": "high" if action == "send_outreach" else "medium",
            "title": f"给 {market} 的 {len(lead_nos)} 家客户{verb}",
            "impact": impact,
        }

    if action == "discover_run":
        market = str(args.get("market") or "").strip()
        if not market:
            return {"ask": "去哪个市场找？"}
        limit = _limit(args)
        return {"payload": {"market": market, "limit": limit}, "risk": "medium",
                "title": f"到 {market} 找 {limit} 家新客户",
                "impact": [("动作类型", "discover_run"), ("市场", market),
                           ("目标数量", f"{limit} 家"), ("对外发送", "无")]}

    if action == "create_task":
        title = str(args.get("title") or "").strip()
        if not title:
            return {"ask": "这条待办写什么？"}
        return {"payload": {"title": title, "type": "task"}, "risk": "low",
                "title": f"建一条待办：{title}",
                "impact": [("动作类型", "create_task"), ("对外发送", "无")]}

    query = str(args.get("query") or "").strip()
    if not query:
        return {"ask": "指哪一家客户？"}
    row = conn.execute(
        "SELECT no, company_en FROM leads WHERE company_en LIKE ? ORDER BY no LIMIT 2",
        (f"%{query}%",)).fetchall()
    if not row:
        return {"ask": f"没找到「{query}」这家客户。"}
    if len(row) > 1:
        names = "、".join(str(r["company_en"]) for r in row)
        return {"ask": f"不确定你说的是哪一家：{names}"}
    lead_no = row[0]["no"]
    label = {"mark_do_not_contact": "标记不再联系", "reply_draft": "起草回信"}[action]
    return {"payload": {"lead_no": lead_no}, "lead_no": lead_no, "risk": "medium",
            "title": f"{row[0]['company_en']}：{label}",
            "impact": [("动作类型", action), ("客户", str(row[0]["company_en"])),
                       ("影响客户", "1 家")]}


def run(conn, said: str) -> dict:
    """The whole flow: understand, then either answer, ask, refuse, or propose."""
    said = (said or "").strip()
    if not said:
        return {"outcome": "ask", "question": "想让它做什么？直接说一句话。"}
    ensure_schema(conn)
    parsed = interpret(conn, said)
    action, args = parsed["action"], parsed["args"]
    repeats = times_said(conn, said) + 1

    def done(outcome: str, summary: str, proposal_id: int | None = None, **extra) -> dict:
        _record(conn, said, parsed, outcome, summary, proposal_id)
        return {"outcome": outcome, "said": said, "action": action, "args": args,
                "confidence": parsed["confidence"], "times": repeats, **extra}

    if action == "none":
        return done("refused", parsed["question"],
                    message=parsed["question"] or "这件事我不做。价格、折扣、交期归你；"
                                                  "写代码、改规格要先写编号规格。")
    if action == "ask" or parsed["confidence"] < MIN_CONFIDENCE:
        question = parsed["question"] or "我不确定你的意思，能说得更具体一点吗？"
        return done("ask", question, question=question)

    if action in READ_ACTIONS:
        answer = answer_read(conn, action, args)
        if answer.get("ask"):
            return done("ask", answer["ask"], question=answer["ask"])
        return done("answered", answer.get("title", ""), answer=answer)

    plan = plan_write(conn, action, args)
    if plan.get("ask"):
        return done("ask", plan["ask"], question=plan["ask"])

    proposal = proposals.create(
        conn, action, title=plan["title"], payload=plan["payload"],
        lead_no=plan.get("lead_no"), risk=plan.get("risk", "medium"),
        reasoning=f"来自指挥台：「{said}」",
        backend="command", dedupe_key=f"command:{said}:{_now()}",
        force_pending=True)       # R2
    if proposal is None:
        return done("ask", "这条提议没能建起来，再说一遍？",
                    question="这条提议没能建起来，再说一遍？")
    return done("proposed", plan["title"], proposal_id=proposal["id"],
                proposal=proposal, impact=[list(x) for x in plan.get("impact", [])])
