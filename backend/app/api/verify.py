from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from app import jobs, verify
from app.db import connect
from app.main_deps import database_path, get_conn

router = APIRouter(prefix="/api")

RESOLVER = None  # injectable in tests; None -> real DNS


class VerifyRequest(BaseModel):
    lead_nos: list[int] | None = None


def _run(job_id: str, lead_nos, db_path: str):
    conn = connect(db_path)
    try:
        resolver = RESOLVER or verify.default_resolver
        result = verify.verify_leads(conn, lead_nos, resolve_domain=resolver)
        jobs.finish(job_id, result)
    except Exception as exc:  # noqa: BLE001
        jobs.fail(job_id, str(exc))
    finally:
        conn.close()


@router.post("/leads/verify")
def verify_emails(req: VerifyRequest, background: BackgroundTasks, conn=Depends(get_conn)):
    job_id = jobs.create(total=len(req.lead_nos) if req.lead_nos else 0)
    background.add_task(_run, job_id, req.lead_nos, database_path(conn))
    return {"job_id": job_id}


@router.get("/leads/verify/jobs/{job_id}")
def verify_job(job_id: str):
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job
