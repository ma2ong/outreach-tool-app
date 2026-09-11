import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import delivery_intents, production_health, runtime
from app.main_deps import database_path, get_conn


router = APIRouter(prefix="/api/runtime", tags=["runtime"])


class DeliveryResolution(BaseModel):
    outcome: str


@router.get("/identity")
def identity():
    return {"app": "mcvisual-outreach-tool"}


@router.get("/status")
def worker_status(conn=Depends(get_conn)):
    data = runtime.status(conn)
    data["embedded_worker_enabled"] = os.environ.get("OUTREACH_EMBEDDED_WORKER", "1") != "0"
    data["dedicated_worker_expected"] = not data["embedded_worker_enabled"]
    data["capabilities"] = runtime.capability_status(conn)
    data["unresolved_deliveries"] = delivery_intents.unresolved(conn)
    data["production"] = production_health.status(conn, database_path(conn))
    return data


@router.post("/delivery-intents/{intent_id}/resolve")
def resolve_delivery(intent_id: int, req: DeliveryResolution, conn=Depends(get_conn)):
    try:
        return delivery_intents.resolve(conn, intent_id, req.outcome)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
