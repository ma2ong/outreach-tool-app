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
    input_voltage_v: float | None = None
    controller_capacity_px: int | None = None
    controller_output_ports: int | None = None
    max_pixels_per_port: int | None = None
    spare_pct: float | None = None


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
    input_voltage_v: float | None = None
    controller_capacity_px: int | None = None
    controller_output_ports: int | None = None
    max_pixels_per_port: int | None = None
    spare_pct: float | None = None


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


@router.get("/coach")
def opportunity_coaching(limit: int = 50, conn=Depends(get_conn)):
    from app.agent import opportunity_coach
    return opportunity_coach.portfolio(conn, limit=limit)


@router.get("/customer/{lead_no}/360")
def customer_360(lead_no: int, conn=Depends(get_conn)):
    from app.agent import customer360
    result = customer360.build(conn, lead_no)
    if result is None:
        raise HTTPException(status_code=404, detail="客户不存在")
    return result


@router.get("/{opportunity_id}/coach")
def coach_one(opportunity_id: int, conn=Depends(get_conn)):
    from app.agent import opportunity_coach
    opportunity = opportunities.get(conn, opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="商机不存在")
    return opportunity_coach.coach_opportunity(conn, opportunity)


@router.get("/{opportunity_id}/products")
def product_matches(opportunity_id: int, limit: int = 3, conn=Depends(get_conn)):
    """Return internal evidence-backed product advice for one opportunity.

    Reference prices are not part of the advisor result. Historical quote/order counts
    are internal tie-break evidence only and never enter automatic customer context.
    """
    from app.agent import product_advisor
    opportunity = opportunities.get(conn, opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="商机不存在")
    return product_advisor.advise(conn, opportunity, limit=limit)


@router.get("/{opportunity_id}/solution")
def solution_engineering(opportunity_id: int, product_id: int | None = None,
                         conn=Depends(get_conn)):
    """Return internal deterministic layout/power/control engineering for one project."""
    from app.agent import solution_engineer
    opportunity = opportunities.get(conn, opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="商机不存在")
    return solution_engineer.advise(conn, opportunity, product_id=product_id)


@router.get("/{opportunity_id}/quote-readiness")
def quote_readiness(opportunity_id: int, product_id: int | None = None,
                    conn=Depends(get_conn)):
    """Return an internal technical starter packet. It never chooses commercial terms."""
    from app.agent import quote_readiness as readiness
    opportunity = opportunities.get(conn, opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="商机不存在")
    return readiness.assess(conn, opportunity, product_id=product_id)


@router.get("/{opportunity_id}/cases")
def case_matches(opportunity_id: int, limit: int = 5, conn=Depends(get_conn)):
    from app import case_library
    opportunity = opportunities.get(conn, opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="商机不存在")
    return case_library.match(conn, opportunity, limit=limit, shareable_only=True)


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
