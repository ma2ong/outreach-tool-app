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
