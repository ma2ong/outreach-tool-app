from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import mailboxes as mb, replies
from app.channels import email_adapter
from app.main_deps import get_conn

router = APIRouter(prefix="/api/mailboxes")


class MailboxCreate(BaseModel):
    email: str
    smtp_host: str
    port: int = 465
    imap_host: str | None = None
    imap_port: int = 993
    username: str
    password: str
    daily_cap: int = 40


class ActiveUpdate(BaseModel):
    active: bool


@router.get("")
def list_mailboxes(conn=Depends(get_conn)):
    return mb.list_mailboxes(conn)


@router.post("")
def create_mailbox(req: MailboxCreate, conn=Depends(get_conn)):
    if not req.email.strip() or not req.smtp_host.strip() or not req.password:
        raise HTTPException(status_code=400, detail="email, smtp_host and password required")
    if req.daily_cap < 1:
        raise HTTPException(status_code=400, detail="daily_cap must be >= 1")
    mid = mb.add_mailbox(conn, req.email.strip(), req.smtp_host.strip(), req.port,
                         (req.username or req.email).strip(), req.password, req.daily_cap,
                         (req.imap_host or mb.infer_imap_host(req.smtp_host)),
                         req.imap_port)
    return next(m for m in mb.list_mailboxes(conn) if m["id"] == mid)


@router.post("/{mid}/test")
def test_mailbox(mid: int, conn=Depends(get_conn)):
    """Verify both sending and reply-sync credentials without sending or reading mail."""
    row = conn.execute("SELECT * FROM mailboxes WHERE id=?", (mid,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="mailbox not found")
    try:
        email_adapter.test_mailbox(dict(row))
        replies.test_mailbox(dict(row))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"SMTP/IMAP 登录失败：{exc}")
    return {"ok": True, "smtp": True, "imap": True}


@router.patch("/{mid}")
def set_active(mid: int, req: ActiveUpdate, conn=Depends(get_conn)):
    if not mb.set_active(conn, mid, req.active):
        raise HTTPException(status_code=404, detail="mailbox not found")
    return {"ok": True}


@router.delete("/{mid}")
def delete_mailbox(mid: int, conn=Depends(get_conn)):
    if not mb.delete_mailbox(conn, mid):
        raise HTTPException(status_code=404, detail="mailbox not found")
    return {"ok": True}
