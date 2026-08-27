from fastapi import APIRouter, Depends, HTTPException

from app import campaigns
from app import repository as repo
from app.main_deps import get_conn
from app.models import Stats

router = APIRouter(prefix="/api")


@router.get("/stats", response_model=Stats)
def get_stats(conn=Depends(get_conn)):
    return repo.stats(conn)


@router.get("/stats/campaigns")
def get_campaign_stats(conn=Depends(get_conn)):
    return {"campaigns": campaigns.campaign_stats(conn),
            "countries": campaigns.country_stats(conn)}


@router.get("/stats/quality")
def get_quality_stats(conn=Depends(get_conn)):
    """Is the outreach reaching anyone worth reaching, and is it arriving at all?"""
    return {"quality": campaigns.quality_stats(conn),
            "deliverability": campaigns.deliverability(conn),
            "danger_pct": campaigns.BOUNCE_DANGER_PCT}

@router.get("/stats/copy-experiments")
def copy_experiments(by: str = "variant,market", days: int = 90, conn=Depends(get_conn)):
    """Reply rate cut by whichever dimensions you ask for (docs/69).

    The one number that existed before — "361 sent, 1 reply" — could not say whether the
    opener was weak, the list wrong, or the third letter the one that burns people.
    """
    from app import copy_experiments as ce

    keys = tuple(k.strip() for k in by.split(",") if k.strip())
    try:
        rows = ce.breakdown(conn, keys, days=days)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"by": list(keys), "days": days, "rows": rows,
            "unmeasured": ce.unmeasured(conn, days),
            "dimensions": list(ce.DIMENSIONS)}
