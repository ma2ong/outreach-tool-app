from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from app import jobs
from app.agent import classify, learn, llm, proposals, report, run
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


def _bad(exc: Exception):
    raise HTTPException(status_code=400, detail=str(exc))


@router.get("/status")
def agent_status(conn=Depends(get_conn)):
    return run.status(conn)


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
def approve(proposal_id: int, req: ApproveRequest, conn=Depends(get_conn)):
    try:
        result = proposals.approve(conn, proposal_id, req.payload, req.note)
    except proposals.ProposalError as exc:
        _bad(exc)
    if result["status"] == "failed":
        raise HTTPException(status_code=400, detail=result["execution_result"])
    return result


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


def _run(job_id: str) -> None:
    from app.db import connect
    conn = connect(DB_PATH)
    try:
        jobs.finish(job_id, run.run_once(conn))
    except Exception as exc:  # noqa: BLE001
        jobs.fail(job_id, str(exc))
    finally:
        conn.close()


@router.post("/run")
def trigger_run(background: BackgroundTasks):
    """Classification and drafting take minutes, so the page never waits on them."""
    job_id = jobs.create(1)
    background.add_task(_run, job_id)
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


def _plan_now(job_id: str) -> None:
    from app.db import connect
    conn = connect(DB_PATH)
    try:
        jobs.finish(job_id, run.make_plan(conn))
    except Exception as exc:  # noqa: BLE001
        jobs.fail(job_id, str(exc))
    finally:
        conn.close()


@router.post("/plan/run")
def trigger_plan(background: BackgroundTasks):
    """Build today's plan on demand — the morning schedule is a convenience, not the
    only way in, and Allen should not have to wait until tomorrow to try it."""
    job_id = jobs.create(1)
    background.add_task(_plan_now, job_id)
    return {"job_id": job_id}


@router.get("/report")
def daily_report(conn=Depends(get_conn)):
    return {"text": report.compose(conn), "webhook_configured": bool(report.webhook_url())}


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
