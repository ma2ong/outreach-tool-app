from fastapi import APIRouter, Depends, HTTPException

from app import replies
from app.main_deps import get_conn

router = APIRouter(prefix="/api/replies")

# Injectable seam for tests; signature: (mailbox, since_days) -> messages.
FETCHER = replies.fetch_mailbox_messages


@router.post("/poll")
def poll(since_days: int = 7, conn=Depends(get_conn)):
    try:
        return replies.poll_all_replies(conn, fetcher=FETCHER, since_days=since_days)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
