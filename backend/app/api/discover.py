from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from app import discovery, jobs
from app.db import connect
from app.main_deps import database_path, get_conn

router = APIRouter(prefix="/api")

SEARCH_FN = None    # injectable in tests; None -> real search
ENRICH_FN = None    # injectable in tests; None -> real enrich
HARVEST_FN = None   # injectable in tests; None -> real harvest


class DiscoverRequest(BaseModel):
    query: str | None = None          # single query (legacy)
    queries: list[str] | None = None  # multiple queries, run sequentially, dedup by domain
    limit: int = 10                   # per query
    exclude_countries: list[str] = []
    exclude_peers: bool = True        # drop Chinese peers/suppliers by default


class PageDiscoverRequest(BaseModel):
    url: str
    limit: int = 40
    exclude_countries: list[str] = []
    exclude_peers: bool = True


class Candidate(BaseModel):
    company_en: str
    website: str | None = None
    email: str | None = None
    country: str | None = None  # detected per candidate; falls back to the request's country
    city: str | None = None
    phone: str | None = None
    instagram: str | None = None
    facebook: str | None = None
    linkedin: str | None = None
    source: str | None = None
    icp_type: str | None = None
    fit_score: int | None = None
    brief: str | None = None
    hook: str | None = None
    email_source: str | None = None
    # Public evidence found during the same website reads. Keep it attached until the
    # candidate is actually imported; discovery results that are rejected create no CRM
    # signal rows.
    buying_signals: list[dict] = Field(default_factory=list)


class ImportRequest(BaseModel):
    country: str | None = None
    candidates: list[Candidate]


def _run(job_id: str, queries: list[str], limit: int, req: "DiscoverRequest", db_path: str):
    conn = connect(db_path)
    try:
        seen: set[str] = set()
        merged: list[dict] = []
        for qi, query in enumerate(queries):
            cands = discovery.run_discovery(
                conn, query, limit, search_fn=SEARCH_FN, enrich_fn=ENRICH_FN,
                on_progress=lambda done, total, qi=qi: jobs.update(job_id, qi * limit + done),
                exclude_countries=req.exclude_countries, exclude_peers=req.exclude_peers)
            for c in cands:
                if c["domain"] not in seen:
                    seen.add(c["domain"])
                    merged.append(c)
        jobs.finish(job_id, {"candidates": merged})
    except Exception as exc:  # noqa: BLE001
        jobs.fail(job_id, str(exc))
    finally:
        conn.close()


def _run_page(job_id: str, url: str, limit: int, req: "PageDiscoverRequest", db_path: str):
    conn = connect(db_path)
    try:
        cands = discovery.run_page_discovery(
            conn, url, limit, harvest_fn=HARVEST_FN, enrich_fn=ENRICH_FN,
            on_progress=lambda done, total: jobs.update(job_id, done),
            exclude_countries=req.exclude_countries, exclude_peers=req.exclude_peers)
        jobs.finish(job_id, {"candidates": cands})
    except Exception as exc:  # noqa: BLE001
        jobs.fail(job_id, str(exc))
    finally:
        conn.close()


@router.post("/discover")
def discover(req: DiscoverRequest, background: BackgroundTasks, conn=Depends(get_conn)):
    queries = [q.strip() for q in (req.queries or ([req.query] if req.query else [])) if q and q.strip()]
    if not queries:
        raise HTTPException(status_code=400, detail="query required")
    job_id = jobs.create(total=req.limit * len(queries))
    background.add_task(_run, job_id, queries, req.limit, req, database_path(conn))
    return {"job_id": job_id}


@router.post("/discover/page")
def discover_page(req: PageDiscoverRequest, background: BackgroundTasks, conn=Depends(get_conn)):
    if not req.url.strip().lower().startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="url must start with http:// or https://")
    job_id = jobs.create(total=req.limit)
    background.add_task(_run_page, job_id, req.url.strip(), req.limit, req, database_path(conn))
    return {"job_id": job_id}


@router.get("/discover/sources")
def discovery_sources():
    """Which prospecting channels can run right now, and why the others cannot.

    Unconfigured and broken are different states (docs/70 R4): one needs a key, the
    other needs fixing, and a page that shows both as "failed" teaches nobody which.
    """
    from app import discovery_sources as sources

    return {"sources": sources.status()}


@router.get("/discover/jobs/{job_id}")
def discover_job(job_id: str):
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.post("/leads/import")
def import_leads(req: ImportRequest, conn=Depends(get_conn)):
    return discovery.import_candidates(
        conn, [candidate.model_dump() for candidate in req.candidates], req.country)
