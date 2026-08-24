from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from app import jobs
from app.agent import classify, control_center, conversation, learn, llm, mission, proposals, report, run
from app.main_deps import DB_PATH, get_conn

router = APIRouter(prefix="/api/agent")


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


class TakeoverRequest(BaseModel):
    reason: str = "Allen 手动接管"


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
    background.add_task(_execute_proposal, job_id, proposal_id, req.note, _db_path(conn))
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


def _db_path(conn) -> str:
    """The file this request's connection is actually open on.

    A background task outlives the request, so it needs its own connection — but
    reading the module-level DB_PATH would send it to the live lead base even when the
    caller was working on another database. Ask the connection instead.
    """
    row = conn.execute("PRAGMA database_list").fetchone()
    return row[2] or DB_PATH


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
    background.add_task(_run, job_id, _db_path(conn))
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
    background.add_task(_plan_now, job_id, _db_path(conn))
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


@router.get("/memory/{lead_no}")
def lead_memory(lead_no: int, conn=Depends(get_conn)):
    return proposals.get_memory(conn, lead_no) or {"lead_no": lead_no, "summary": ""}
