import os
import sqlite3
from contextlib import contextmanager
from typing import Optional


def _propedge_conn() -> sqlite3.Connection:
    path = os.environ.get("PROPEDGE_DB_PATH", "")
    if not path:
        raise RuntimeError("PROPEDGE_DB_PATH is not set")
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db():
    conn = _propedge_conn()
    try:
        yield conn
    finally:
        conn.close()


def get_picks(sport: str, date: str, tier: Optional[str] = None) -> list[dict]:
    with get_db() as conn:
        sql = "SELECT * FROM picks WHERE sport = ? AND game_date = ?"
        params: list = [sport, date]
        if tier:
            sql += " AND tier = ?"
            params.append(tier.upper())
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]


def get_slate_status(sport: str, date: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM slate_status WHERE sport = ? AND game_date = ?",
            (sport, date),
        ).fetchone()
        return dict(row) if row else None
