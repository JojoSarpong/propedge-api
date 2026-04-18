from contextlib import asynccontextmanager
import os
import sqlite3

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Header, HTTPException
from enrichment import init_reasoning_cache
from middleware.auth import APIKeyMiddleware, init_keys_db
from routes import props, keys


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_keys_db()
    init_reasoning_cache()
    yield


app = FastAPI(title="propedge-api", version="0.1.0", lifespan=lifespan)

app.add_middleware(APIKeyMiddleware)

app.include_router(props.router, prefix="/v1")
app.include_router(keys.router, prefix="/v1")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/admin/debug/db")
async def debug_db(x_debug_token: str = Header(default="")):
    """
    Returns raw settlement counts from slip_picks and hit_rates.
    Requires X-Debug-Token header matching DEBUG_TOKEN env var.
    """
    expected = os.getenv("DEBUG_TOKEN", "").strip()
    if not expected or x_debug_token != expected:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Debug-Token")

    db_path = os.getenv("DB_PATH", "/data/propedge.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 1. slip_picks settled counts by prop_type and result
    c.execute("""
        SELECT prop_type, result, COUNT(*) as n
        FROM slip_picks
        WHERE result IN ('HIT', 'MISS')
        GROUP BY prop_type, result
        ORDER BY prop_type, result
    """)
    slip_picks_breakdown = [dict(r) for r in c.fetchall()]

    # 2. Most recent hit_rates rows (table has no updated_at — use id DESC)
    c.execute("""
        SELECT * FROM hit_rates ORDER BY id DESC LIMIT 20
    """)
    hit_rates_recent = [dict(r) for r in c.fetchall()]

    # 3. slip_picks total count + earliest slip creation date
    c.execute("""
        SELECT COUNT(*) as total,
               (SELECT MIN(created_at) FROM slips) as earliest_slip_created_at
        FROM slip_picks
    """)
    slip_picks_summary = dict(c.fetchone())

    conn.close()
    return {
        "slip_picks_by_prop_and_result": slip_picks_breakdown,
        "hit_rates_recent_20":           hit_rates_recent,
        "slip_picks_summary":            slip_picks_summary,
    }
