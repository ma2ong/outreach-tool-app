from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import activation
from app.main_deps import get_conn


router = APIRouter(prefix="/api/activation", tags=["activation"])


class AcknowledgeRequest(BaseModel):
    step: str


@router.get("")
def activation_status(conn=Depends(get_conn)):
    return activation.status(conn)


@router.get("/preview")
def activation_preview(conn=Depends(get_conn)):
    return activation.preview(conn)


@router.post("/acknowledge")
def acknowledge(req: AcknowledgeRequest, conn=Depends(get_conn)):
    try:
        return activation.acknowledge(conn, req.step)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
