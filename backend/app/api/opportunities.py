from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import opportunities
from app.main_deps import get_conn

router = APIRouter(prefix="/api/opportunities")


class OpportunityCreate(BaseModel):
    lead_no: int
    title: str
    stage: str = "qualified"
    amount: float | None = None
    currency: str = "USD"
    probability: int | None = None
    expected_close_date: str | None = None
    next_action: str | None = None
    next_action_date: str | None = None
    use_case: str | None = None
    indoor_outdoor: str | None = None
    width_m: float | None = None
    height_m: float | None = None
    quantity: int = 1
    pixel_pitch: str | None = None
    destination: str | None = None
    incoterm: str | None = None
    competitor: str | None = None
    loss_reason: str | None = None
    viewing_distance_m: float | None = None
    brightness_nits: int | None = None
    refresh_rate_hz: int | None = None
    maintenance_access: str | None = None
    cabinet_size: str | None = None
    control_system: str | None = None
    installation_type: str | None = None
    project_timing: str | None = None
    budget_range: str | None = None
    decision_process: str | None = None
    technical_notes: str | None = None


class OpportunityUpdate(BaseModel):
    title: str | None = None
    stage: str | None = None
    amount: float | None = None
    currency: str | None = None
    probability: int | None = None
    expected_close_date: str | None = None
    next_action: str | None = None
    next_action_date: str | None = None
    use_case: str | None = None
    indoor_outdoor: str | None = None
    width_m: float | None = None
    height_m: float | None = None
    quantity: int | None = None
    pixel_pitch: str | None = None
    destination: str | None = None
    incoterm: str | None = None
    competitor: str | None = None
    loss_reason: str | None = None
    viewing_distance_m: float | None = None
    brightness_nits: int | None = None
    refresh_rate_hz: int | None = None
    maintenance_access: str | None = None
    cabinet_size: str | None = None
    control_system: str | None = None
    installation_type: str | None = None
    project_timing: str | None = None
    budget_range: str | None = None
    decision_process: str | None = None
    technical_notes: str | None = None


def _bad(exc: opportunities.OpportunityValidation):
    raise HTTPException(status_code=400, detail=str(exc))


@router.get("")
def list_opportunities(stage: str | None = None, lead_no: int | None = None,
                       attention: bool = False, conn=Depends(get_conn)):
    return opportunities.list_all(
        conn, stage=stage, lead_no=lead_no, attention=attention)


@router.get("/stats")
def opportunity_stats(conn=Depends(get_conn)):
    return opportunities.stats(conn)


@router.post("")
def create_opportunity(req: OpportunityCreate, conn=Depends(get_conn)):
    try:
        return opportunities.create(
            conn, req.lead_no, req.model_dump(exclude_none=True, exclude={"lead_no"}))
    except opportunities.OpportunityValidation as exc:
        _bad(exc)


@router.patch("/{opportunity_id}")
def update_opportunity(opportunity_id: int, req: OpportunityUpdate, conn=Depends(get_conn)):
    try:
        result = opportunities.update(
            conn, opportunity_id, req.model_dump(exclude_unset=True))
    except opportunities.OpportunityValidation as exc:
        _bad(exc)
    if result is None:
        raise HTTPException(status_code=404, detail="商机不存在")
    return result
