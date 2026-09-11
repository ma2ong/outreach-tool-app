from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from app import jobs
from app.agent import (classify, command, control_center, conversation, learn, llm,
                       memory as memory_mod, mission, proposals, report, run)
from app.main_deps import database_path, get_conn

router = APIRouter(prefix="/api/agent")


class MemoryWriteRequest(BaseModel):
    content: str
    kind: str = "profile"


class ApproveRequest(BaseModel):
    payload: dict | None = None
    note: str = ""


class RejectRequest(BaseModel):
    reason: str
    note: str = ""


class AutonomyRequest(BaseModel):
    kind: str
    level: str


class BackendRequest(BaseModel):
    task: str
    backend: str


class PlanRequest(BaseModel):
    enabled: bool


class MissionRequest(BaseModel):
    target_markets: list[str]
    daily_qualified_leads: int
    minimum_fit_score: int
    auto_enroll: bool


class CommandRequest(BaseModel):
    said: str


class TakeoverRequest(BaseModel):
    reason: str = "Allen 手动接管"


class ConversationScheduleRequest(BaseModel):
    next_action: str
    due_at: str


class LearningLessonCreate(BaseModel):
    rule_text: str
    category: str
    channel: str | None = None
    market: str | None = None
    customer_type: str | None = None
    source_proposal_ids: list[int] = []


class LearningLessonStatus(BaseModel):
    status: str


class LearningLessonRevise(BaseModel):
    rule_text: str
    category: str | None = None
    channel: str | None = None
    market: str | None = None
    customer_type: str | None = None


def _bad(exc: Exception):
    raise HTTPException(status_code=400, detail=str(exc))


@router.get("/status")
def agent_status(conn=Depends(get_conn)):
    return run.status(conn)


@router.get("/control-center")
def autonomy_control_center(conn=Depends(get_conn)):
    """One read-only operating picture; it never creates/sends/updates customer work."""
    return control_center.snapshot(conn)


@router.get("/mission")
def get_mission(conn=Depends(get_conn)):
    return mission.get(conn)


@router.put("/mission")
def update_mission(req: MissionRequest, conn=Depends(get_conn)):
    return mission.set_mission(conn, req.model_dump())


def _conversation_channel(channel: str) -> str:
    if channel not in ("email", "whatsapp", "instagram", "facebook"):
        raise HTTPException(status_code=400, detail="不支持的会话渠道")
    return channel


@router.post("/conversations/{lead_no}/{channel}/takeover")
def takeover_conversation(lead_no: int, channel: str, req: TakeoverRequest,
                          conn=Depends(get_conn)):
    if conn.execute("SELECT 1 FROM leads WHERE no=?", (lead_no,)).fetchone() is None:
        raise HTTPException(status_code=404, detail="客户不存在")
    return conversation.takeover(conn, lead_no, _conversation_channel(channel), req.reason)


@router.post("/conversations/{lead_no}/{channel}/resume")
def resume_conversation(lead_no: int, channel: str, conn=Depends(get_conn)):
    if conn.execute("SELECT 1 FROM leads WHERE no=?", (lead_no,)).fetchone() is None:
        raise HTTPException(status_code=404, detail="客户不存在")
    return conversation.resume(conn, lead_no, _conversation_channel(channel))


@router.patch("/conversations/{lead_no}/{channel}/schedule")
def schedule_conversation(lead_no: int, channel: str, req: ConversationScheduleRequest,
                          conn=Depends(get_conn)):
    if conn.execute("SELECT 1 FROM leads WHERE no=?", (lead_no,)).fetchone() is None:
        raise HTTPException(status_code=404, detail="客户不存在")
    try:
        return conversation.reschedule(
            conn, lead_no, _conversation_channel(channel),
            next_action=req.next_action, due_at=req.due_at,
        )
    except ValueError as exc:
        _bad(exc)


@router.get("/meta")
def agent_meta():
    """The vocabulary the UI renders: kinds, levels, intents, rejection reasons."""
    return {
        "kinds": list(proposals.KINDS),
        "autonomy": list(proposals.AUTONOMY),
        "risks": list(proposals.RISKS),
        "intents": classify.INTENTS,
        # The UI must be able to say "this one is yours" without hardcoding the rule.
        "quote_intents": list(classify.QUOTE_INTENTS),
        "reject_reasons": proposals.REJECT_REASONS,
        "backends": list(llm.BACKENDS),
        "tasks": list(llm.TASKS),
    }


@router.get("/proposals")
def list_proposals(status: str | None = "pending", lead_no: int | None = None,
                   kind: str | None = None, limit: int = 200, conn=Depends(get_conn)):
    return proposals.list_proposals(conn, status=status, lead_no=lead_no,
                                    kind=kind, limit=limit)


@router.get("/proposals/{proposal_id}")
def get_proposal(proposal_id: int, conn=Depends(get_conn)):
    p = proposals.get(conn, proposal_id)
    if not p:
        raise HTTPException(status_code=404, detail="提议不存在")
    return p


@router.post("/proposals/{proposal_id}/approve")
def approve(proposal_id: int, req: ApproveRequest, background: BackgroundTasks,
            conn=Depends(get_conn)):
    """Record the decision now, do the work in the background.

    A discover_run takes minutes; waiting for it inside the request is what let the
    tunnel cut the connection while the server kept going."""
    try:
        proposal = proposals.mark_approved(conn, proposal_id, req.payload, req.note)
    except proposals.ProposalError as exc:
        _bad(exc)
    job_id = jobs.create(1)
    background.add_task(_execute_proposal, job_id, proposal_id, req.note, database_path(conn))
    return {"job_id": job_id, "proposal": proposal}


def _execute_proposal(job_id: str, proposal_id: int, note: str, db_path: str) -> None:
    from app.db import connect
    conn = connect(db_path)
    try:
        result = proposals.execute_approved(conn, proposal_id, note=note)
        if result["status"] == "failed":
            jobs.fail(job_id, result["execution_result"])
        else:
            jobs.finish(job_id, result)
    except Exception as exc:  # noqa: BLE001 — a failed action stays visible, not crashes
        jobs.fail(job_id, str(exc))
    finally:
        conn.close()


@router.get("/proposals/job/{job_id}")
def proposal_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.post("/proposals/{proposal_id}/reject")
def reject(proposal_id: int, req: RejectRequest, conn=Depends(get_conn)):
    try:
        return proposals.reject(conn, proposal_id, req.reason, req.note)
    except proposals.ProposalError as exc:
        _bad(exc)


@router.post("/autonomy")
def set_autonomy(req: AutonomyRequest, conn=Depends(get_conn)):
    try:
        proposals.set_autonomy(conn, req.kind, req.level)
    except proposals.ProposalError as exc:
        _bad(exc)
    return {"autonomy": proposals.autonomy_map(conn)}


@router.post("/backend")
def set_backend(req: BackendRequest, conn=Depends(get_conn)):
    try:
        llm.set_backend(conn, req.task, req.backend)
    except ValueError as exc:
        _bad(exc)
    return llm.status(conn)


def _run(job_id: str, db_path: str) -> None:
    from app.db import connect
    conn = connect(db_path)
    try:
        jobs.finish(job_id, run.run_once(conn))
    except Exception as exc:  # noqa: BLE001
        jobs.fail(job_id, str(exc))
    finally:
        conn.close()


@router.post("/run")
def trigger_run(background: BackgroundTasks, conn=Depends(get_conn)):
    """Classification and drafting take minutes, so the page never waits on them."""
    job_id = jobs.create(1)
    background.add_task(_run, job_id, database_path(conn))
    return {"job_id": job_id}


@router.get("/run/{job_id}")
def run_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.post("/plan/enabled")
def set_plan_enabled(req: PlanRequest, conn=Depends(get_conn)):
    run.set_plan_enabled(conn, req.enabled)
    return run.status(conn)["plan"]


def _plan_now(job_id: str, db_path: str) -> None:
    from app.db import connect
    conn = connect(db_path)
    try:
        jobs.finish(job_id, run.make_plan(conn))
    except Exception as exc:  # noqa: BLE001
        jobs.fail(job_id, str(exc))
    finally:
        conn.close()


@router.post("/plan/run")
def trigger_plan(background: BackgroundTasks, conn=Depends(get_conn)):
    """Build today's plan on demand — the morning schedule is a convenience, not the
    only way in, and Allen should not have to wait until tomorrow to try it."""
    job_id = jobs.create(1)
    background.add_task(_plan_now, job_id, database_path(conn))
    return {"job_id": job_id}


@router.get("/report")
def daily_report(conn=Depends(get_conn)):
    return {"text": report.compose(conn), "targets": report.targets(),
            "webhook_configured": bool(report.targets())}


@router.post("/report/send")
def send_report(conn=Depends(get_conn)):
    return report.send_daily(conn)


@router.get("/learning")
def learning(conn=Depends(get_conn)):
    """What Allen's decisions have taught the agent — and whether it is using it yet."""
    return learn.summary(conn)


@router.post("/learning/lessons")
def create_learning_lesson(req: LearningLessonCreate, conn=Depends(get_conn)):
    try:
        return learn.create_lesson(conn, **req.model_dump())
    except (ValueError, LookupError) as exc:
        _bad(exc)


@router.patch("/learning/lessons/{lesson_id}/status")
def change_learning_lesson_status(lesson_id: int, req: LearningLessonStatus,
                                  conn=Depends(get_conn)):
    try:
        return learn.set_lesson_status(conn, lesson_id, req.status)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        _bad(exc)


@router.post("/learning/lessons/{lesson_id}/revisions")
def revise_learning_lesson(lesson_id: int, req: LearningLessonRevise,
                           conn=Depends(get_conn)):
    try:
        return learn.revise_lesson(conn, lesson_id, **req.model_dump())
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        _bad(exc)


@router.get("/memory/{lead_no}")
def lead_memory(lead_no: int, conn=Depends(get_conn)):
    stored = proposals.get_memory(conn, lead_no) or {"lead_no": lead_no, "summary": ""}
    return {**stored, "items": memory_mod.items(conn, lead_no)}


@router.post("/memory/{lead_no}")
def write_lead_memory(lead_no: int, req: MemoryWriteRequest, conn=Depends(get_conn)):
    """A memory Allen writes himself. The agent may read it and may never rewrite it."""
    try:
        return memory_mod.write_explicit(conn, lead_no, req.content, req.kind)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/memory/{lead_no}/{item_id}")
def forget_lead_memory(lead_no: int, item_id: int, conn=Depends(get_conn)):
    """Retire one memory. The row stays on the record; it just stops being current."""
    if not memory_mod.forget(conn, lead_no, item_id):
        raise HTTPException(status_code=404, detail="记忆不存在")
    return {"ok": True}


@router.post("/command")
def agent_command(req: CommandRequest, conn=Depends(get_conn)):
    """One sentence in (docs/88). Writes stop at `pending`; approval goes through the
    existing /proposals/{id}/approve — the command bar adds no way to execute."""
    try:
        return command.run(conn, req.said)
    except Exception as exc:  # noqa: BLE001
        _bad(exc)


@router.get("/commands")
def agent_command_history(limit: int = 20, conn=Depends(get_conn)):
    return {"items": command.history(conn, limit=limit)}
