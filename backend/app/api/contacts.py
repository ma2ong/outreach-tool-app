from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import contacts
from app.main_deps import get_conn

router = APIRouter(prefix="/api/contacts")


class ContactCreate(BaseModel):
    lead_no: int
    name: str | None = None
    title: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    role: str = "other"
    note: str | None = None
    is_primary: bool = False


# docs/114：同一个人的另一个信箱 / 另一个号码。
class ChannelCreate(BaseModel):
    kind: str
    value: str
    # 地址已属于同公司另一个联系人时，前端确认「是同一个人」后带这个再来一次。
    merge: bool = False


class ContactUpdate(BaseModel):
    name: str | None = None
    title: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    role: str | None = None
    note: str | None = None


def _bad(exc: contacts.ContactValidation):
    raise HTTPException(status_code=400, detail=str(exc))


@router.get("")
def list_contacts(lead_no: int | None = None, conn=Depends(get_conn)):
    return contacts.list_all(conn, lead_no)


@router.get("/stats")
def contact_stats(conn=Depends(get_conn)):
    return contacts.stats(conn)


@router.post("")
def create_contact(req: ContactCreate, conn=Depends(get_conn)):
    try:
        return contacts.create(
            conn, req.lead_no,
            req.model_dump(exclude={"lead_no", "is_primary"}, exclude_none=True),
            is_primary=req.is_primary,
        )
    except contacts.ContactValidation as exc:
        _bad(exc)


@router.patch("/{contact_id}")
def update_contact(contact_id: int, req: ContactUpdate, conn=Depends(get_conn)):
    try:
        result = contacts.update(conn, contact_id, req.model_dump(exclude_unset=True))
    except contacts.ContactValidation as exc:
        _bad(exc)
    if result is None:
        raise HTTPException(status_code=404, detail="联系人不存在")
    return result


@router.post("/{contact_id}/channels")
def add_channel(contact_id: int, req: ChannelCreate, conn=Depends(get_conn)):
    try:
        return contacts.add_channel(conn, contact_id, req.kind, req.value)
    except contacts.ContactConflict as exc:
        if not req.merge:
            # 409 带上占着这个地址的是谁，前端才问得出「把他并过来吗」。
            raise HTTPException(status_code=409, detail={
                "message": str(exc), "contact_id": exc.contact_id,
                "contact_name": exc.contact_name,
            })
        try:
            merged = contacts.fold_into(conn, contact_id, exc.contact_id)
        except contacts.ContactValidation as bad:
            _bad(bad)
        if merged is None:
            raise HTTPException(status_code=404, detail="联系人不存在")
        return merged
    except contacts.ContactValidation as exc:
        _bad(exc)


@router.delete("/channels/{channel_id}")
def delete_channel(channel_id: int, conn=Depends(get_conn)):
    if not contacts.delete_channel(conn, channel_id):
        raise HTTPException(status_code=404, detail="联系方式不存在")
    return {"ok": True}


@router.post("/channels/{channel_id}/primary")
def promote_channel(channel_id: int, conn=Depends(get_conn)):
    result = contacts.promote_channel(conn, channel_id)
    if result is None:
        raise HTTPException(status_code=404, detail="联系方式不存在")
    return result


@router.post("/{contact_id}/primary")
def set_primary(contact_id: int, conn=Depends(get_conn)):
    result = contacts.set_primary(conn, contact_id)
    if result is None:
        raise HTTPException(status_code=404, detail="联系人不存在")
    return result


@router.delete("/{contact_id}")
def delete_contact(contact_id: int, conn=Depends(get_conn)):
    if not contacts.delete(conn, contact_id):
        raise HTTPException(status_code=404, detail="联系人不存在")
    return {"ok": True}
