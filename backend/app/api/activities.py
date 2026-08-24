from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import activities
from app.agent import task_ownership
from app.main_deps import get_conn

router = APIRouter(prefix="/api/activities")


class ActivityCreate(BaseModel):
    lead_no: int
    opportunity_id: int | None = None
    type: str = "task"
    title: str
    due_at: str | None = None
    priority: str = "normal"
    note: str | None = None


class ActivityUpdate(BaseModel):
    type: str | None = None
    title: str | None = None
    due_at: str | None = None
    priority: str | None = None
    status: str | None = None
    note: str | None = None


def _bad(exc: activities.ActivityValidation):
    raise HTTPException(status_code=400, detail=str(exc))


@router.get("")
def list_activities(status: str | None = "open", scope: str | None = None,
                    lead_no: int | None = None, opportunity_id: int | None = None,
                    work_owner: str | None = None, limit: int = 500,
                    conn=Depends(get_conn)):
    try:
        # Owner metadata is an additive migration and historic Agent provenance is
        # repaired only from exact proposal/task IDs. Never infer ownership from titles.
        task_ownership.backfill(conn)
        rows = activities.list_all(
            conn, status=status, scope=scope, lead_no=lead_no,
            opportunity_id=opportunity_id, limit=max(limit, 1000) if work_owner else limit)
        return task_ownership.filter_rows(rows, work_owner)[:limit]
    except activities.ActivityValidation as exc:
        _bad(exc)


@router.get("/stats")
def activity_stats(work_owner: str | None = None, conn=Depends(get_conn)):
    try:
        task_ownership.backfill(conn)
        return task_ownership.stats(conn, work_owner)
    except activities.ActivityValidation as exc:
        _bad(exc)


@router.post("")
def create_activity(req: ActivityCreate, conn=Depends(get_conn)):
    try:
        # A task explicitly created in the UI is human-owned by the schema default.
        task_ownership.ensure_schema(conn)
        return activities.create(
            conn, req.lead_no,
            req.model_dump(exclude={"lead_no", "opportunity_id"}, exclude_none=True),
            req.opportunity_id,
        )
    except activities.ActivityValidation as exc:
        _bad(exc)


@router.patch("/{activity_id}")
def update_activity(activity_id: int, req: ActivityUpdate, conn=Depends(get_conn)):
    try:
        result = activities.update(conn, activity_id, req.model_dump(exclude_unset=True))
    except activities.ActivityValidation as exc:
        _bad(exc)
    if result is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return result


@router.post("/{activity_id}/complete")
def complete_activity(activity_id: int, conn=Depends(get_conn)):
    result = activities.complete(conn, activity_id)
    if result is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return result
