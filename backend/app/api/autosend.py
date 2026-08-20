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
    return autosend.status(conn)
