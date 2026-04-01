import hashlib
import os
import sqlite3
from datetime import datetime, timezone

import anthropic

_ENRICHABLE_TIERS = {"STRONG", "SOLID"}


def _cache_conn() -> sqlite3.Connection:
    path = os.environ.get("REASONING_CACHE_DB_PATH", "")
    if not path:
        raise RuntimeError("REASONING_CACHE_DB_PATH is not set")
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_reasoning_cache() -> None:
    conn = _cache_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pick_reasoning (
            pick_key     TEXT PRIMARY KEY,
            reasoning    TEXT NOT NULL,
            generated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def _pick_key(pick: dict, date: str) -> str:
    raw = (
        f"{pick.get('player_name', '')}|"
        f"{pick.get('prop_type', '')}|"
        f"{pick.get('line', '')}|"
        f"{pick.get('side', '')}|"
        f"{date}"
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def _build_prompt(pick: dict) -> str:
    hit_pct = round(float(pick.get("hit_probability", 0)) * 100, 1)
    edge_pct = round(float(pick.get("edge_pct", 0)) * 100, 1)
    return (
        "You are a sports betting analyst. Write 1-2 sentences explaining why this prop "
        "pick has edge. Be specific and data-driven. Do not use hedging language.\n\n"
        f"Player: {pick.get('player_name', '')}\n"
        f"Prop: {pick.get('prop_type', '')}\n"
        f"Line: {pick.get('line', '')}\n"
        f"Direction: {pick.get('side', '')}\n"
        f"Hit probability: {hit_pct}%\n"
        f"Edge: {edge_pct}%\n"
        f"Tier: {pick.get('confidence_tier', '')}\n\n"
        "Respond with only the 1-2 sentence narrative. No preamble, no bullet points."
    )


def get_reasoning(pick: dict, date: str) -> str | None:
    """
    Returns Claude-generated reasoning for a pick, caching results in SQLite.
    Returns None on any error so a failed enrichment never breaks the endpoint.
    Only enriches picks in ENRICHABLE_TIERS (STRONG, SOLID).
    """
    if pick.get("confidence_tier") not in _ENRICHABLE_TIERS:
        return None

    try:
        key = _pick_key(pick, date)

        conn = _cache_conn()
        try:
            row = conn.execute(
                "SELECT reasoning FROM pick_reasoning WHERE pick_key = ?", (key,)
            ).fetchone()
            if row:
                return row["reasoning"]
        finally:
            conn.close()

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return None

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=150,
            messages=[{"role": "user", "content": _build_prompt(pick)}],
        )
        reasoning = message.content[0].text.strip()

        conn = _cache_conn()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO pick_reasoning (pick_key, reasoning, generated_at)
                VALUES (?, ?, ?)
                """,
                (key, reasoning, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

        return reasoning

    except Exception:
        return None
