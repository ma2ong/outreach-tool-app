from fastapi import APIRouter, Depends

from app import readiness
from app.main_deps import get_conn

router = APIRouter(prefix="/api/readiness")


@router.get("")
def get_readiness(conn=Depends(get_conn)):
    return readiness.build(conn)
