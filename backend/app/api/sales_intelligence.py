from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import sales_intelligence
from app.main_deps import get_conn


router = APIRouter(prefix="/api")


class SignalCreate(BaseModel):
    signal_type: str = "manual"
    headline: str
    evidence: str
    source_url: str
    occurred_at: str | None = None
    confidence: int = 60
    use_case: str | None = None
    product_fit: str | None = None
    suggested_angle: str | None = None


class SignalUpdate(BaseModel):
    signal_type: str | None = None
    headline: str | None = None
    evidence: str | None = None
    source_url: str | None = None
    occurred_at: str | None = None
    confidence: int | None = None
    use_case: str | None = None
    product_fit: str | None = None
    suggested_angle: str | None = None
    status: str | None = None


def _bad(exc: sales_intelligence.SalesIntelligenceValidation):
    raise HTTPException(status_code=400, detail=str(exc))


@router.get("/sales-intelligence/ranked")
def ranked(limit: int = 100, min_score: int = 0, conn=Depends(get_conn)):
    return sales_intelligence.ranked(conn, limit=limit, min_score=min_score)


@router.get("/sales-intelligence/summary")
def summary(conn=Depends(get_conn)):
    return sales_intelligence.summary(conn)


@router.get("/leads/{lead_no}/intelligence")
def lead_intelligence(lead_no: int, conn=Depends(get_conn)):
    result = sales_intelligence.score_lead(conn, lead_no)
    if result is None:
        raise HTTPException(status_code=404, detail="客户不存在")
    result["signals"] = sales_intelligence.list_signals(conn, lead_no=lead_no)
    return result


@router.get("/buying-signals")
def list_signals(lead_no: int | None = None, status: str | None = None,
                 limit: int = 200, conn=Depends(get_conn)):
    try:
        return sales_intelligence.list_signals(
            conn, lead_no=lead_no, status=status, limit=limit)
    except sales_intelligence.SalesIntelligenceValidation as exc:
        _bad(exc)


@router.post("/leads/{lead_no}/buying-signals")
def create_signal(lead_no: int, req: SignalCreate, conn=Depends(get_conn)):
    try:
        return sales_intelligence.create_signal(
            conn, lead_no, req.model_dump(exclude_none=True))
    except sales_intelligence.SalesIntelligenceValidation as exc:
        _bad(exc)


@router.patch("/buying-signals/{signal_id}")
def update_signal(signal_id: int, req: SignalUpdate, conn=Depends(get_conn)):
    try:
        result = sales_intelligence.update_signal(
            conn, signal_id, req.model_dump(exclude_unset=True))
    except sales_intelligence.SalesIntelligenceValidation as exc:
        _bad(exc)
    if result is None:
        raise HTTPException(status_code=404, detail="采购信号不存在")
    return result


@router.post("/buying-signals/{signal_id}/task")
def signal_to_task(signal_id: int, conn=Depends(get_conn)):
    result = sales_intelligence.create_task_from_signal(conn, signal_id)
    if result is None:
        raise HTTPException(status_code=404, detail="采购信号不存在")
    return result


@router.post("/buying-signals/{signal_id}/opportunity")
def signal_to_opportunity(signal_id: int, conn=Depends(get_conn)):
    result = sales_intelligence.create_opportunity_from_signal(conn, signal_id)
    if result is None:
        raise HTTPException(status_code=404, detail="采购信号不存在")
    return result
