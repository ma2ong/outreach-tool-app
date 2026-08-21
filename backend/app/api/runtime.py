import os

from fastapi import APIRouter, Depends

from app import runtime
from app.main_deps import get_conn


router = APIRouter(prefix="/api/runtime", tags=["runtime"])


@router.get("/status")
def worker_status(conn=Depends(get_conn)):
    data = runtime.status(conn)
    data["embedded_worker_enabled"] = os.environ.get("OUTREACH_EMBEDDED_WORKER", "1") != "0"
    data["dedicated_worker_expected"] = not data["embedded_worker_enabled"]
    return data
