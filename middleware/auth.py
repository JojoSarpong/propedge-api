import os
import hashlib
import sqlite3
import time
import threading
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

RATE_LIMITS: dict[str, int] = {"free": 10, "pro": 60, "ultra": 500}

# RapidAPI subscription plan → internal tier
RAPIDAPI_PLAN_MAP: dict[str, str] = {
    "basic": "free",
    "pro": "pro",
    "ultra": "ultra",
}

# {key_hash: {"count": int, "window_start": float}}
_rate_store: dict[str, dict] = {}
_rate_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Keys DB helpers
# ---------------------------------------------------------------------------

def _keys_conn() -> sqlite3.Connection:
    path = os.environ.get("API_KEYS_DB_PATH", "")
    if not path:
        raise RuntimeError("API_KEYS_DB_PATH is not set")
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_keys_db() -> None:
    conn = _keys_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            key_hash     TEXT    NOT NULL UNIQUE,
            tier         TEXT    NOT NULL DEFAULT 'free',
            owner_email  TEXT    NOT NULL,
            created_at   TEXT    NOT NULL,
            last_used_at TEXT,
            is_active    INTEGER NOT NULL DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()


def lookup_key(key_hash: str) -> sqlite3.Row | None:
    conn = _keys_conn()
    try:
        return conn.execute(
            "SELECT id, tier, is_active FROM api_keys WHERE key_hash = ?",
            (key_hash,),
        ).fetchone()
    finally:
        conn.close()


def touch_last_used(key_hash: str) -> None:
    conn = _keys_conn()
    try:
        conn.execute(
            "UPDATE api_keys SET last_used_at = ? WHERE key_hash = ?",
            (datetime.now(timezone.utc).isoformat(), key_hash),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

def _allow_request(key_hash: str, tier: str) -> bool:
    limit = RATE_LIMITS.get(tier, 10)
    now = time.monotonic()
    with _rate_lock:
        entry = _rate_store.get(key_hash)
        if entry is None or now - entry["window_start"] >= 86400:
            _rate_store[key_hash] = {"count": 1, "window_start": now}
            return True
        if entry["count"] >= limit:
            return False
        entry["count"] += 1
        return True


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc", "/v1/keys/provision"}

STATUS_THROTTLE_LIMIT = 60
STATUS_THROTTLE_WINDOW = 60

# {ip: {"count": int, "window_start": float}}
_status_rate_store: dict[str, dict] = {}
_status_rate_lock = threading.Lock()


def _allow_status_request(ip: str) -> bool:
    now = time.monotonic()
    with _status_rate_lock:
        entry = _status_rate_store.get(ip)
        if entry is None or now - entry["window_start"] >= STATUS_THROTTLE_WINDOW:
            _status_rate_store[ip] = {"count": 1, "window_start": now}
            return True
        if entry["count"] >= STATUS_THROTTLE_LIMIT:
            return False
        entry["count"] += 1
        return True


def _handle_rapidapi(request: Request) -> JSONResponse | None:
    """
    Validates a RapidAPI-proxied request.
    Returns a JSONResponse error if validation fails, or None to allow through.
    Sets request.state.key_tier on success.
    """
    expected_secret = os.environ.get("RAPIDAPI_PROXY_SECRET", "")
    incoming_secret = request.headers.get("X-RapidAPI-Proxy-Secret", "")

    if not expected_secret or incoming_secret != expected_secret:
        return JSONResponse({"detail": "Invalid RapidAPI proxy secret"}, status_code=403)

    plan = request.headers.get("X-RapidAPI-Subscription-Plan", "").lower()
    tier = RAPIDAPI_PLAN_MAP.get(plan, "free")

    rapid_user = request.headers.get("X-RapidAPI-User", "rapidapi-unknown")
    rate_key = f"rapidapi:{rapid_user}"

    if not _allow_request(rate_key, tier):
        limit = RATE_LIMITS.get(tier, 10)
        return JSONResponse(
            {"detail": f"Rate limit exceeded ({limit} req/day for {tier} tier)"},
            status_code=429,
        )

    request.state.key_tier = tier
    return None


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/v1/props/today/status":
            ip = request.client.host if request.client else "unknown"
            if not _allow_status_request(ip):
                return JSONResponse(
                    {"detail": f"Rate limit exceeded ({STATUS_THROTTLE_LIMIT} req/{STATUS_THROTTLE_WINDOW}s)"},
                    status_code=429,
                )
            return await call_next(request)

        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        if request.headers.get("X-RapidAPI-Proxy-Secret"):
            error = _handle_rapidapi(request)
            if error:
                return error
            return await call_next(request)

        raw_key = request.headers.get("X-API-Key")
        if not raw_key:
            return JSONResponse({"detail": "Missing X-API-Key header"}, status_code=401)

        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        row = lookup_key(key_hash)

        if row is None or not row["is_active"]:
            return JSONResponse({"detail": "Invalid or inactive API key"}, status_code=401)

        tier: str = row["tier"]

        if not _allow_request(key_hash, tier):
            limit = RATE_LIMITS.get(tier, 10)
            return JSONResponse(
                {"detail": f"Rate limit exceeded ({limit} req/min for {tier} tier)"},
                status_code=429,
            )

        touch_last_used(key_hash)
        request.state.key_tier = tier
        return await call_next(request)
