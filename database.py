import os
import sqlite3
from contextlib import contextmanager

_DB_PATH = os.environ.get("PROPEDGE_DB_PATH", "")


def _get_connection() -> sqlite3.Connection:
    if not _DB_PATH:
        raise RuntimeError("PROPEDGE_DB_PATH environment variable is not set")
    conn = sqlite3.connect(f"file:{_DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db():
    conn = _get_connection()
    try:
        yield conn
    finally:
        conn.close()
