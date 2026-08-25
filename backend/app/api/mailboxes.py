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
    imap_enabled: bool = True


class ActiveUpdate(BaseModel):
    active: bool


class PasswordUpdate(BaseModel):
    password: str


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
                         req.imap_port, req.imap_enabled)
    return next(m for m in mb.list_mailboxes(conn) if m["id"] == mid)


@router.post("/{mid}/test")
def test_mailbox(mid: int, conn=Depends(get_conn)):
    """Verify the credentials this mailbox actually uses, without sending or reading mail.

    A send-only mailbox is not tested for IMAP: it is configured not to have any, so
    failing it there would report a broken mailbox that is working exactly as set up."""
    row = conn.execute("SELECT * FROM mailboxes WHERE id=?", (mid,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="mailbox not found")
    box = dict(row)
    # Say the plain thing first. NetEase answers an empty credential by closing the
    # socket, which surfaces as "Connection unexpectedly closed" — indistinguishable
    # from a network problem, and the reason this mailbox looked unreachable.
    if not box.get("password"):
        raise HTTPException(status_code=400,
                            detail="这个邮箱还没有密码：点「改密码」填入客户端授权码后再测试")
    imap = bool(box.get("imap_enabled", 1))
    try:
        email_adapter.test_mailbox(box)
        if imap:
            replies.test_mailbox(box)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400,
                            detail=f"{'SMTP/IMAP' if imap else 'SMTP'} 登录失败：{exc}")
    return {"ok": True, "smtp": True, "imap": imap}


@router.patch("/{mid}")
def set_active(mid: int, req: ActiveUpdate, conn=Depends(get_conn)):
    if not mb.set_active(conn, mid, req.active):
        raise HTTPException(status_code=404, detail="mailbox not found")
    return {"ok": True}


@router.put("/{mid}/password")
def set_password(mid: int, req: PasswordUpdate, conn=Depends(get_conn)):
    """Change one mailbox's credential in place, without deleting and re-adding it."""
    if not req.password.strip():
        raise HTTPException(status_code=400, detail="密码不能为空")
    if not mb.set_password(conn, mid, req.password.strip()):
        raise HTTPException(status_code=404, detail="mailbox not found")
    return {"ok": True}


@router.delete("/{mid}")
def delete_mailbox(mid: int, conn=Depends(get_conn)):
    if not mb.delete_mailbox(conn, mid):
        raise HTTPException(status_code=404, detail="mailbox not found")
    return {"ok": True}
