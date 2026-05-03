from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .config import (
    DB_PATH,
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_SYSTEM_PROMPT,
)


def init_db(db_path: Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS executions (
                id INTEGER PRIMARY KEY,
                code TEXT NOT NULL,
                stdout TEXT NOT NULL,
                stderr TEXT NOT NULL,
                exit_code INTEGER NOT NULL,
                created_at DATETIME NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        defaults = {
            "model": DEFAULT_MODEL,
            "ollama_base_url": DEFAULT_OLLAMA_BASE_URL,
            "system_prompt": DEFAULT_SYSTEM_PROMPT,
        }
        conn.executemany(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            defaults.items(),
        )
        conn.commit()


@contextmanager
def connect(db_path: Path = DB_PATH) -> Iterator[sqlite3.Connection]:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_execution(code: str, stdout: str, stderr: str, exit_code: int) -> int:
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO executions (code, stdout, stderr, exit_code, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (code, stdout, stderr, exit_code, utc_now()),
        )
        conn.commit()
        return int(cursor.lastrowid)


def list_executions(limit: int = 20) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, code, stdout, stderr, exit_code, created_at
            FROM executions
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_settings() -> dict[str, str]:
    with connect() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {row["key"]: row["value"] for row in rows}


def update_settings(values: dict[str, str]) -> dict[str, str]:
    allowed = {"model", "ollama_base_url", "system_prompt"}
    filtered = {key: value for key, value in values.items() if key in allowed}
    with connect() as conn:
        conn.executemany(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            filtered.items(),
        )
        conn.commit()
    return get_settings()
