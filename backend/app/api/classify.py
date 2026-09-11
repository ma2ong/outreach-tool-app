from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from app import icp, jobs
from app.db import connect
from app.jina import fetch as jina_fetch
from app.main_deps import database_path, get_conn

router = APIRouter(prefix="/api")

FETCHER = None  # injectable in tests; None -> real jina fetch


class ClassifyRequest(BaseModel):
    lead_nos: list[int] | None = None


def _run(job_id: str, lead_nos, db_path: str):
    conn = connect(db_path)
    fetch = FETCHER or jina_fetch
    try:
        if lead_nos:
            ph = ",".join("?" * len(lead_nos))
            rows = conn.execute(
                f"SELECT no, website FROM leads WHERE website IS NOT NULL AND website != '' AND no IN ({ph})",
                lead_nos).fetchall()
        else:
            rows = conn.execute(
                "SELECT no, website FROM leads WHERE website IS NOT NULL AND website != ''").fetchall()
        jobs.update(job_id, 0)
        counts: dict[str, int] = {}
        for i, r in enumerate(rows, 1):
            site = r["website"].removeprefix("https://").removeprefix("http://").strip("/")
            try:
                text = fetch(f"https://{site}")
            except Exception:  # noqa: BLE001 - unreachable site: leave lead unclassified
                jobs.update(job_id, i)
                continue
            result = icp.classify_text(text)
            icp.apply_to_lead(conn, r["no"], result)
            counts[result["icp_type"]] = counts.get(result["icp_type"], 0) + 1
            jobs.update(job_id, i)
        jobs.finish(job_id, {"checked": len(rows), "by_type": counts})
    except Exception as exc:  # noqa: BLE001
        jobs.fail(job_id, str(exc))
    finally:
        conn.close()


@router.post("/leads/classify")
def classify_leads(req: ClassifyRequest, background: BackgroundTasks, conn=Depends(get_conn)):
    job_id = jobs.create(total=len(req.lead_nos) if req.lead_nos else 0)
    background.add_task(_run, job_id, req.lead_nos, database_path(conn))
    return {"job_id": job_id}


@router.get("/leads/classify/jobs/{job_id}")
def classify_job(job_id: str):
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job
