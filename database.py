import os
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

import httpx

_ET = ZoneInfo("America/New_York")


def _backend_url() -> str:
    url = os.environ.get("PROPEDGE_BACKEND_URL", "").rstrip("/")
    if not url:
        raise RuntimeError("PROPEDGE_BACKEND_URL is not set")
    return url


def _et_today() -> str:
    """Return today's date string (YYYY-MM-DD) in US Eastern time."""
    return datetime.now(_ET).strftime("%Y-%m-%d")


def get_slate(sport: str, tier: Optional[str] = None) -> dict:
    """
    Calls GET {PROPEDGE_BACKEND_URL}/api/v1/slate/{sport}/prizepicks/today
    Passes ?date= in ET so the backend's date filter matches the cron's date.
    Returns {"sport", "date", "generated_at", "picks": [...]}.
    Tier filter is applied client-side.
    """
    url = f"{_backend_url()}/api/v1/slate/{sport}/prizepicks/today"
    try:
        resp = httpx.get(url, params={"date": _et_today()}, timeout=10)
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
