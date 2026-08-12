from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app import sales_documents
from app.main_deps import get_conn


router = APIRouter(prefix="/api/sales")


class QuoteItemInput(BaseModel):
    description: str = ""
    model: str | None = None
    pixel_pitch: str | None = None
    width_m: float | None = None
    height_m: float | None = None
    quantity: int = 1
    pricing_unit: str = "sqm"
    unit_price: float
    note: str | None = None


class QuoteCreate(BaseModel):
    lead_no: int
    opportunity_id: int | None = None
    contact_id: int | None = None
    title: str
    currency: str = "USD"
    incoterm: str | None = None
    destination: str | None = None
    valid_until: str | None = None
    payment_terms: str | None = None
    lead_time: str | None = None
    warranty: str | None = None
    shipping: float = 0
    discount: float = 0
    items: list[QuoteItemInput] = Field(min_length=1)


class QuoteUpdate(BaseModel):
    opportunity_id: int | None = None
    contact_id: int | None = None
    title: str | None = None
    currency: str | None = None
    incoterm: str | None = None
    destination: str | None = None
    valid_until: str | None = None
    payment_terms: str | None = None
    lead_time: str | None = None
    warranty: str | None = None
    shipping: float | None = None
    discount: float | None = None
    items: list[QuoteItemInput] | None = None


class QuoteStatusUpdate(BaseModel):
    status: str


class OrderUpdate(BaseModel):
    status: str | None = None
    deposit_amount: float | None = None
    paid_amount: float | None = None
    expected_ship_date: str | None = None
    shipped_at: str | None = None
    tracking_no: str | None = None
    note: str | None = None


def _bad(exc: ValueError):
    raise HTTPException(status_code=400, detail=str(exc))


@router.get("/quotes")
def list_quotes(status: str | None = None, lead_no: int | None = None,
                opportunity_id: int | None = None, conn=Depends(get_conn)):
    try:
        return sales_documents.list_quotes(
            conn, status=status, lead_no=lead_no, opportunity_id=opportunity_id
        )
    except ValueError as exc:
        _bad(exc)


@router.post("/quotes")
def create_quote(req: QuoteCreate, conn=Depends(get_conn)):
    payload = req.model_dump(exclude={"lead_no", "items"})
    try:
        return sales_documents.create_quote(
            conn, req.lead_no, payload, [item.model_dump() for item in req.items]
        )
    except ValueError as exc:
        _bad(exc)


@router.get("/quotes/{quote_id}")
def get_quote(quote_id: int, conn=Depends(get_conn)):
    result = sales_documents.get_quote(conn, quote_id)
    if result is None:
        raise HTTPException(status_code=404, detail="报价不存在")
    return result


@router.patch("/quotes/{quote_id}")
def update_quote(quote_id: int, req: QuoteUpdate, conn=Depends(get_conn)):
    data = req.model_dump(exclude_unset=True, exclude={"items"})
    items = (
        [item.model_dump() for item in req.items]
        if "items" in req.model_fields_set and req.items is not None else None
    )
    try:
        result = sales_documents.update_quote(conn, quote_id, data, items)
    except ValueError as exc:
        _bad(exc)
    if result is None:
        raise HTTPException(status_code=404, detail="报价不存在")
    return result


@router.post("/quotes/{quote_id}/status")
def update_quote_status(quote_id: int, req: QuoteStatusUpdate, conn=Depends(get_conn)):
    try:
        result = sales_documents.set_quote_status(conn, quote_id, req.status)
    except ValueError as exc:
        _bad(exc)
    if result is None:
        raise HTTPException(status_code=404, detail="报价不存在")
    return result


@router.get("/quotes/{quote_id}/print", response_class=HTMLResponse)
def print_quote(quote_id: int, conn=Depends(get_conn)):
    result = sales_documents.print_quote_html(conn, quote_id)
    if result is None:
        raise HTTPException(status_code=404, detail="报价不存在")
    return HTMLResponse(result)


@router.post("/quotes/{quote_id}/order")
def convert_quote_to_order(quote_id: int, conn=Depends(get_conn)):
    try:
        return sales_documents.create_order(conn, quote_id)
    except ValueError as exc:
        _bad(exc)


@router.get("/orders")
def list_orders(status: str | None = None, lead_no: int | None = None,
                conn=Depends(get_conn)):
    try:
        return sales_documents.list_orders(conn, status=status, lead_no=lead_no)
    except ValueError as exc:
        _bad(exc)


@router.get("/orders/{order_id}")
def get_order(order_id: int, conn=Depends(get_conn)):
    result = sales_documents.get_order(conn, order_id)
    if result is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    return result


@router.patch("/orders/{order_id}")
def update_order(order_id: int, req: OrderUpdate, conn=Depends(get_conn)):
    try:
        result = sales_documents.update_order(conn, order_id, req.model_dump(exclude_unset=True))
    except ValueError as exc:
        _bad(exc)
    if result is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    return result
