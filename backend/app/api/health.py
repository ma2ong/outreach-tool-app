from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app import health, seeds
from app.main_deps import get_conn

router = APIRouter(prefix="/api")


class FixRequest(BaseModel):
    issues: list[str]


@router.get("/health/scan")
def scan(conn=Depends(get_conn)):
    found = health.scan(conn)
    return {"issues": found, "total": sum(len(v) for v in found.values())}


@router.post("/health/fix")
def fix(req: FixRequest, conn=Depends(get_conn)):
    return health.fix(conn, req.issues)


@router.get("/health/cleanable")
def cleanable(conn=Depends(get_conn)):
    """Preview for 一键智能清理: what a smart clean would delete, before it deletes it."""
    leads = health.cleanable(conn)
    return {"leads": leads, "count": len(leads)}


@router.post("/seeds/load")
def load_seeds(conn=Depends(get_conn)):
    templates = seeds.seed_templates(conn)
    sequence_ids = seeds.seed_sequences(conn)
    return {"templates": templates, "sequence_ids": sequence_ids}
