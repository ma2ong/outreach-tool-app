import datetime as dt
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app import case_library, quote
from app.main_deps import DB_PATH as _DB_PATH, get_conn

router = APIRouter(prefix="/api")

DB_PATH = _DB_PATH


def _quotes_dir() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(DB_PATH)), "quotes")


class ProductCreate(BaseModel):
    model: str
    pixel_pitch: str | None = None
    brightness: str | None = None
    use_case: str | None = None
    ref_price_sqm: str | None = None
    indoor_outdoor: str | None = None
    refresh_rate_hz: int | None = None
    maintenance_access: str | None = None
    cabinet_size: str | None = None
    control_system: str | None = None
    notes: str | None = None
    cabinet_width_mm: float | None = None
    cabinet_height_mm: float | None = None
    cabinet_resolution_w: int | None = None
    cabinet_resolution_h: int | None = None
    module_width_mm: float | None = None
    module_height_mm: float | None = None
    max_power_w_cabinet: float | None = None
    avg_power_w_cabinet: float | None = None
    agent_approved: bool = False


class ProductUpdate(BaseModel):
    model: str | None = None
    pixel_pitch: str | None = None
    brightness: str | None = None
    use_case: str | None = None
    ref_price_sqm: str | None = None
    indoor_outdoor: str | None = None
    refresh_rate_hz: int | None = None
    maintenance_access: str | None = None
    cabinet_size: str | None = None
    control_system: str | None = None
    notes: str | None = None
    cabinet_width_mm: float | None = None
    cabinet_height_mm: float | None = None
    cabinet_resolution_w: int | None = None
    cabinet_resolution_h: int | None = None
    module_width_mm: float | None = None
    module_height_mm: float | None = None
    max_power_w_cabinet: float | None = None
    avg_power_w_cabinet: float | None = None
    agent_approved: bool | None = None


class CaseCreate(BaseModel):
    internal_name: str
    public_label: str | None = None
    country: str | None = None
    application: str | None = None
    indoor_outdoor: str | None = None
    pixel_pitch: str | None = None
    width_m: float | None = None
    height_m: float | None = None
    product_model: str | None = None
    public_summary: str | None = None
    source_url: str | None = None
    shareable: bool = False


class CaseUpdate(BaseModel):
    internal_name: str | None = None
    public_label: str | None = None
    country: str | None = None
    application: str | None = None
    indoor_outdoor: str | None = None
    pixel_pitch: str | None = None
    width_m: float | None = None
    height_m: float | None = None
    product_model: str | None = None
    public_summary: str | None = None
    source_url: str | None = None
    shareable: bool | None = None


class QuoteRequest(BaseModel):
    product_ids: list[int]
    note: str = ""


_PRODUCT_FIELDS = (
    "model", "pixel_pitch", "brightness", "use_case", "ref_price_sqm",
    "indoor_outdoor", "refresh_rate_hz", "maintenance_access", "cabinet_size",
    "control_system", "notes", "cabinet_width_mm", "cabinet_height_mm",
    "cabinet_resolution_w", "cabinet_resolution_h", "module_width_mm",
    "module_height_mm", "max_power_w_cabinet", "avg_power_w_cabinet",
    "agent_approved",
)

_FLOAT_ENGINEERING_FIELDS = (
    "cabinet_width_mm", "cabinet_height_mm", "module_width_mm", "module_height_mm",
    "max_power_w_cabinet", "avg_power_w_cabinet",
)
_INT_ENGINEERING_FIELDS = ("cabinet_resolution_w", "cabinet_resolution_h")


def _clean_product(data: dict, *, partial: bool = False) -> dict:
    clean = {k: v for k, v in data.items() if k in _PRODUCT_FIELDS}
    if not partial or "model" in clean:
        model = str(clean.get("model") or "").strip()
        if not model:
            raise HTTPException(status_code=400, detail="model required")
        clean["model"] = model[:160]
    for field in (
        "pixel_pitch", "brightness", "use_case", "ref_price_sqm", "indoor_outdoor",
        "maintenance_access", "cabinet_size", "control_system", "notes",
    ):
        if field in clean:
            clean[field] = str(clean[field] or "").strip()[:1000] or None
    if clean.get("indoor_outdoor"):
        value = clean["indoor_outdoor"].lower()
        if value not in ("indoor", "outdoor"):
            raise HTTPException(status_code=400, detail="indoor_outdoor must be Indoor or Outdoor")
        clean["indoor_outdoor"] = value.title()
    if "refresh_rate_hz" in clean and clean["refresh_rate_hz"] is not None:
        try:
            refresh = int(clean["refresh_rate_hz"])
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="refresh_rate_hz must be an integer") from exc
        if not 240 <= refresh <= 20000:
            raise HTTPException(status_code=400, detail="refresh_rate_hz out of range")
        clean["refresh_rate_hz"] = refresh
    for field in _FLOAT_ENGINEERING_FIELDS:
        if field in clean and clean[field] is not None:
            try:
                value = float(clean[field])
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=400, detail=f"{field} must be numeric") from exc
            if value <= 0:
                raise HTTPException(status_code=400, detail=f"{field} must be > 0")
            clean[field] = value
    for field in _INT_ENGINEERING_FIELDS:
        if field in clean and clean[field] is not None:
            try:
                value = int(clean[field])
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=400, detail=f"{field} must be integer") from exc
            if value <= 0:
                raise HTTPException(status_code=400, detail=f"{field} must be > 0")
            clean[field] = value
    if (
        clean.get("avg_power_w_cabinet") is not None
        and clean.get("max_power_w_cabinet") is not None
        and clean["avg_power_w_cabinet"] > clean["max_power_w_cabinet"]
    ):
        raise HTTPException(status_code=400, detail="avg_power_w_cabinet cannot exceed max_power_w_cabinet")
    if "agent_approved" in clean:
        clean["agent_approved"] = int(bool(clean["agent_approved"]))
    return clean


def _case_bad(exc: case_library.CaseValidation):
    raise HTTPException(status_code=400, detail=str(exc))


@router.get("/products")
def list_products(conn=Depends(get_conn)):
    return [dict(r) for r in conn.execute("SELECT * FROM products ORDER BY id")]


@router.post("/products")
def create_product(req: ProductCreate, conn=Depends(get_conn)):
    clean = _clean_product(req.model_dump())
    fields = list(clean)
    cur = conn.execute(
        f"INSERT INTO products({','.join(fields)}) VALUES ({','.join('?' * len(fields))})",
        [clean[field] for field in fields],
    )
    conn.commit()
    return dict(conn.execute("SELECT * FROM products WHERE id=?", (cur.lastrowid,)).fetchone())


@router.patch("/products/{pid}")
def update_product(pid: int, req: ProductUpdate, conn=Depends(get_conn)):
    if conn.execute("SELECT 1 FROM products WHERE id=?", (pid,)).fetchone() is None:
        raise HTTPException(status_code=404, detail="product not found")
    clean = _clean_product(req.model_dump(exclude_unset=True), partial=True)
    if clean:
        current = dict(conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone())
        merged = {**current, **clean}
        if (
            merged.get("avg_power_w_cabinet") is not None
            and merged.get("max_power_w_cabinet") is not None
            and float(merged["avg_power_w_cabinet"]) > float(merged["max_power_w_cabinet"])
        ):
            raise HTTPException(status_code=400, detail="avg_power_w_cabinet cannot exceed max_power_w_cabinet")
        conn.execute(
            f"UPDATE products SET {', '.join(f'{field}=?' for field in clean)} WHERE id=?",
            [*clean.values(), pid],
        )
        conn.commit()
    return dict(conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone())


@router.post("/products/seed")
def seed_products(conn=Depends(get_conn)):
    """Load the default Maxcolor ranges as reference rows, never Agent-approved facts."""
    if conn.execute("SELECT 1 FROM products LIMIT 1").fetchone():
        raise HTTPException(status_code=400, detail="products already exist")
    for p in quote.DEFAULT_PRODUCTS:
        conn.execute(
            "INSERT INTO products(model, pixel_pitch, brightness, use_case, ref_price_sqm, agent_approved)"
            " VALUES (?, ?, ?, ?, ?, 0)",
            (p["model"], p["pixel_pitch"], p["brightness"], p["use_case"], p["ref_price_sqm"]))
    conn.commit()
    return {"seeded": len(quote.DEFAULT_PRODUCTS)}


@router.delete("/products/{pid}")
def delete_product(pid: int, conn=Depends(get_conn)):
    cur = conn.execute("DELETE FROM products WHERE id=?", (pid,))
    conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="product not found")
    return {"ok": True}


@router.get("/cases")
def list_cases(shareable: bool | None = None, limit: int = 100, conn=Depends(get_conn)):
    return case_library.list_all(conn, shareable=shareable, limit=limit)


@router.post("/cases")
def create_case(req: CaseCreate, conn=Depends(get_conn)):
    try:
        return case_library.create(conn, req.model_dump())
    except case_library.CaseValidation as exc:
        _case_bad(exc)


@router.patch("/cases/{case_id}")
def update_case(case_id: int, req: CaseUpdate, conn=Depends(get_conn)):
    try:
        result = case_library.update(conn, case_id, req.model_dump(exclude_unset=True))
    except case_library.CaseValidation as exc:
        _case_bad(exc)
    if result is None:
        raise HTTPException(status_code=404, detail="case not found")
    return result


@router.delete("/cases/{case_id}")
def delete_case(case_id: int, conn=Depends(get_conn)):
    if not case_library.delete(conn, case_id):
        raise HTTPException(status_code=404, detail="case not found")
    return {"ok": True}


@router.post("/quote")
def generate_quote(req: QuoteRequest, conn=Depends(get_conn)):
    if not req.product_ids:
        raise HTTPException(status_code=400, detail="pick at least one product")
    ph = ",".join("?" * len(req.product_ids))
    rows = [dict(r) for r in conn.execute(
        f"SELECT * FROM products WHERE id IN ({ph}) ORDER BY id", req.product_ids)]
    if not rows:
        raise HTTPException(status_code=404, detail="products not found")
    name = f"quote_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    path = quote.render_quote(rows, os.path.join(_quotes_dir(), name), note=req.note.strip())
    return {"file": name, "path": os.path.abspath(path)}


@router.get("/quote/file/{name}")
def quote_file(name: str):
    if "/" in name or "\\" in name or ".." in name:
        raise HTTPException(status_code=400, detail="bad name")
    path = os.path.join(_quotes_dir(), name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(path, media_type="image/png")
