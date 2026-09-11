from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from app import jobs, sequence_edit, sequence_send
from app import sequences as seq
from app.api import channels as channels_api
from app.api import send as send_api
from app.db import connect
from app.main_deps import database_path, get_conn
from app.models import DueItem, Sequence, SequenceStep

router = APIRouter(prefix="/api/sequences")


class StepIn(BaseModel):
    day_offset: int = 0
    subject: str | None = None
    body: str
    image: str | None = None


class SequenceCreate(BaseModel):
    name: str
    channel: str
    steps: list[StepIn]
    # docs/86 R4: who this sequence is for. Left empty it is a manual-only sequence —
    # usable from 客户库, never picked by automatic routing, and the form says so.
    segment: str | None = None
    korean: bool = False
    route_country: str | None = None
    route_priority: int = 100_000


class StepEdit(BaseModel):
    subject: str | None = None
    body: str
    day_offset: int | None = None


class EnrollRequest(BaseModel):
    lead_nos: list[int]


class AdvanceRequest(BaseModel):
    enrollment_ids: list[int]


class SendDueRequest(BaseModel):
    enrollment_ids: list[int]
    image: str | None = send_api.DEFAULT_ATTACHMENT


class RoutingRuleIn(BaseModel):
    sequence_id: int
    enabled: bool = True
    priority: int = 0
    country: str | None = None
    language: str | None = None
    customer_type: str | None = None


class RoutingPreviewIn(BaseModel):
    country: str | None = None
    language: str | None = None
    customer_type: str | None = None


class CopyRollbackIn(BaseModel):
    version_id: int


def _run_send(job_id: str, enrollment_ids: list[int], image: str | None, db_path: str):
    conn = connect(db_path)
    try:
        result = sequence_send.send_due(
            conn, enrollment_ids, sender=send_api.pick_sender(conn), engine=channels_api.ENGINE,
            image_default=image,
            on_progress=lambda done, total: jobs.update(job_id, done))
        jobs.finish(job_id, result)
    except Exception as exc:  # noqa: BLE001
        jobs.fail(job_id, str(exc))
    finally:
        conn.close()


@router.get("", response_model=list[Sequence])
def list_sequences(conn=Depends(get_conn)):
    return [Sequence(**s) for s in seq.list_sequences(conn)]


@router.post("", response_model=Sequence)
def create_sequence(req: SequenceCreate, conn=Depends(get_conn)):
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="name required")
    if req.channel not in ("email", "whatsapp", "instagram", "facebook"):
        raise HTTPException(status_code=400, detail="unsupported channel")
    if not req.steps or any(not s.body.strip() for s in req.steps):
        raise HTTPException(status_code=400, detail="each step needs a body")
    from app import copy_segments, sequence_routing
    from app.seed_sequences import ensure_routing_columns

    if req.segment and req.segment not in copy_segments.SEGMENTS:
        raise HTTPException(status_code=400, detail="unknown segment")
    if not 0 <= req.route_priority <= 1_000_000:
        raise HTTPException(status_code=400, detail="route priority must be 0..1000000")
    sid = seq.create_sequence(conn, req.name.strip(), req.channel,
                              [s.model_dump() for s in req.steps])
    ensure_routing_columns(conn)
    if req.segment:
        conn.execute("UPDATE sequences SET segment=?, korean=? WHERE id=?",
                     (req.segment, int(req.korean), sid))
        conn.commit()
        sequence_routing.replace_declared_route(
            conn, sid, customer_type=req.segment,
            language="ko" if req.korean else "en",
            country=req.route_country, priority=req.route_priority)
    return Sequence(**seq.get_sequence(conn, sid))


def _routing_values(req: RoutingRuleIn) -> dict:
    if not 0 <= req.priority <= 1_000_000:
        raise HTTPException(status_code=400, detail="route priority must be 0..1000000")
    return req.model_dump()


@router.get("/routing")
def list_routing_rules(conn=Depends(get_conn)):
    from app import sequence_routing
    return sequence_routing.list_rules(conn)


@router.post("/routing")
def create_routing_rule(req: RoutingRuleIn, conn=Depends(get_conn)):
    from app import sequence_routing
    values = _routing_values(req)
    try:
        rule_id = sequence_routing.add_rule(conn, **values)
        return next(row for row in sequence_routing.list_rules(conn) if row["id"] == rule_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/routing/{rule_id}")
def edit_routing_rule(rule_id: int, req: RoutingRuleIn, conn=Depends(get_conn)):
    from app import sequence_routing
    try:
        return sequence_routing.update_rule(conn, rule_id, **_routing_values(req))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/routing/preview")
def preview_routing(req: RoutingPreviewIn, conn=Depends(get_conn)):
    from app import copy_segments, sequence_routing
    if req.language not in (None, "en", "ko"):
        raise HTTPException(status_code=400, detail="language must be en, ko or empty")
    if req.customer_type not in (None, *copy_segments.SEGMENTS):
        raise HTTPException(status_code=400, detail="unknown customer type")
    return sequence_routing.explain(conn, {
        "country": req.country, "routing_language": req.language,
        "customer_type": req.customer_type,
    })


@router.post("/{sid}/steps/{order}/preview")
def preview_step(sid: int, order: int, req: StepEdit, conn=Depends(get_conn)):
    """Render this step against a real lead and run the guard, before it is saved."""
    if seq.get_sequence(conn, sid) is None:
        raise HTTPException(status_code=404, detail="sequence not found")
    return sequence_edit.preview(conn, sid, order, req.subject, req.body)


@router.put("/{sid}/steps/{order}")
def update_step(sid: int, order: int, req: StepEdit, conn=Depends(get_conn)):
    if seq.get_sequence(conn, sid) is None:
        raise HTTPException(status_code=404, detail="sequence not found")
    try:
        return sequence_edit.update_step(
            conn, sid, order, subject=req.subject, body=req.body,
            day_offset=req.day_offset)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{sid}/steps/{order}/versions")
def step_versions(sid: int, order: int, conn=Depends(get_conn)):
    from app import copy_versions
    if seq.get_sequence(conn, sid) is None:
        raise HTTPException(status_code=404, detail="sequence not found")
    return copy_versions.list_sequence_step(conn, sid, order)


@router.post("/{sid}/steps/{order}/rollback")
def rollback_step(sid: int, order: int, req: CopyRollbackIn, conn=Depends(get_conn)):
    from app import copy_versions
    if seq.get_sequence(conn, sid) is None:
        raise HTTPException(status_code=404, detail="sequence not found")
    try:
        return copy_versions.rollback_sequence_step(conn, sid, order, req.version_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{sid}/revert")
def revert_sequence(sid: int, conn=Depends(get_conn)):
    """Give a sequence back to the repo's copy on the next seed."""
    if seq.get_sequence(conn, sid) is None:
        raise HTTPException(status_code=404, detail="sequence not found")
    from app import seed_sequences

    sequence_edit.revert(conn, sid)
    seed_sequences.seed_all(conn)
    return {"reverted": True}


@router.get("/due", response_model=list[DueItem])
def due(channel: str | None = None, conn=Depends(get_conn)):
    return [DueItem(**d) for d in seq.due_queue(conn, channel)]


@router.post("/{sid}/enroll")
def enroll(sid: int, req: EnrollRequest, conn=Depends(get_conn)):
    if seq.get_sequence(conn, sid) is None:
        raise HTTPException(status_code=404, detail="sequence not found")
    # Report the language refusals separately: "3 fewer than selected" reads as a
    # duplicate skip, and the user would try again instead of picking the right sequence.
    wrong_language = seq.language_blocked(conn, sid, req.lead_nos)
    enrolled = seq.enroll_leads(conn, sid, req.lead_nos)
    return {"enrolled": enrolled, "selected": len(req.lead_nos),
            "wrong_language": len(wrong_language)}


@router.post("/advance")
def advance(req: AdvanceRequest, conn=Depends(get_conn)):
    for eid in req.enrollment_ids:
        seq.advance_enrollment(conn, eid)
    return {"advanced": len(req.enrollment_ids)}


@router.post("/send")
def send_due(req: SendDueRequest, background: BackgroundTasks, conn=Depends(get_conn)):
    due_ids = {d["enrollment_id"] for d in seq.due_queue(conn)}
    targets = [e for e in req.enrollment_ids if e in due_ids]
    job_id = jobs.create(total=len(targets))
    background.add_task(_run_send, job_id, targets, req.image, database_path(conn))
    return {"job_id": job_id, "will_send": len(targets), "selected": len(req.enrollment_ids)}
