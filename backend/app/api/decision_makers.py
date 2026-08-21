from fastapi import APIRouter, Depends, HTTPException, Query

from app import decision_maker_radar
from app.main_deps import get_conn


router = APIRouter(prefix="/api/decision-makers", tags=["decision-makers"])


@router.get("/candidates")
def candidates(lead_no: int | None = None,
               status: str | None = Query("new"),
               limit: int = Query(200, ge=1, le=1000),
               conn=Depends(get_conn)):
    try:
        return decision_maker_radar.list_candidates(
            conn, lead_no=lead_no, status=status or None, limit=limit)
    except decision_maker_radar.DecisionMakerValidation as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/scan/{lead_no}")
def scan(lead_no: int, conn=Depends(get_conn)):
    try:
        return decision_maker_radar.scan(conn, lead_no)
    except decision_maker_radar.DecisionMakerValidation as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/candidates/{candidate_id}/promote")
def promote(candidate_id: int, conn=Depends(get_conn)):
    try:
        return decision_maker_radar.promote_candidate(conn, candidate_id, manual=True)
    except decision_maker_radar.DecisionMakerValidation as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/candidates/{candidate_id}/dismiss")
def dismiss(candidate_id: int, conn=Depends(get_conn)):
    try:
        return decision_maker_radar.dismiss_candidate(conn, candidate_id)
    except decision_maker_radar.DecisionMakerValidation as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
