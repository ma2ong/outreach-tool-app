from fastapi import APIRouter, Depends, HTTPException

from app import inbound, replies
from app.main_deps import get_conn

router = APIRouter(prefix="/api/replies")

# Injectable seam for tests; signature: (mailbox, since_days) -> messages.
FETCHER = replies.fetch_mailbox_messages


@router.post("/poll")
def poll(since_days: int | None = None, conn=Depends(get_conn)):
    try:
        return replies.poll_all_replies(conn, fetcher=FETCHER, since_days=since_days)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/scan")
def scan_social(channel: str | None = None, conn=Depends(get_conn)):
    """Read WhatsApp / Instagram thread lists for inbound messages.

    Requires the channel to be connected: launching a browser window as a side effect
    of a scan would be a surprise, and a logged-out session silently returns nothing,
    which would read as 'no replies' — the exact false-negative this fixes."""
    from app.api.channels import ENGINE
    targets = [channel] if channel else list(inbound.CHANNELS)
    for ch in targets:
        if ch not in inbound.CHANNELS:
            raise HTTPException(status_code=400, detail=f"不支持的渠道：{ch}")
    live = [ch for ch in targets if ENGINE.status(ch) == "connected"]
    if not live:
        raise HTTPException(
            status_code=400,
            detail="WhatsApp / Instagram 都没有连接。请先到「渠道」页连接并扫码登录，再回来扫描。")
    result = inbound.scan_all(conn, ENGINE.scan_threads, channels=live)
    result["skipped"] = [ch for ch in targets if ch not in live]
    return result


@router.get("/scan/status")
def scan_status(conn=Depends(get_conn)):
    return inbound.status(conn)
