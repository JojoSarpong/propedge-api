from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from database import get_slate, get_slate_status
from enrichment import get_reasoning
from models.schemas import PickResponse, PropListResponse, SlateStatusResponse

router = APIRouter(tags=["props"])

_REASONING_TIERS = {"pro", "ultra"}


def _row_to_pick(p: dict, reasoning: str | None = None) -> PickResponse:
    return PickResponse(
        player=p["player_name"],
        prop=p["prop_type"],
        line=p["line"],
        side=p["side"],
        hit_probability=p["hit_probability"],
        edge_pct=p["edge_pct"],
        tier=p["confidence_tier"],
        reasoning=reasoning,
    )


@router.get("/props/today", response_model=PropListResponse, response_model_exclude_none=True)
def get_props_today(
    request: Request,
    sport: str = Query(..., description="Sport slug, e.g. tennis or nba"),
    tier: Optional[Literal["STRONG", "SOLID", "LEAN", "SKIP"]] = Query(None, description="Filter by tier: STRONG, SOLID, LEAN, SKIP"),
):
    try:
        slate = get_slate(sport=sport, tier=tier)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    key_tier = getattr(request.state, "key_tier", "free")
    enrich = key_tier in _REASONING_TIERS

    picks = []
    for p in slate["picks"]:
        reasoning = get_reasoning(p, slate["date"]) if enrich else None
        picks.append(_row_to_pick(p, reasoning=reasoning))

    return PropListResponse(
        date=slate["date"],
        sport=sport,
        generated_at=slate["generated_at"],
        picks=picks,
    )


@router.get("/props/today/status", response_model=SlateStatusResponse)
def get_props_today_status(
    sport: str = Query(..., description="Sport slug, e.g. tennis or nba"),
):
    try:
        status = get_slate_status(sport=sport)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return SlateStatusResponse(
        sport=sport,
        date=status.get("date", ""),
        status=status.get("status", "unknown"),
        pick_count=status.get("pick_count", 0),
        generated_at=None,
    )
