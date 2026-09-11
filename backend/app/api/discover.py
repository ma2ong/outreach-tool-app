from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from app import discovery, jobs
from app.db import connect
from app.main_deps import DB_PATH as _DB_PATH, get_conn

router = APIRouter(prefix="/api")

DB_PATH = _DB_PATH
SEARCH_FN = None    # injectable in tests; None -> real search
ENRICH_FN = None    # injectable in tests; None -> real enrich
HARVEST_FN = None   # injectable in tests; None -> real harvest


class DiscoverRequest(BaseModel):
    query: str | None = None          # single query (legacy)
    queries: list[str] | None = None  # multiple queries, run sequentially, dedup by domain
    limit: int = 10                   # per query
    exclude_countries: list[str] = []
    exclude_peers: bool = True        # drop Chinese peers/suppliers by default
    # Which channels to ask, and how to read them (docs/128). Empty means the channels
    # that can run with nobody watching; naming one is Allen pressing the button, which
    # is the only way a channel that opens a window is ever reached.
    channels: list[str] | None = None
    engine: str | None = None


class PageDiscoverRequest(BaseModel):
    url: str
    limit: int = 40
    # jina reads the HTML; browser drives a real Chrome for listings that keep their
    # companies inside JavaScript (docs/124). Never defaulted to browser: it opens a
    # visible window and costs a model call per step.
    engine: str = "jina"
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


def _search_fn_for(req: "DiscoverRequest", report: list[dict]):
    """The reader for this request, and a place to put what each channel reported.

    A channel that was turned away says so (docs/128 R2), and that sentence has to reach
    the panel: "0 家" and "Google 判定本机为异常流量" look identical in a candidate list
    and mean opposite things.
    """
    if SEARCH_FN:
        return SEARCH_FN
    from app import discovery_sources

    def search(query: str, limit: int):
        out = discovery_sources.gather([query], limit, only=req.channels, engine=req.engine)
        report.extend(out["sources"])
        return out["candidates"]
    return search


def _run(job_id: str, queries: list[str], limit: int, req: "DiscoverRequest"):
    conn = connect(DB_PATH)
    report: list[dict] = []
    try:
        seen: set[str] = set()
        merged: list[dict] = []
        for qi, query in enumerate(queries):
            cands = discovery.run_discovery(
                conn, query, limit, search_fn=_search_fn_for(req, report), enrich_fn=ENRICH_FN,
                on_progress=lambda done, total, qi=qi: jobs.update(job_id, qi * limit + done),
                exclude_countries=req.exclude_countries, exclude_peers=req.exclude_peers)
            for c in cands:
                if c["domain"] not in seen:
                    seen.add(c["domain"])
                    merged.append(c)
        jobs.finish(job_id, {"candidates": merged, "sources": _merge_report(report)})
    except Exception as exc:  # noqa: BLE001
        jobs.fail(job_id, str(exc))
    finally:
        conn.close()


def _merge_report(report: list[dict]) -> list[dict]:
    """One line per channel for the whole run, not one per keyword."""
    merged: dict[str, dict] = {}
    for row in report:
        prev = merged.setdefault(row["name"], {**row, "found": 0})
        prev["found"] += row.get("found", 0)
        # A channel that worked on one keyword and was walled on the next is worth
        # knowing about, so a failure wins over an ok that came before it.
        if row.get("status") != "ok" and prev.get("status") == "ok":
            prev["status"], prev["reason"] = row.get("status"), row.get("reason", "")
    return list(merged.values())


def _harvest_fn_for(engine: str):
    """The browser route bypasses HARVEST_FN: they are two different readers of one page."""
    if engine != "browser":
        return HARVEST_FN
    from app import browser_harvest

    return lambda url, limit: browser_harvest.harvest_with_browser(url, limit)


def _run_page(job_id: str, url: str, limit: int, req: "PageDiscoverRequest"):
    conn = connect(DB_PATH)
    try:
        cands = discovery.run_page_discovery(
            conn, url, limit, harvest_fn=_harvest_fn_for(req.engine), enrich_fn=ENRICH_FN,
            on_progress=lambda done, total: jobs.update(job_id, done),
            exclude_countries=req.exclude_countries, exclude_peers=req.exclude_peers)
        jobs.finish(job_id, {"candidates": cands})
    except Exception as exc:  # noqa: BLE001
        jobs.fail(job_id, str(exc))
    finally:
        conn.close()


def _check_channels(req: "DiscoverRequest") -> None:
    """Refuse an unknown channel or a reader it never declared (docs/128 R5).

    Silently falling back to the default reader would answer a different question than
    the one asked — the same failure mode Bing was dropped for.
    """
    from app import discovery_sources

    for name in req.channels or []:
        source = discovery_sources.SOURCES.get(name)
        if source is None:
            raise HTTPException(status_code=400, detail=f"没有这条渠道：{name}")
        if req.engine and req.engine not in source.engines:
            raise HTTPException(
                status_code=400,
                detail=f"{name} 没有「{req.engine}」这种读法，它声明的是："
                       f"{'/'.join(source.engines)}")
        reason = source.unavailable()
        if reason:
            raise HTTPException(status_code=400, detail=f"{source.label}：{reason}")


@router.post("/discover")
def discover(req: DiscoverRequest, background: BackgroundTasks):
    queries = [q.strip() for q in (req.queries or ([req.query] if req.query else [])) if q and q.strip()]
    if not queries:
        raise HTTPException(status_code=400, detail="query required")
    _check_channels(req)
    job_id = jobs.create(total=req.limit * len(queries))
    background.add_task(_run, job_id, queries, req.limit, req)
    return {"job_id": job_id}


@router.post("/discover/page")
def discover_page(req: PageDiscoverRequest, background: BackgroundTasks):
    if not req.url.strip().lower().startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="url must start with http:// or https://")
    if req.engine not in ("jina", "browser"):
        raise HTTPException(status_code=400, detail="engine must be jina or browser")
    if req.engine == "browser":
        from app import browser_harvest

        # Refuse before the job exists: an unconfigured engine is something to tell
        # Allen now, not a job that finishes with nothing in it (docs/124 R5).
        reason = browser_harvest.unavailable()
        if reason:
            raise HTTPException(status_code=400, detail=reason)
    job_id = jobs.create(total=req.limit)
    background.add_task(_run_page, job_id, req.url.strip(), req.limit, req)
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
