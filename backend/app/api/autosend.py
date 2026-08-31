from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import autosend, mailboxes
from app.channels.email_adapter import get_password
from app.main_deps import get_conn

router = APIRouter(prefix="/api/autosend")


class AutoSendUpdate(BaseModel):
    enabled: bool
    acknowledge_safety_risk: bool = False


@router.get("/status")
def get_status(conn=Depends(get_conn)):
    return autosend.status(conn)


@router.get("/plan")
def get_plan(conn=Depends(get_conn)):
    """Today's email plan: who, what, when, and what is being held back and why.

    The same questions the social DM page answers. This lived as one line of small print
    on the dashboard, which is why Allen asked where the email plan was (docs/66 R5).
    """
    import datetime as dt

    from app import local_time, message_guard, sequences
    from app.outreach import render

    now = dt.datetime.now(dt.UTC)
    rows, held = [], []
    for item in sequences.due_queue(conn, "email"):
        lead = conn.execute(
            "SELECT no, company_en, company_local, country, email, hook, contact_name,"
            " tags FROM leads WHERE no=?", (item["lead_no"],)).fetchone()
        if lead is None:
            continue
        allowed, why = local_time.may_email(item.get("_lead_country"), now)
        body = render(item.get("body") or "", dict(lead))
        subject = render(item.get("subject") or "", dict(lead))
        verdict = message_guard.check(
            body, dict(lead), subject=subject, step_order=item.get("step_order", 0))
        entry = {
            "lead_no": lead["no"], "company": lead["company_en"],
            "country": lead["country"], "email": lead["email"],
            "sequence": item.get("sequence_name"), "step": item.get("step_order"),
            "subject": subject, "body": body,
            "local_time": (local_time.local_now(lead["country"], now) or now).strftime("%m-%d %H:%M"),
        }
        if verdict.blocked:
            held.append({**entry, "reason": verdict.detail or verdict.reason})
        elif allowed:
            rows.append(entry)
        else:
            held.append({**entry, "reason": why})

    status = autosend.status(conn)
    # Allen looked at 「待发 1 封」 and asked why the day was so thin. It was not thin:
    # sixty had already gone out that morning and the budget was spent. The page could
    # not say so, because the only numbers it had were what remained. Say what was sent
    # and what is left, so the answer is on the page instead of in a question.
    from app import outreach as _outreach
    sent = _outreach.sent_today(conn)
    left = _outreach.remaining_today(conn)
    return {
        "ready": rows, "held": held,
        "his_window": list(autosend.WINDOW),
        "their_window": list(local_time.EMAIL_WINDOW),
        "status": status,
        "budget": {"sent_today": sent, "remaining": left, "cap": sent + left},
    }


@router.patch("")
def update_status(req: AutoSendUpdate, conn=Depends(get_conn)):
    if req.enabled and not (mailboxes.has_active(conn) or get_password()):
        raise HTTPException(
            status_code=400,
            detail="请先配置并测试至少一个邮箱，再启用自动发送",
        )
    pause = autosend.safety_pause(conn)
    if req.enabled and pause and not req.acknowledge_safety_risk:
        raise HTTPException(
            status_code=409,
            detail=f"邮件因安全风险暂停：{pause['reason']}。请阅读风险并明确确认后再恢复。",
        )
    autosend.set_enabled(conn, req.enabled)
    if req.enabled and pause:
        # He was shown this pause's reason and evidence and confirmed anyway. Without
        # recording that, the next agent run re-pauses and his decision never lands.
        autosend.acknowledge(conn, pause)
    return autosend.status(conn)
