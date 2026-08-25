from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from app import jobs, sequence_send
from app import sequences as seq
from app.api import channels as channels_api
from app.api import send as send_api
from app.db import connect
from app.main_deps import DB_PATH, get_conn
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


class EnrollRequest(BaseModel):
    lead_nos: list[int]


class AdvanceRequest(BaseModel):
    enrollment_ids: list[int]


class SendDueRequest(BaseModel):
    enrollment_ids: list[int]
    image: str | None = send_api.DEFAULT_ATTACHMENT


def _run_send(job_id: str, enrollment_ids: list[int], image: str | None):
    conn = connect(DB_PATH)
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
    sid = seq.create_sequence(conn, req.name.strip(), req.channel,
                              [s.model_dump() for s in req.steps])
    return Sequence(**seq.get_sequence(conn, sid))


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
    background.add_task(_run_send, job_id, targets, req.image)
    return {"job_id": job_id, "will_send": len(targets), "selected": len(req.enrollment_ids)}
