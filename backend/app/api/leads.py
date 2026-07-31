import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app import dedupe, export, repository as repo
from app.main_deps import get_conn
from app.models import Lead

router = APIRouter(prefix="/api")

REPLY_CHANNELS = ("email", "whatsapp", "instagram")
ENRICH_FN = None  # injectable in tests; None -> real website enrich


class QuickAddRequest(BaseModel):
    url: str
    country: str | None = None
    company_en: str | None = None


class ReplyRequest(BaseModel):
    channel: str


class LeadUpdate(BaseModel):
    company_en: str | None = None
    company_local: str | None = None
    country: str | None = None
    city: str | None = None
    contact_name: str | None = None
    title: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    instagram: str | None = None
    facebook: str | None = None
    linkedin: str | None = None
    business: str | None = None
    stage: str | None = None
    tags: str | None = None
    follow_up_date: str | None = None
    next_action: str | None = None
    do_not_contact: bool | None = None


class NoteRequest(BaseModel):
    text: str


@router.get("/leads", response_model=list[Lead])
def list_leads(response: Response, country: str | None = None, channel: str | None = None,
               status: str | None = None, search: str | None = None,
               has: str | None = None, follow_up: str | None = None,
               sort: str | None = None, order: str = "asc",
               limit: int | None = None, offset: int = 0, conn=Depends(get_conn)):
    filters = dict(country=country, channel=channel, status=status, search=search,
                   has=has, follow_up=follow_up)
    response.headers["X-Total-Count"] = str(repo.count_leads(conn, **filters))
    return repo.list_leads(conn, **filters, sort=sort, order=order, limit=limit, offset=offset)


@router.get("/leads/export")
def export_leads(country: str | None = None, channel: str | None = None,
                 status: str | None = None, search: str | None = None,
                 has: str | None = None, follow_up: str | None = None,
                 fmt: str = "xlsx", conn=Depends(get_conn)):
    leads = repo.list_leads(conn, country=country, channel=channel, status=status,
                            search=search, has=has, follow_up=follow_up)
    stamp = dt.date.today().isoformat()
    if fmt == "csv":
        return Response(
            content=export.build_csv(leads), media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="leads_{stamp}.csv"'})
    return Response(
        content=export.build_xlsx(leads),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="leads_{stamp}.xlsx"'})


@router.post("/leads/quick_add")
def quick_add_lead(req: QuickAddRequest, conn=Depends(get_conn)):
    """Paste any customer URL (IG/FB/LinkedIn/website) -> lead in one click."""
    from app import icp as icp_mod, quick_add as qa
    try:
        fields = qa.parse_url(req.url)
    except qa.BadUrl as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    dup = repo.find_duplicate(conn, website=fields.get("website"),
                              instagram=fields.get("instagram"))
    if dup:
        return {"duplicate_of": dup, "lead": repo.get_lead(conn, dup)}
    data: dict = dict(fields)
    company_from_site = None
    if fields.get("website"):
        enrich = ENRICH_FN or _real_enrich
        try:
            info = enrich(fields["website"]) or {}
        except Exception:  # noqa: BLE001 — enrich failure must not block a manual add
            info = {}
        for k in ("email", "phone", "instagram", "facebook", "linkedin"):
            data.setdefault(k, info.get(k))
        company_from_site = info.get("company")
        if info.get("icp_type") and info["icp_type"] != "unknown":
            data["target_fit"] = f"{icp_mod.label(info['icp_type'])} ({info.get('fit_score', 0)})"
    data["company_en"] = (req.company_en or "").strip() or company_from_site or qa.display_name(fields)
    data["country"] = (req.country or "").strip() or None
    data.setdefault("target_fit", "quick-add")
    no = repo.insert_lead(conn, data)
    repo.add_note(conn, no, f"快速添加自 {req.url.strip()}")
    return {"duplicate_of": None, "lead": repo.get_lead(conn, no)}


def _real_enrich(domain: str) -> dict:
    from app.enrich import enrich_domain
    return enrich_domain(domain)


@router.get("/leads/duplicates")
def list_duplicates(conn=Depends(get_conn)):
    groups = dedupe.find_duplicate_groups(conn)
    return {"groups": groups, "total_dups": sum(len(g["dups"]) for g in groups)}


@router.post("/leads/duplicates/merge")
def merge_duplicates(conn=Depends(get_conn)):
    return dedupe.merge_all(conn)


@router.get("/leads/{no}", response_model=Lead)
def get_lead(no: int, conn=Depends(get_conn)):
    lead = repo.get_lead(conn, no)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead not found")
    return lead


@router.patch("/leads/{no}", response_model=Lead)
def update_lead(no: int, req: LeadUpdate, conn=Depends(get_conn)):
    fields = req.model_dump(exclude_unset=True)
    if not repo.update_lead(conn, no, fields):
        raise HTTPException(status_code=404, detail="lead not found")
    return repo.get_lead(conn, no)


@router.get("/leads/{no}/notes")
def list_notes(no: int, conn=Depends(get_conn)):
    if repo.get_lead(conn, no) is None:
        raise HTTPException(status_code=404, detail="lead not found")
    return repo.list_notes(conn, no)


@router.post("/leads/{no}/notes", response_model=Lead)
def add_note(no: int, req: NoteRequest, conn=Depends(get_conn)):
    if repo.get_lead(conn, no) is None:
        raise HTTPException(status_code=404, detail="lead not found")
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="empty note")
    repo.add_note(conn, no, text)
    return repo.get_lead(conn, no)


@router.post("/leads/{no}/reply")
def mark_replied(no: int, req: ReplyRequest, conn=Depends(get_conn)):
    if req.channel not in REPLY_CHANNELS:
        raise HTTPException(status_code=400, detail="unknown channel")
    if repo.get_lead(conn, no) is None:
        raise HTTPException(status_code=404, detail="lead not found")
    repo.mark_replied(conn, no, req.channel)
    return {"ok": True}
