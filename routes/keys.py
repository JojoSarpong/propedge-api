import hashlib
import os
import secrets
from datetime import datetime, timezone

import sqlite3
from fastapi import APIRouter, Header, HTTPException

from models.schemas import KeyProvisionRequest, KeyProvisionResponse

router = APIRouter(tags=["keys"])


def _keys_conn() -> sqlite3.Connection:
    path = os.environ.get("API_KEYS_DB_PATH", "")
    if not path:
        raise RuntimeError("API_KEYS_DB_PATH is not set")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


@router.post("/keys/provision", response_model=KeyProvisionResponse)
def provision_key(
    body: KeyProvisionRequest,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
):
    try:
        admin_secret = os.environ.get("ADMIN_SECRET", "")
        if not admin_secret or x_admin_secret != admin_secret:
            raise HTTPException(status_code=403, detail="Invalid admin secret")

        raw_key = "pe_" + secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        created_at = datetime.now(timezone.utc).isoformat()

        conn = _keys_conn()
        try:
            conn.execute(
                """
                INSERT INTO api_keys (key_hash, tier, owner_email, created_at, is_active)
                VALUES (?, ?, ?, ?, 1)
                """,
                (key_hash, body.tier, body.owner_email, created_at),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            # Extremely unlikely collision — treat as server error
            raise HTTPException(status_code=500, detail="Key generation conflict, please retry")
        finally:
            conn.close()

        return KeyProvisionResponse(
            key=raw_key,
            owner_email=body.owner_email,
            tier=body.tier,
            created_at=created_at,
        )
    except HTTPException:
        raise
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Internal configuration error")
