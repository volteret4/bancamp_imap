#!/usr/bin/env python3
"""
Estado de "escuchado" en SQLite, compartido entre server.py (API) y
bc_static_generator.py (filtra al renderizar). Sustituye al flujo anterior
de localStorage + export manual (bc_sync.py).
"""
import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.getenv("LISTENED_DB", "data/listened.db")


def _connect():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS listened (id TEXT PRIMARY KEY, marked_at TEXT NOT NULL)"
    )
    return conn


def is_listened(embed_id: str) -> bool:
    if not embed_id:
        return False
    with _connect() as conn:
        row = conn.execute("SELECT 1 FROM listened WHERE id = ?", (embed_id,)).fetchone()
        return row is not None


def listened_ids() -> set:
    with _connect() as conn:
        return {row[0] for row in conn.execute("SELECT id FROM listened")}


def mark_listened(embed_id: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO listened (id, marked_at) VALUES (?, ?)",
            (embed_id, datetime.now(timezone.utc).isoformat()),
        )
