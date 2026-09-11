"""Today's social DM queue: read it, fix it, send it.

Sending is a separate request that a person makes. There is no scheduler here and no
background job that reaches this table on its own — that boundary is the whole point of
`docs/52`, and of the `AGENTS.md` rule it works around rather than removes.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from app import channel_outreach, jobs, social_autonomy, social_queue
from app.api import channels as channels_api
from app.api import send as send_api
from app.main_deps import database_path, get_conn

router = APIRouter(prefix="/api/social-queue")


class EditRequest(BaseModel):
    body: str


class SendRequest(BaseModel):
    ids: list[int]


class ModeRequest(BaseModel):
    channel: str
    mode: str
    confirm: str = ""


@router.get("")
def read_queue(conn=Depends(get_conn)):
    rows = social_queue.today(conn)
    return {"date": social_queue.sales_day(), "items": rows,
            # What the dashboard counts. A row on an `auto` channel is not waiting for
            # him, and saying it was is half of why six silent days went unnoticed
            # (docs/92 R6).
            "awaiting_you": social_queue.awaiting_you(conn),
            "per_channel": {c: sum(1 for r in rows if r["channel"] == c)
                            for c in social_queue.CHANNELS}}


@router.get("/autonomy")
def read_autonomy(conn=Depends(get_conn)):
    """Per-channel mode, plus what today's automatic run did (if it ran)."""
    return {"modes": social_autonomy.all_modes(conn),
            "last_run": social_autonomy.last_run(conn)}


@router.put("/autonomy")
def set_autonomy(req: ModeRequest, conn=Depends(get_conn)):
    """Raising a channel to `auto` costs typing its name — it spends an account that
    cannot be recovered, and a yes/no dialog gets answered reflexively."""
    try:
        mode = social_autonomy.set_mode(conn, req.channel, req.mode, req.confirm)
    except social_autonomy.ConfirmationRequired as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"channel": req.channel, "mode": mode}


@router.post("/build")
def build_queue(conn=Depends(get_conn)):
    """Prepare (or refresh) today's queue. Writes rows; sends nothing."""
    return social_queue.build_today(conn)


@router.patch("/{queue_id}")
def edit_item(queue_id: int, req: EditRequest, conn=Depends(get_conn)):
    if not social_queue.edit(conn, queue_id, req.body):
        raise HTTPException(status_code=404, detail="这条已发送或不存在")
    return {"ok": True}


@router.delete("/{queue_id}")
def drop_item(queue_id: int, conn=Depends(get_conn)):
    if not social_queue.drop(conn, queue_id):
        raise HTTPException(status_code=404, detail="这条已发送或不存在")
    return {"ok": True}


@router.post("/{queue_id}/no-whatsapp")
def mark_no_whatsapp(queue_id: int, conn=Depends(get_conn)):
    """He saw WhatsApp say this number has no account. Keep it (docs/108 R1)."""
    if not social_queue.mark_no_whatsapp(conn, queue_id):
        raise HTTPException(status_code=404, detail="这条不是待发的 WhatsApp，或已经不在队列里")
    return {"ok": True}


def _run_send(job_id: str, db_path: str, items: list[dict]) -> None:
    from app.db import connect

    conn = connect(db_path)
    try:
        result = channel_outreach.send_prepared(
            conn, items, channels_api.ENGINE, image=send_api.DEFAULT_ATTACHMENT,
            campaign="每日社媒队列",
            on_progress=lambda done, total: jobs.update(job_id, done))
        # Which ones went, not how many — the same slice bug as run_due (docs/102 R1).
        sent_ids = list(result.get("sent_ids") or [])
        if sent_ids:
            placeholders = ",".join("?" * len(sent_ids))
            conn.execute(
                f"UPDATE social_dm_queue SET status='sent' WHERE id IN ({placeholders})",
                sent_ids)
            conn.commit()
        jobs.finish(job_id, result)
    except Exception as exc:  # noqa: BLE001
        jobs.fail(job_id, str(exc))
    finally:
        conn.close()


@router.post("/send")
def send_queue(req: SendRequest, background: BackgroundTasks, conn=Depends(get_conn)):
    """Send the rows Allen confirmed. The one place in this feature that reaches a customer."""
    if not req.ids:
        raise HTTPException(status_code=400, detail="没有选中任何一条")
    placeholders = ",".join("?" * len(req.ids))
    rows = conn.execute(
        f"SELECT id, lead_no, channel, target, body FROM social_dm_queue"
        f" WHERE id IN ({placeholders}) AND queue_date=? AND status='ready'"
        f" ORDER BY rank_order", [*req.ids, social_queue.sales_day()]).fetchall()
    items = [dict(r) for r in rows]
    if not items:
        raise HTTPException(status_code=400, detail="选中的条目已发送或已不在今天的队列里")
    job_id = jobs.create(total=len(items))
    background.add_task(_run_send, job_id, database_path(conn), items)
    return {"job_id": job_id, "will_send": len(items)}
