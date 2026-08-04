from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import blocklist
from app.main_deps import get_conn

router = APIRouter(prefix="/api/blocklist")


class BlockRequest(BaseModel):
    value: str          # a domain, a website URL or an email address
    reason: str | None = None


@router.get("")
def list_blocked(conn=Depends(get_conn)):
    return blocklist.list_all(conn)


@router.post("")
def add_blocked(req: BlockRequest, conn=Depends(get_conn)):
    row = blocklist.add(conn, req.value, req.reason)
    if row is None:
        raise HTTPException(status_code=400, detail="这里面看不出域名，填公司官网或邮箱")
    return row


@router.delete("/{block_id}")
def remove_blocked(block_id: int, conn=Depends(get_conn)):
    if not blocklist.remove(conn, block_id):
        raise HTTPException(status_code=404, detail="not found")
    return {"ok": True}
