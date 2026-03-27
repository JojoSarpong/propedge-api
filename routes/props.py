from datetime import date as date_type
from typing import Optional

from fastapi import APIRouter, Query, Request, HTTPException

from database import get_picks, get_slate_status
from models.schemas import PickResponse, PropListResponse, SlateStatusResponse

router = APIRouter(tags=["props"])


def _today() -> str:
    return date_type.today().isoformat()


def _row_to_pick(row: dict) -> PickResponse:
    return PickResponse(
        player=row["player"],
        prop=row["prop"],
        line=row["line"],
        side=row["side"],
        hit_probability=row["hit_probability"],
        edge_pct=row["edge_pct"],
        tier=row["tier"],
        reasoning=row["reasoning"],
    )


@router.get("/props/today", response_model=PropListResponse)
def get_props_today(
    request: Request,
    sport: str = Query(..., description="Sport slug, e.g. tennis or nba"),
    tier: Optional[str] = Query(None, description="Filter by tier: STRONG, LEAN, etc."),
):
    today = _today()
    try:
        rows = get_picks(sport=sport, date=today, tier=tier)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    slate = None
    try:
        slate = get_slate_status(sport=sport, date=today)
    except RuntimeError:
        pass

    generated_at = slate["created_at"] if slate else today

    return PropListResponse(
        date=today,
        sport=sport,
        generated_at=generated_at,
        picks=[_row_to_pick(r) for r in rows],
    )


@router.get("/props/today/status", response_model=SlateStatusResponse)
def get_slate_status_route(
    sport: str = Query(..., description="Sport slug, e.g. tennis or nba"),
):
    today = _today()
    try:
        slate = get_slate_status(sport=sport, date=today)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if slate is None:
        return SlateStatusResponse(
            sport=sport,
            date=today,
            status="not_generated",
            pick_count=0,
            generated_at=None,
        )

    return SlateStatusResponse(
        sport=sport,
        date=today,
        status=slate.get("status", "unknown"),
        pick_count=slate.get("pick_count", 0),
        generated_at=slate.get("created_at"),
    )
