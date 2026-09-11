from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import mailboxes as mb, replies, settings
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


class TestSend(BaseModel):
    to: str


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
    import datetime as dt
    settings.set_value(conn, f"mailbox_test_success:{mid}", dt.datetime.now(dt.UTC).isoformat())
    return {"ok": True, "smtp": True, "imap": imap}


@router.patch("/{mid}")
def set_active(mid: int, req: ActiveUpdate, conn=Depends(get_conn)):
    if not mb.set_active(conn, mid, req.active):
        raise HTTPException(status_code=404, detail="mailbox not found")
    return {"ok": True}


def _real_first_touch(conn) -> tuple[str, str, dict]:
    """The actual opening email, rendered against a real lead.

    A deliverability score is only worth having on the message customers really get: a
    mail reading "test" scores differently on content, wording and links than the first
    touch does, and it is the first touch whose score we need.
    """
    from app.personalize import render

    step = conn.execute(
        "SELECT st.subject, st.body FROM sequence_steps st JOIN sequences s ON s.id=st.sequence_id"
        " WHERE s.channel='email' AND s.active=1 AND st.step_order=0 ORDER BY s.id LIMIT 1"
    ).fetchone()
    if step is None:
        raise HTTPException(status_code=400, detail="没有可用的邮件序列，取不到真实开发信内容")
    row = conn.execute(
        "SELECT no, company_en, country, city, website, hook, contact_name FROM leads"
        " WHERE COALESCE(hook,'') != '' AND COALESCE(company_en,'') != ''"
        " ORDER BY no LIMIT 1").fetchone()
    lead = dict(row) if row else {"no": 0, "company_en": "Example AV", "country": "USA",
                                  "city": "Houston, TX", "website": "example.com",
                                  "hook": "Saw the rental work on your site."}
    return render(step["subject"], lead), render(step["body"], lead), lead


@router.post("/{mid}/send-test")
def send_test(mid: int, req: TestSend, conn=Depends(get_conn)):
    """Send one real opening email to an address you control, to measure deliverability.

    Not counted against the daily cap and not written to send_log: nobody was prospected
    here. It goes out through the same mailbox, renderer and SMTP path as a customer
    mail, because anything else would be measuring a different message.
    """
    from app import message_guard

    to = req.to.strip()
    if "@" not in to or to.startswith("@") or to.endswith("@"):
        raise HTTPException(status_code=400, detail="收件地址不正确")
    row = conn.execute("SELECT * FROM mailboxes WHERE id=?", (mid,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="mailbox not found")
    box = dict(row)
    if not box.get("password"):
        raise HTTPException(status_code=400, detail="这个邮箱还没有密码：点「改密码」填入后再发测试信")
    subject, body, lead = _real_first_touch(conn)
    try:
        email_adapter.send_via(box, to, subject, body, None)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"发送失败：{exc}") from exc
    # What our own outbound guard makes of this copy. It does not block the test — the
    # recipient is not a customer — but a first touch it would hold is worth seeing here.
    verdict = message_guard.check(body, lead, subject=subject)
    return {"ok": True, "to": to, "from": box["email"], "subject": subject,
            "sample_company": lead.get("company_en"),
            "guard_blocked": verdict.blocked, "guard_detail": verdict.detail}


@router.put("/{mid}/password")
def set_password(mid: int, req: PasswordUpdate, conn=Depends(get_conn)):
    """Change one mailbox's credential in place, without deleting and re-adding it."""
    if not req.password.strip():
        raise HTTPException(status_code=400, detail="密码不能为空")
    if not mb.set_password(conn, mid, req.password.strip()):
        raise HTTPException(status_code=404, detail="mailbox not found")
    conn.execute("DELETE FROM settings WHERE key=?", (f"mailbox_test_success:{mid}",))
    conn.commit()
    return {"ok": True}


@router.delete("/{mid}")
def delete_mailbox(mid: int, conn=Depends(get_conn)):
    if not mb.delete_mailbox(conn, mid):
        raise HTTPException(status_code=404, detail="mailbox not found")
    return {"ok": True}
