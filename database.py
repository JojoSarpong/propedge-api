import os
from typing import Optional

import httpx


def _backend_url() -> str:
    url = os.environ.get("PROPEDGE_BACKEND_URL", "").rstrip("/")
    if not url:
        raise RuntimeError("PROPEDGE_BACKEND_URL is not set")
    return url


def get_slate(sport: str, tier: Optional[str] = None) -> dict:
    """
    Calls GET {PROPEDGE_BACKEND_URL}/api/v1/slate/{sport}/prizepicks/today
    Returns {"sport", "date", "generated_at", "picks": [...]}.
    Tier filter is applied client-side.
    """
    url = f"{_backend_url()}/api/v1/slate/{sport}/prizepicks/today"
    try:
        resp = httpx.get(url, timeout=10)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError("PropEdge backend unavailable")

    data = resp.json()
    picks = data.get("picks", [])
    if tier:
        picks = [p for p in picks if p.get("confidence_tier", "").upper() == tier.upper()]

    return {
        "sport": sport,
        "date": data.get("date", ""),
        "generated_at": data.get("generated_at", ""),
        "picks": picks,
    }


def get_slate_status(sport: str) -> dict:
    """
    Calls GET {PROPEDGE_BACKEND_URL}/api/v1/slate/status
    Returns {"status", "pick_count", "date"}.
    """
    url = f"{_backend_url()}/api/v1/slate/status"
    try:
        resp = httpx.get(url, timeout=10)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError("PropEdge backend unavailable")

    return resp.json()
